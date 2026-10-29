import hashlib,json,tempfile,unittest,zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from . import materials,runtime,source_adapter

class ExportMetadataCacheTests(unittest.TestCase):
 def test_slim_index_reuses_reads_and_invalidates_after_source_update(self):
  from . import article_export as exports
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'sources.json'
   p.write_text(json.dumps([{'url':'https://example.com/a','article':{'final_url':'https://example.com/b','author':'one','text':'large private full text','metadata':{'publisher':'media'}}}]))
   exports._source_index.cache_clear()
   with patch.object(runtime,'read',wraps=runtime.read) as read:
    first=exports._source_index(p,exports._signature(p))
    second=exports._source_index(p,exports._signature(p))
    self.assertIs(first,second);self.assertEqual(read.call_count,1)
    self.assertEqual(first['https://example.com/b']['article']['author'],'one')
    self.assertNotIn('text',first['https://example.com/a']['article'])
    p.write_text(json.dumps([{'url':'https://example.com/a','author':'updated longer author'}]))
    changed=exports._source_index(p,exports._signature(p))
    self.assertEqual(changed['https://example.com/a']['author'],'updated longer author');self.assertEqual(read.call_count,2)

class MaterialTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.patches=[patch.object(materials,'ROOT',self.root/'materials'),patch.object(materials,'LEGACY',self.root/'legacy'),patch.object(materials,'GEO',self.root/'geo'),patch.object(runtime,'BASE',self.root/'jobs'),patch.object(runtime,'SHARED',self.root/'legacy')]
  for p in self.patches:p.start()
  materials.ROOT.mkdir();materials.LEGACY.mkdir();materials.GEO.mkdir()
  materials.atomic_json(materials.ROOT/'settings.json',{'enabled':True,'time':'01:00','questions':['专用问题'],'start_date':'2026-10-17'})
  materials.atomic_json(materials.GEO/'daily_plan.json',{'enabled':True,'time':'05:00'})
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.temp.cleanup()
 def test_private_records_and_catalog_do_not_query_geo(self):
  path=materials.LEGACY/'captures/2026-10-14/daily/observations.jsonl';path.parent.mkdir(parents=True)
  row={'model':'deepseek','question':'专用问题','body':'正文','body_capture_complete':True,'captured_at':'2026-10-14T01:00:00+08:00','url':'https://chat.deepseek.com/a/chat/s/test'}
  path.write_text(json.dumps(row)+'\n')
  with patch.object(source_adapter,'query',side_effect=AssertionError('Private materials must not query GEO')):
   self.assertEqual(materials.records('2026-10-14','专用问题',['deepseek']),[row])
   self.assertEqual(materials.catalog()['questions'],['专用问题'])
 def test_save_time_keeps_geo_plan_untouched(self):
  path=materials.GEO/'daily_plan.json';before=path.read_bytes()
  materials.save({'enabled':True,'time':'01:00','questions':['原问题','新问题']})
  self.assertEqual(path.read_bytes(),before)
  with self.assertRaises(ValueError):materials.save({'enabled':True,'time':'05:00','questions':['原问题']})
 def test_resource_and_pre_monitor_window_gates(self):
  plan={'enabled':True,'time':'05:00'};now=datetime(2026,10,17,1,tzinfo=ZoneInfo('Asia/Shanghai'))
  self.assertEqual(materials.conflict(now,'deepseek',plan,True),'waiting_for_geo')
  self.assertIsNone(materials.conflict(now,'deepseek',plan,False))
  self.assertEqual(materials.conflict(now.replace(hour=4,minute=45),'deepseek',plan,False),'waiting_for_geo_window')
  self.assertEqual(materials.conflict(now.replace(hour=4,minute=58),'baidu_ai',plan,False),'waiting_for_geo_window')
  self.assertEqual(materials.conflict(now.replace(hour=5),'deepseek',plan,False),'waiting_for_geo_window')
 def test_today_first_does_not_relabel_or_delete_backlog(self):
  materials.atomic_json(materials.ROOT/'days/2026-10-19/config.json',{'questions':['旧问题'],'channels':['baidu_ai']})
  cfg={'frequency':'daily','day_policy':'today_first','start_date':'2026-10-19','time':'01:00'}
  now=datetime(2026,10,20,2,tzinfo=materials.ZONE)
  self.assertEqual(materials.next_day(cfg,'2026-10-20',now),'2026-10-20')
  self.assertTrue((materials.ROOT/'days/2026-10-19/config.json').exists())
 def test_recovery_progress_reports_safe_fields_without_captcha_urls(self):
  import sqlite3
  folder=materials.ROOT/'days/2026-10-20/wenxin_card/collector';folder.mkdir(parents=True)
  with sqlite3.connect(folder/'tasks.sqlite') as db:
   db.execute('create table captures(state text)');db.execute("insert into captures values('pending')")
  materials.atomic_json(folder/'search_recovery.json',{'kind':'verification','status':'cooling_down','cooldown_until':123,'error':'private URL','task_id':'internal'})
  row=next(r for r in materials.progress('2026-10-20') if r['id']=='wenxin_card')
  self.assertEqual(row['recovery'],{'kind':'verification','status':'cooling_down','cooldown_until':123})
 def test_dedicated_search_pool_isolated_without_releasing_deepseek_gate(self):
  now=datetime(2026,10,20,9,tzinfo=ZoneInfo('Asia/Shanghai'));plan={'enabled':True,'time':'09:00'}
  with patch.object(materials,'CONTENT_BASE',self.root),patch.object(materials,'SEARCH_POOL',self.root/'pool'):
   materials.atomic_json(self.root/'creation_search_pool.json',{'enabled':True})
   cfg=materials.settings();cfg['search_pool']='creation_only';materials.atomic_json(materials.ROOT/'settings.json',cfg)
   for model in ('baidu_ai','wenxin_card'):
    resources=materials.search_resources(model)
    self.assertTrue(resources['dedicated'])
    self.assertEqual(resources['lock'],self.root/'pool/browser.lock')
    self.assertNotEqual(resources['rate'],materials.GEO/'search_last_start.json')
    self.assertIsNone(materials.conflict(now,model,plan,True,dedicated=True))
   self.assertFalse(materials.dedicated_search('deepseek'))
   self.assertEqual(materials.conflict(now,'deepseek',plan,True,dedicated=True),'waiting_for_geo')
   materials.atomic_json(self.root/'creation_search_pool.json',{'enabled':False})
   self.assertFalse(materials.search_resources('baidu_ai')['dedicated'])
 def test_private_creation_enqueues_preparation_without_geo_query_or_paid_call(self):
  row={'model':'deepseek','question':'专用问题','body':'原始正文','sources':[]}
  with patch.object(materials,'records',return_value=[row]),patch.object(source_adapter,'observations',side_effect=AssertionError('No GEO observations')),patch.object(runtime,'balance',return_value={'is_available':True}):
   result=runtime.create({'date':'2026-10-14','question':'专用问题','material_source':'dedicated','product':{'name':'用户产品','facts':[]}})
  root=runtime.job_root(result['job_id']);job=runtime.read(root/'job.json')
  self.assertEqual(job['preparation'],'pending');self.assertEqual(job['platform_questions_sent'],0)
  self.assertEqual(json.loads((root/'private_observations.jsonl').read_text()),row)
 def approved(self):
  folder=materials.LEGACY/'approved/2026-10-14/排行类/01';folder.mkdir(parents=True)
  (folder/'draft.md').write_text('# 已审稿\n原始成稿')
  with zipfile.ZipFile(folder/'article.docx','w') as z:z.writestr('word/document.xml','<document>正文</document>')
  hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
  (folder/'receipt.json').write_text(json.dumps({'status':'accepted_for_user_review','files':hashes,'word_sha256':hashes['article.docx']}))
  return folder,hashes
 def test_legacy_word_and_bundle_preserve_original_bytes(self):
  folder,hashes=self.approved();article_id='2026-10-14/排行类/01'
  self.assertEqual(runtime.download('legacy-original',article_id,'word').read_bytes(),(folder/'article.docx').read_bytes())
  archive=runtime.download('all-approved','','bundle')
  with zipfile.ZipFile(archive) as z:
   word=next(n for n in z.namelist() if n.endswith('.docx'))
   self.assertEqual(hashlib.sha256(z.read(word)).hexdigest(),hashes['article.docx'])
 def test_revoked_and_modified_deliveries_cannot_be_downloaded(self):
  folder,hashes=self.approved();materials.atomic_json(materials.LEGACY/'revocations/test.json',{'word_sha256':hashes['article.docx']})
  self.assertEqual(runtime.articles(materials.LEGACY),[])
  with self.assertRaises(ValueError):runtime.download('legacy-original','2026-10-14/排行类/01','word')
  (materials.LEGACY/'revocations/test.json').unlink();(folder/'draft.md').write_text('修改正文')
  self.assertEqual(runtime.articles(materials.LEGACY),[])

 def test_product_date_bundle_uses_archived_product_and_only_selected_articles(self):
  import shutil
  first,_=self.approved();second=materials.LEGACY/'approved/2026-10-13/排行类/01'
  second.parent.mkdir(parents=True);shutil.copytree(first,second)
  materials.atomic_json(materials.LEGACY/'days/2026-10-14/product.json',{'name':'产品甲','brand':'品牌甲'})
  materials.atomic_json(materials.LEGACY/'days/2026-10-13/product.json',{'name':'产品乙','brand':'品牌乙'})
  materials.atomic_json(materials.LEGACY/'product.json',{'name':'之后改动的产品'})
  rows=runtime.articles(materials.LEGACY);chosen=next(a for a in rows if a['date']=='2026-10-14')
  self.assertEqual(chosen['product']['name'],'产品甲')
  path=runtime.download('all-approved','','bundle',{'date':'2026-10-14','product':chosen['product']['id'],'source':'legacy-original','search':'已审稿'})
  with zipfile.ZipFile(path) as z:
   manifest=json.loads(z.read('导出清单.json'));self.assertEqual(manifest['count'],1)
   self.assertTrue(all('_2026-10-14/' in n for n in z.namelist() if n!='导出清单.json'))
  with self.assertRaisesRegex(ValueError,'没有可下载'):
   runtime.download('all-approved','','bundle',{'date':'2026-10-13','product':chosen['product']['id']})
  with self.assertRaises(ValueError):runtime.download('all-approved','','bundle',{'product':'../../bad'})

if __name__=='__main__':unittest.main()
