"""Real user-requested sample, original queue and shared ledger, isolated from production jobs."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path[:0] = [str(BASE / 'engine'), str(BASE)]
os.environ['GEO_CREATION_ROOT'] = str(BASE / 'real-sample')
from geo_source_cards.runtime import atomic_json
from geo_source_cards.staged_editorial import read
from geo_source_cards.api_worker import Worker
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.deepseek_api import DeepSeekClient
from geo_source_cards.rewrite_v2 import integration, material_manager
from creation.runtime import SharedBudget, KEY

ROOT = BASE / 'real-sample/runs/creation-1792742400-a2c61023'
DAY = '2026-10-23'
META = {'date': DAY, 'category': '排行类', 'number': 1, 'workflow': 'rewrite-v2'}
CACHE = BASE / 'real-sample/cache'

def status(budget):
    tickets = [{k: read(p).get(k) for k in ('id', 'stage', 'state', 'error', 'waiting_skeleton')} for p in sorted((ROOT / 'queue').glob('*/ticket.json'))]
    costs = [dict(r) for r in budget.db.execute('select c.stage,c.reserved,c.charged,c.state,c.usage from costs c join studio_cost_scopes s on c.id=s.id where s.job=?', (ROOT.name,))]
    result = {'root': str(ROOT), 'tickets': tickets, 'costs': costs,
              'remaining_cny': budget.remaining(META, 'writer'), 'at': time.time()}
    atomic_json(BASE / 'real-sample/status.json', result)
    print(json.dumps(result, ensure_ascii=False), flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['parse', 'material', 'continue', 'status'])
    args = parser.parse_args()
    data = read(BASE / 'sample_input.json')
    if not (ROOT / 'job.json').exists():
        atomic_json(ROOT / 'rewrite_policy.json', {'workflow': 'rewrite-v2', 'cache_dir': str(CACHE), 'max_rewrites': 1})
        atomic_json(ROOT / 'job.json', {'workflow': 'rewrite-v2', 'job_id': ROOT.name, 'date': DAY,
                    'task_name': '用户指定小绿瓶知识库 V2 真实样例', 'budget_limits': {'article_budget_cny': .35, 'task_budget_cny': .35}})
        atomic_json(ROOT / 'logic_policy.json', {'required': True, 'version': 'rewrite-v2'})
        atomic_json(ROOT / 'days' / DAY / 'day.json', {'date': DAY, 'status': 'producing', 'planned_articles': 1})
        atomic_json(ROOT / 'days' / DAY / 'product.json', data['product'])
        atomic_json(ROOT / 'sample_provenance.json', data['provenance'])
        loc = ROOT / 'days' / DAY / 'jobs/排行类/01/research'
        integration.prepare_research(loc, data['observations'], data['product'])
        atomic_json(loc.parent / 'category.json', {'label': '排行类', 'number': 1, 'source_urls': [data['provenance']['reference_url']]})
        publish_ticket(ROOT, 'research', loc, ['research_input.json', 'research_task.txt'], ['research_result.json'], META)
    budget = SharedBudget(ROOT)
    client = DeepSeekClient(KEY, budget=budget)
    try:
        if args.phase == 'material':
            material_manager.process(client, data['product'], CACHE, ROOT / 'prefetch-material', META)
        elif args.phase in {'parse', 'continue'}:
            worker = Worker(ROOT, client)
            for _ in range(3 if args.phase == 'parse' else 10):
                result = worker.once(DAY)
                print(json.dumps(result, ensure_ascii=False), flush=True)
                if result.get('status') in {'needs_attention', 'complete', 'waiting_human_review', 'blocked_unknown_execution'}:
                    break
    finally:
        status(budget)
        budget.db.close()
        client.session.close()

if __name__ == '__main__':
    main()
