"""Apply the user's 2026-10-24 explicit instruction to let the assistant check these skeletons."""
import json,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from geo_source_cards.runtime import atomic_json
from geo_source_cards.rewrite_v2 import structure_parser
from geo_source_cards.rewrite_v2.common import digest
from multi_run import CACHE
out=BASE/'multi-results'
manifest=json.loads((out/'review-manifest.json').read_text())
authorization={'user_instruction':'我要的是全流程，我主要看文章，给我把最终文章跑出来啊，你觉得我需要来校验骨架吗，先写，我看到有问题我再决定',
 'user_date':'2026-10-24','mode':'assistant_review_explicitly_delegated_by_user',
 'scope':[row['key'] for row in manifest],'at':time.time(),
 'human_review_performed':False,'meaning':'User superseded the document requirement to personally inspect skeletons; assistant checked the proposed corrections.'}
atomic_json(out/'delegated-review-authorization.json',authorization)
for row in manifest:
    proposal=json.loads((out/row['key']/'proposed-skeleton.json').read_text())
    assert digest(proposal)==row['proposal_sha256'],'Proposal changed since preparation'
    existing=json.loads((CACHE/'skeleton'/(row['cache_key']+'.json')).read_text())
    reviewer='assistant under explicit user delegation 2026-10-24; not human skeleton inspection'
    if existing.get('approval'):
        assert existing['approval']['reviewer']==reviewer and existing['skeleton']==proposal
        continue
    approved=structure_parser.approve(CACHE,row['cache_key'],row['expected_sha256'],reviewer,skeleton=proposal)
    atomic_json(out/row['key']/'accepted-skeleton.json',approved)
    print('accepted delegated review',row['key'],flush=True)
