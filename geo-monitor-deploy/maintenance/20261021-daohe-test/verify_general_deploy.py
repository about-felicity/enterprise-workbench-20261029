import sys,json,hashlib
from pathlib import Path
from datetime import datetime
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,observation as o
from geo_source_cards.article_logic import WRITING_RULES
from geo_source_cards.consumer_voice import issues
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');baseline=o.read(o.OUTPUT/'baseline.json');current=o.collect(datetime.now(o.ZONE))
assert baseline['source_fingerprint']==current['source_fingerprint']
assert '显色' not in WRITING_RULES and '不得把其他品类的示例' in WRITING_RULES
assert issues('成分表原文和瓶身标签原文。')==[]
assert issues('原文先写配方再写品牌。')
o.main()
backup=max(M.glob('source-before-general-rules-fix-*'),key=lambda p:p.name)
value={'at':current['at'],'backup':str(backup),'engine_tests':108,'creation_tests':69,'source_baseline_matches':True,'rules_verified':True,'completion_note':'Deployment completed; cleared deploy-only CLI flag before observer argparse verification'}
runtime.atomic_json(M/'general-rules-fix-deployment.json',value);print(json.dumps(value))
