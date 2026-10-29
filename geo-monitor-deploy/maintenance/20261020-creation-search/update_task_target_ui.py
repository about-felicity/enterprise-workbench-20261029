from pathlib import Path
base=Path(__file__).resolve().parents[2]/'creation'
field='<label for="planTarget">本任务每次执行成稿目标（可选）</label><input id="planTarget" type="number" min="1" max="100" placeholder="留空沿用每题每类篇数" oninput="planDirty=true;scheduleSummary()"><small>填写后汇总所有问题的当天素材，去重后按任务总篇数分配，优先兼顾科普与排行；不足时显示缺口。</small>'
for name in ('panel.html','wizard_sections.html'):
 path=base/name;text=path.read_text(encoding='utf8');needle='<label for="planCount">'
 assert text.count(needle)==1
 if 'id="planTarget"' not in text:text=text.replace(needle,field+needle)
 path.write_text(text,encoding='utf8')
for name in ('panel.html','wizard.js'):
 path=base/name;text=path.read_text(encoding='utf8')
 changes={
 "max_per_category:Number($('planCount').value),enabled:":"max_per_category:Number($('planCount').value),article_target:Number($('planTarget').value)||0,enabled:",
 "$('planCount').value=p.max_per_category??'';":"$('planCount').value=p.max_per_category??'';$('planTarget').value=p.article_target||'';",
 "const creation=(t?.task_type||p.task_type)==='capture_only'?":"const outputTarget=Number(t?.article_target||p.article_target)||0;const creation=(t?.task_type||p.task_type)==='capture_only'?",
 ":bar('文章创作',writing,questions,`${writing} / ${questions} 个问题完成 · ${t?.articles||0} 篇成稿`);":":outputTarget?bar('文章创作',Math.min(outputTarget,t?.articles||0),outputTarget,`${t?.articles||0} / ${outputTarget} 篇已审稿成稿`):bar('文章创作',writing,questions,`${writing} / ${questions} 个问题完成 · ${t?.articles||0} 篇成稿`);",
 " · 每题每类最多${p.max_per_category}篇":" · ${p.article_target?'每次目标'+p.article_target+'篇':'每题每类最多'+p.max_per_category+'篇'}",
 "n+'个问题，每类最多'+count+'篇，排行类与科普类合计最多'+n*count*2+'篇。'":"Number($('planTarget').value)>0?'汇总'+n+'个问题的独立素材，本次目标'+Number($('planTarget').value)+'篇，按真实体裁分配。':n+'个问题，每类最多'+count+'篇，排行类与科普类合计最多'+n*count*2+'篇。'",
 }
 for old,new in changes.items():
  assert text.count(old)>=1,(name,old,text.count(old));text=text.replace(old,new)
 text=text.replace(" }return true;\n}\nfunction scheduleSummary", " }if($('planTarget').value&&!$('planTarget').checkValidity()){message('任务总篇数应为1至100篇',true);return false}return true;\n}\nfunction scheduleSummary")
 path.write_text(text,encoding='utf8')
panel=base/'panel.html';text=panel.read_text(encoding='utf8');text=text.replace("const studioStates={", "const studioStates={insufficient_materials:'素材不足，已保留合格成稿',")
panel.write_text(text,encoding='utf8')
