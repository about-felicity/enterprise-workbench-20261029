"""Consolidate product cards and byte-identical uploads; preserve rollback evidence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import uuid

from creation import knowledge_library as kl, runtime, studio
from geo_source_cards.runtime import process_lock

ROOT = studio.ROOT
BACKUP = Path(os.environ.get('GEO_KNOWLEDGE_DEDUP_BACKUP', '/opt/monitor/geo-content/maintenance/knowledge-dedup-20261026'))
ALIASES = {
    'product-ae04b5d593044c62bd59f77a3eb83987': 'product-7fd5fad9bef04e4ca2b00045443ea372',
    'product-18d49f719f2c4ef7a341241ccf540102': 'product-cbdab5bf17454acaa1996253f6c50ac9',
}


def digest_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def original_files():
    return {str(p.relative_to(ROOT)): digest_file(p)
            for pattern in ('imports/**/*', 'images/*/original', 'plans/*.json', 'days/**/*.json')
            for p in ROOT.glob(pattern) if p.is_file() and p.suffix != '.lock'}


def run():
    with process_lock(runtime.BASE / 'actions.lock', blocking=True):
        if (BACKUP / 'result.json').exists():
            raise RuntimeError('This consolidation has already completed')
        BACKUP.mkdir(parents=True, exist_ok=True)
        protected = original_files()
        records = kl.records()
        products = {p['product_id']: p for p in studio.products()}
        images = [runtime.read(p) for p in (ROOT / 'images').glob('*/metadata.json')]
        for folder in ('products', 'library'):
            shutil.copytree(ROOT / folder, BACKUP / 'before' / folder, dirs_exist_ok=True)
        for p in (ROOT / 'images').glob('*/metadata.json'):
            dest = BACKUP / 'before' / 'images' / p.parent.name / p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
        runtime.atomic_json(BACKUP / 'protected-before.json', protected)

        # Verify the two explicit equivalence decisions before any mutation.
        for old, new in ALIASES.items():
            assert products[old]['product']['name'] == products[new]['product']['name']
            assert products[old]['updated_at'] < products[new]['updated_at']

        changes = []
        for record in records:
            pid = record.get('product_id', '')
            if pid in ALIASES:
                record['product_id'] = ALIASES[pid]
                changes.append({'action': 'merge_product_reference', 'old': pid, 'new': ALIASES[pid]})
            runtime.atomic_json(ROOT / 'library' / (record['library_id'] + '.json'), record)

        # Same original bytes need no repeated analysis; publish with the existing
        # reviewed facts, retaining evidence and the product's stable identity.
        reused = []
        for record in kl.records():
            pid = record.get('product_id')
            if not pid or not record.get('uploads'):
                continue
            current = studio.product(pid)
            latest = record['uploads'][-1]
            if (latest['status'] == 'pending'
                    and latest.get('sha256') == current.get('word_source', {}).get('sha256')):
                product = current['product']
                result = kl.publish({
                    'library_id': record['library_id'], 'import_id': latest['import_id'],
                    'expected_version': current['version'],
                    'reviewer': 'Codex：原文件SHA256完全一致，复用已有人工分析',
                    'product': {'name': product['name'], 'brand': product.get('brand', ''),
                                'audience': product.get('audience', ''),
                                'facts': [f['text'] for f in product['facts']]},
                })
                reused.append({'library_id': record['library_id'], **result})

        deduped = []
        for record in kl.records():
            # Walk backwards so the latest upload metadata wins for equal bytes.
            seen, kept = set(), []
            for upload in reversed(record['uploads']):
                key = upload.get('sha256') or upload['import_id']
                if key in seen:
                    deduped.append({'library_id': record['library_id'], 'import_id': upload['import_id']})
                    continue
                seen.add(key)
                kept.append(upload)
            record['uploads'] = list(reversed(kept))
            for index, upload in enumerate(record['uploads'], 1):
                upload['revision'] = index
            runtime.atomic_json(ROOT / 'library' / (record['library_id'] + '.json'), record)

        # Give the two pre-existing products without an inbox record a single
        # library record too, without inventing an upload for manually entered data.
        linked = {r.get('product_id') for r in kl.records()}
        created = []
        for pid, product in products.items():
            if pid in ALIASES or pid in linked:
                continue
            source = product.get('word_source', {})
            uploads = []
            if source.get('import_id'):
                item = {k: source.get(k) for k in ('import_id', 'filename', 'sha256', 'bytes', 'paragraphs')}
                item.update(uploaded_at=source.get('at', product['updated_at']), revision=1,
                            status='published', product_version=product['version'], notes='已有产品原知识库，整理时补齐统一入口')
                uploads.append(item)
            lid = 'library-' + uuid.uuid4().hex
            record = {'library_id': lid, 'product_id': pid, 'name': product['product']['name'],
                      'created_at': product['updated_at'], 'updated_at': product['updated_at'], 'uploads': uploads}
            runtime.atomic_json(ROOT / 'library' / (lid + '.json'), record)
            created.append(lid)

        relinked = []
        for image in images:
            pid = image.get('product_id', '')
            if pid in ALIASES:
                image['product_id'] = ALIASES[pid]
                runtime.atomic_json(ROOT / 'images' / image['image_id'] / 'metadata.json', image)
                relinked.append(image['image_id'])
        for old in ALIASES:
            src = ROOT / 'products' / (old + '.json')
            version = ROOT / 'versions' / old / (products[old]['version'] + '.json')
            if not version.exists():
                version.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, version)
            archive = BACKUP / 'retired-products' / src.name
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(archive))

        active = studio.products()
        records = kl.records()
        names = [p['product']['name'] for p in active]
        names += [r['name'] for r in records if not r.get('product_id')]
        assert len(names) == len(set(names)), 'Duplicate visible product names'
        links = [r['product_id'] for r in records if r.get('product_id')]
        assert len(links) == len(set(links)) == len(active)
        assert set(links) == {p['product_id'] for p in active}
        assert original_files() == protected, 'Original files or task snapshots changed'
        for image in images:
            assert not image.get('product_id') or image['product_id'] in set(links)
            assert not image.get('library_id') or image['library_id'] in {r['library_id'] for r in records}
            assert digest_file(ROOT / 'images' / image['image_id'] / 'original') == image['sha256']
        rows = []
        for r in records:
            pid, lid = r.get('product_id'), r['library_id']
            rows.append({'name': r['name'], 'product_id': pid, 'library_id': lid,
                         'versions': len(r['uploads']),
                         'latest_status': r['uploads'][-1]['status'] if r['uploads'] else 'manual',
                         'images': sum(bool((pid and i.get('product_id') == pid) or i.get('library_id') == lid) for i in images)})
        result = {'at': time.time(), 'aliases': ALIASES, 'deduplicated_uploads': deduped,
                  'reused_analysis': reused, 'created_library_records': created,
                  'relinked_images': relinked, 'products': len(active), 'library_records': len(records),
                  'visible_products': len(names), 'images': len(images), 'rows': rows,
                  'protected_files': len(protected), 'protected_unchanged': True}
        runtime.atomic_json(BACKUP / 'result.json', result)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
