"""Resume only unsent maintenance holds; never resume a production job."""
import argparse
import json
import time
from pathlib import Path
from geo_source_cards.consumer_prompts import require_writer_material, evidence_units
from geo_source_cards.runtime import atomic_json, process_lock
from . import runtime, quality_repair as repair


def eligibility(item, include_paused_sources=False):
    entry = repair.ROOT / item['key']
    state = runtime.read(entry / 'status.json')
    if state.get('state') != 'needs_attention' or state.get('reason') != 'consumer_contract_maintenance':
        return 'not_unsent_maintenance_hold'
    root = Path(item['root'])
    if runtime.read(root / 'control.json').get('paused') and not include_paused_sources:
        return 'production_job_paused'
    # A maintenance label alone is insufficient proof of no send.
    if any(entry.glob('attempt-*/calls/*/api_state.json')) or any(entry.glob('attempt-*/calls/*/request.json')):
        return 'existing_request_evidence'
    if any(entry.glob('calls/*/api_state.json')) or any(entry.glob('calls/*/request.json')):
        return 'existing_request_evidence'
    folder = root / 'approved' / item['id']
    if runtime.read(folder / 'receipt.json').get('word_sha256') != item['original_word_sha256']:
        return 'article_version_changed'
    if item.get('preflight_error') or not item.get('writer'):
        return 'missing_original_evidence'
    active = runtime.read(root / 'api/active.json')
    if active.get('state') not in (None, 'SUBMITTED'):
        return 'production_execution_in_progress'
    writer = Path(item['writer'])
    try:
        require_writer_material(runtime.read(writer / 'knowledge.json'), runtime.read(writer / 'product.json'), evidence_units(writer))
    except (ValueError, KeyError, TypeError, FileNotFoundError) as error:
        return 'insufficient_material: ' + str(error)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--include-paused-sources', action='store_true', help='Explicitly revise saved articles in isolated sidecars; never resume their original paused jobs')
    args = parser.parse_args()
    report = {'started_at': time.time(), 'paid_run': args.run, 'selected': [], 'excluded': [], 'results': []}
    report['include_paused_sources'] = args.include_paused_sources
    target = repair.ROOT / ('followup-paused-20261021.json' if args.include_paused_sources else 'followup-20261021.json')
    with process_lock(repair.ROOT / 'process.lock', blocking=False):
        repair.STOP.clear()
        repair.STOP_ON_UNKNOWN = True
        for item in repair.scan():
            reason = eligibility(item, args.include_paused_sources)
            if reason:
                report['excluded'].append({'key': item['key'], 'id': item['id'], 'reason': reason})
            else:
                report['selected'].append(item)
        atomic_json(target, report)
        if args.run:
            for item in report['selected']:
                reason = eligibility(item, args.include_paused_sources)
                if reason:
                    report['results'].append({'key': item['key'], 'state': 'skipped', 'reason': reason})
                else:
                    control_path = Path(item['root']) / 'control.json'
                    before_control = control_path.read_bytes() if control_path.exists() else None
                    result = repair.revise(item, retry_known=True)
                    after_control = control_path.read_bytes() if control_path.exists() else None
                    report['results'].append({'key': item['key'], **result, 'original_job_control_unchanged': before_control == after_control})
                    if before_control != after_control:
                        report['stopped_on_control_change'] = True
                        atomic_json(target, report)
                        break
                atomic_json(target, report)
                print(json.dumps(report['results'][-1], ensure_ascii=False), flush=True)
                if repair.STOP.is_set():
                    report['stopped_on_new_unknown'] = True
                    break
        report['finished_at'] = time.time()
        atomic_json(target, report)
    print(json.dumps({'selected': len(report['selected']), 'excluded': len(report['excluded']), 'processed': len(report['results']), 'stopped_on_new_unknown': report.get('stopped_on_new_unknown', False)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
