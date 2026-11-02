import json
import sys
from pathlib import Path
here=Path(__file__).resolve().parent
root=here.parents[1]
mapping={
 'creation/materials.py':('geo-monitor-deploy/creation/materials.py','1d261c17d6f7abd58f5e852ada2e4c00b628fd930cd1a0039d146dd33d42ba65'),
 'creation/client.py':('geo-monitor-deploy/creation/client.py','2f6eda3addb209c3a65719b068cfa9085256f95542d87aa415105c61b69c8882'),
 'creation/supplement.py':('geo-monitor-deploy/creation/supplement.py','0e9d7c55ab1ddc68d28bd098c878cd72229e7c71e921bdf37ef1c0b6ca3b7916'),
 'creation/studio.py':('geo-monitor-deploy/creation/studio.py','8079a4a4e8c9718f725e261f37a92f7614a8bda9e32d6b03a01d56dd53553adf'),
 'engine/geo_source_cards/source_analysis.py':('geo-source-card-collectors/geo_source_cards/source_analysis.py','4a50e656f7d737464f07863805508b06e85b70b51f81be344b91d1f2464e8ede'),
}
files={target:{'source':source,'before':before,'text':(root/source).read_text('utf8')} for target,(source,before) in mapping.items()}
suffix=''
if len(sys.argv)>1 and sys.argv[1]=='cache':
 suffix='_cache'
 mapping={
  'creation/materials.py':('geo-monitor-deploy/creation/materials.py','800a0064796025a5f0ad1d10c17f7666095e60b61f254b0ec98a2f0b749b1695'),
  'creation/source_cache.py':('geo-monitor-deploy/creation/source_cache.py','6061f0af0f7f9049f5ba4ae6171dd69f0e8f0a538d893f58065015a8de17e70b'),
  'creation/runtime.py':('geo-monitor-deploy/creation/runtime.py','86eee7071a8462f3584ac38c401efd29792d76b8094940341ba4f9412fabf11d'),
 }
 files={target:{'source':source,'before':before,'text':(root/source).read_text('utf8')} for target,(source,before) in mapping.items()}
if len(sys.argv)>1 and sys.argv[1]=='scope':
 suffix='_scope'
 mapping={'engine/geo_source_cards/source_scope.py':('geo-source-card-collectors/geo_source_cards/source_scope.py','e089ac755de1e3d9fd2d4f157e7d9a9d51b047ec2e258086f43842308a3ad793')}
 files={target:{'source':source,'before':before,'text':(root/source).read_text('utf8')} for target,(source,before) in mapping.items()}
tests={name:(root/'geo-monitor-deploy/creation'/name).read_text('utf8') for name in ['test_jsonl_records.py','test_response_framing.py','test_source_cache.py','test_shared_source_cache.py','test_topic_aliases.py']}
template=(here/'deploy_template.py').read_text('utf8')
(here/('deploy'+suffix+'.py')).write_text('FILES='+repr(files)+'\nTESTS='+repr(tests)+'\nRESTART_UNITS='+repr([] if suffix=='_scope' else ['geo-content-api.service','geo-creation-studio.service'])+'\n'+template,encoding='utf8')
print('Prepared release with',len(files),'production files')
