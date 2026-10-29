"""Allocate a configurable task total across genuine, deduplicated source pools."""
def validate_quotas(value,target):
 if not value:return {}
 if not isinstance(value,dict) or not set(value)<={'排行类','科普类','测评类'} or any(type(n) is not int or not 1<=n<=100 for n in value.values()) or sum(value.values())!=target:raise ValueError('分类篇数须为正整数，合计等于任务总篇数')
 return dict(value)

def allocate(pools,target,preferences,genre_targets=None):
 if type(target) is not int or not 1<=target<=100:raise ValueError('Article target must be 1..100')
 labels=list(dict.fromkeys([v for v in preferences if v in pools]+list(pools)))
 quotas=validate_quotas(genre_targets,target)
 chosen={label:[] for label in pools};seen=set();offsets={label:0 for label in pools}
 while sum(map(len,chosen.values()))<target:
  advanced=False
  for label in labels:
   if quotas and len(chosen[label])>=quotas.get(label,0):continue
   while offsets[label]<len(pools[label]):
    source,group=pools[label][offsets[label]];offsets[label]+=1
    if group in seen:continue
    chosen[label].append(source);seen.add(group);advanced=True;break
   if sum(map(len,chosen.values()))>=target:break
  if not advanced:break
 count=sum(map(len,chosen.values()))
 return {'selected':chosen,'target':target,'planned':count,'shortfall':target-count,'missing_genres':[label for label in preferences if not chosen.get(label)],**({'genre_targets':quotas,'genre_shortfalls':{k:max(0,n-len(chosen.get(k,[]))) for k,n in quotas.items()}} if quotas else {})}
