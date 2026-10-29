import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,'/tmp/geo-yuanbao-text-candidate')
sys.path.append('/opt/monitor')
from monitor_core.native_text import clean_native_text,decode_native_text
from monitor_core.owned_products import own_product_mentions,owned_product_recommendations
from monitor_core.ingestion import normalize_remote_record
from monitor_core.analytics import _owned_product_model_status
from monitor_core.product_analysis import merge_explicit_owned_products
import save_doubao_refs as saver


class NativeTextTests(unittest.TestCase):
 def test_empty_brand_control_is_removed_without_removing_words(self):
  text='### 梵玢[](@replace=10001) FBCY 眉毛精华液（温和）[](@mark_underline=2)[citation:5][](@mark_underline=3)'
  clean,report=decode_native_text(text)
  self.assertEqual(clean,'### 梵玢 FBCY 眉毛精华液（温和）[citation:5]')
  self.assertEqual(report['empty_controls_removed'],3)
  self.assertIn('梵玢眉毛精华液',own_product_mentions(text))
  self.assertIn('梵玢眉毛精华液',owned_product_recommendations(text))
 def test_all_plain_models_pass_through_exactly(self):
  for value in ['推荐：品牌甲精华液。\n\n[citation:1]', '正文 @example.com', '参考 [链接](https://example.com)', '## 正文\n汉字🙂']:
   self.assertEqual(clean_native_text(value),value)
 def test_only_known_placeholder_host_and_schema_are_removed(self):
  value='真实产品名\n![@replace_goods&abc](https://yuanbao)\n![@replace_videoBoxV2&def](https://yuanbao)'
  self.assertEqual(clean_native_text(value),'真实产品名')
  for value in ['![@replace_goods&id](https://example.com)','[](@unknown=1)','[文字](@replace=10001)']:
   self.assertEqual(clean_native_text(value),value)
 def test_normalization_is_idempotent(self):
  value='甲[](@mark_underline=1)乙[](@replace=1)丙\n\n![@replace_goods&id](https://yuanbao)'
  self.assertEqual(clean_native_text(clean_native_text(value)),clean_native_text(value))
 def test_mini_program_links_preserve_visible_brand_text(self):
  value='推荐[植村秀](@stylelink?key=@replace_miniProgram_abc&style=iconLink&display=miniProgram)卸妆油。![@replace_miniProgramBox&box](https://yuanbao)'
  clean,report=decode_native_text(value)
  self.assertEqual(clean,'推荐植村秀卸妆油。')
  self.assertEqual(report['style_links_decoded'],1)
  self.assertEqual(report['mini_program_cards_archived'],1)
  self.assertEqual(report['unhandled_controls'],0)
 def test_empty_replacement_ids_can_be_opaque_not_only_numeric(self):
  self.assertEqual(clean_native_text('甲[](@replace=media_20c6e634aa7a2bca)乙'),'甲乙')
 def test_unknown_native_control_is_preserved_and_flagged(self):
  raw='甲[](@mark_unknown=1)乙'
  clean,report=decode_native_text(raw)
  self.assertEqual(clean,raw)
  self.assertGreater(report['unhandled_controls'],0)
 def test_native_media_placeholder_keeps_only_meaningful_alt_text(self):
  self.assertEqual(clean_native_text('正文![goods](@replace=media_20c6e634aa7a2bca)'),'正文')
  self.assertEqual(clean_native_text('正文![原始图片说明](@replace=media_abc)'),'正文原始图片说明')
 def test_all_frozen_affected_history_decodes_without_losing_citations(self):
  import re
  root=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit')
  backups=sorted(root.glob('database-before-[0-9]*.jsonl'))
  if not backups:self.skipTest('Historical frozen fixture absent')
  count=0
  for line in backups[0].read_text().splitlines():
   raw=json.loads(line)['run']['answer'];clean,report=decode_native_text(raw)
   self.assertEqual(report.get('unhandled_controls',0),0)
   self.assertEqual(re.findall(r'\[citation:\d+\]',raw),re.findall(r'\[citation:\d+\]',clean))
   count+=1
  self.assertEqual(count,632)
 def test_negative_product_remains_negative(self):
  text='不推荐梵玢[](@replace=1)眉毛精华液。'
  self.assertNotIn('梵玢眉毛精华液',owned_product_recommendations(text))
 def test_normalization_preserves_raw_capture_and_stable_run_identity(self):
  record={'question':'推荐一款眉毛增长液','web_body':'梵玢[](@replace=1)眉毛精华液','serial':'yuanbao-hpe14-android13','round':1,'started_at':'2026-10-17T05:00:00+08:00','finished_at':'2026-10-17T05:01:00+08:00','sources':[]}
  original=copy.deepcopy(record)
  normalized=normalize_remote_record('yuanbao',record)
  self.assertEqual(record,original)
  self.assertEqual(normalized['answer'],'梵玢眉毛精华液')
  self.assertEqual(normalized['answer_raw'],original['web_body'])
  self.assertEqual(normalize_remote_record('yuanbao',record)['run_id'],normalized['run_id'])
 def test_pending_analysis_does_not_become_a_zero_recommendation(self):
  row={'run_id':'pending','answer':'推荐品牌甲眉毛精华液','products':[],'product_review_status':'ai_pending'}
  status=_owned_product_model_status([row],'梵玢眉毛精华液','眉毛增长液推荐')
  self.assertEqual(status['state'],'pending')
  self.assertEqual(status['pending_runs'],1)
 def test_pending_ai_does_not_hide_explicit_positive_body_evidence(self):
  row={'run_id':'pending','answer':'推荐梵玢[](@replace=1)眉毛精华液','products':[],'product_review_status':'ai_pending'}
  status=_owned_product_model_status([row],'梵玢眉毛精华液','眉毛增长液推荐')
  self.assertEqual(status['state'],'listed')
  self.assertEqual(status['recommendation_rate'],100)
 def test_owned_merge_retains_literal_evidence(self):
  body='### 梵玢[](@replace=1)FBCY眉毛精华液（温和养护）'
  products=merge_explicit_owned_products(body,'眉毛增长液推荐',[])
  self.assertEqual(len(products),1)
  self.assertNotIn('@replace',products[0]['evidence'])
  self.assertIn('梵玢',products[0]['evidence'])
 def test_instruction_is_not_a_product(self):
  for name in ['避开米诺地尔**','不要买品牌甲精华液','不推荐品牌甲精华液']:
   with self.subTest(name=name),self.assertRaises(ValueError):
    saver.validate_grounded_ai_products(name,[{'product_name':name,'evidence':name,'brand_name':''}])
 def test_positive_avoid_irritation_is_not_a_negative_product(self):
  saver.validate_grounded_ai_products('推荐品牌甲精华液，避免接触眼睛。',[{'product_name':'品牌甲精华液','evidence':'推荐品牌甲精华液','brand_name':'品牌甲'}])
 def test_avoiding_an_ingredient_does_not_negate_the_product(self):
  for evidence in ['头皮容易过敏、想避开对苯二胺：选北柔染发膏','北柔染发膏（避开强致敏成分）']:
   saver.validate_grounded_ai_products(evidence,[{'product_name':'北柔染发膏','brand_name':'北柔','evidence':evidence}])
 def test_avoidance_directly_targeting_a_product_is_rejected(self):
  with self.assertRaises(ValueError):
   saver.validate_grounded_ai_products('避开米诺地尔。',[{'product_name':'米诺地尔','evidence':'避开米诺地尔','brand_name':''}])
 def test_selection_summary_is_not_an_extra_product_heading(self):
  from unittest.mock import patch
  body='### 北柔染发膏\n- 核心：温和配方\n## 怎么选\n- 头皮敏感、想避开致敏成分：选**北柔染发膏**\n- 功效：遮白发'
  with patch.object(saver,'_load_historical_brand_registry',return_value={'北柔'}):
   items=saver.extract_structured_product_headings(body,'染发剂推荐')
  self.assertTrue(all(not item['product_name'].startswith('选') for item in items))
  self.assertTrue(all('想避开' not in item['evidence'] for item in items))
 def test_actual_today_corpus_preserves_other_models_and_fixes_eyebrow(self):
  path=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit/today-before.json')
  if not path.exists():self.skipTest('Production frozen read-only fixture absent')
  rows=json.loads(path.read_text());matches=0;total=0
  for row in rows:
   if row['model_id']!='yuanbao':self.assertEqual(clean_native_text(row['answer']),row['answer'])
   if row['model_id']=='yuanbao' and row['question']=='眉毛增长液推荐':
    total+=1
    matches+='梵玢眉毛精华液' in owned_product_recommendations(row['answer'])
  self.assertEqual((matches,total),(4,8))


if __name__=='__main__':unittest.main()
