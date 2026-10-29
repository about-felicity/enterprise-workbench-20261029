from pathlib import Path
import re,shutil
D=Path(__file__).resolve().parent;out=D/'app';out.mkdir(exist_ok=True)
s=(D/'before/app/Dashboard.tsx').read_text('utf-8')
s=s.replace('import WorkbenchLogo from "./WorkbenchLogo";\n"use client";','"use client";\n\nimport WorkbenchLogo from "./WorkbenchLogo";')
for cls in ['owned-video-category-note','owned-product-board-note','common-owned-note']:
 s,n=re.subn(r'\s*<p className="'+cls+r'">.*?</p>','',s,flags=re.S);assert n==1,cls
for text in ['任意1轮回答正文确认推荐，即记为上榜','点击左侧模型可进入单模型视角','文章、视频、社交与电商']:
 s=s.replace('note="'+text+'"','')
for text in ['仅统计所选自然月；每个“产品 × 模型 × 日期”的提及率等权平均，不受提问次数影响，该模型没数据的日期不计入','跨日累计，仅作样本量参考','比例只以已核验信源为分母；待分析与抓取失败单列，不会误算为未提及']:
 s=s.replace('<small>'+text+'</small>','')
s=s.replace('<span>INTERACTIVE TREND</span>','')
s=re.sub(r'<small>\{historyLoading \? .*?</small>','{historyLoading && <small role="status">趋势加载中…</small>}',s)
s=re.sub(r'\s*<p>\s*选择问题后，这里会用.*?</p>','',s,flags=re.S)
start=s.index('              {!date && analytics.detail_scope?.kind === "latest_day" && (')
end=s.index('              <section className="panel intersection-target-panel">',start)
s=s[:start]+s[end:]
s=s.replace('<span>链接交集对象</span>','').replace('查看自有产品或竞品的跨模型共同信源','跨模型共同信源')
s=re.sub(r'<p>\{sourceIntersectionPending.*?</p>','{sourceIntersectionPending && <p role="status">正在加载信源…</p>}',s,flags=re.S)
s=re.sub(r'\s*<section className="analysis-note panel">\s*<b>准确性与成本口径</b>.*?</section>','',s,flags=re.S)
s=s.replace('{item.analysis_pending_runs} 轮产品复核尚未完成；品牌榜已按回答正文实时统计，产品榜只以已解析轮次为分母，待解析轮次不会误算为未提及。','{item.analysis_pending_runs} 轮待解析')
s=s.replace('<span>COLLECTION WORKSPACE</span>','').replace('每个模型独立配置，互不影响','其他采集通道')
s=re.sub(r'\s*<p>\s*问题清单、账号校验、采集进程、分析与数据文件.*?</p>','',s,flags=re.S)
s=s.replace('先选择一个问题','选择问题').replace('按日采集脉搏','每日采集量')
for text in ['标题本地分词；显示每日 Top 10，便于观察主题升降','状态每 2 秒从采集日志同步','数据通过鉴权后直接写入 PostgreSQL，并自动进入正文、信源、品牌和产品分析。']:
 s=s.replace('<small>'+text+'</small>','')
s=re.sub(r'<small>\{kind === "brand" \? "品牌提及率 = .*?</small>','',s)
s=s.replace('Chrome 启动、账号校验完成后会自动运行采集脚本','启动中…')
(out/'Dashboard.tsx').write_text(s,'utf-8')
for name in ['CreationControl.tsx','CaptureControl.tsx']:
 s=(D/'before/app'/name).read_text('utf-8')
 s=re.sub(r'(<div className="geo-capture-caption">)<p>.*?</p>',r'\1',s)
 (out/name).write_text(s,'utf-8')
s=(D/'before/app/PerformanceBoard.tsx').read_text('utf-8')
s=re.sub(r'\s*<details className="performance-rules">.*?</details>','',s,flags=re.S)
(out/'PerformanceBoard.tsx').write_text(s,'utf-8')
s=(D/'before/app/globals.css').read_text('utf-8')
s+='\n.geo-capture-caption { justify-content: flex-end; padding-top: 0; padding-bottom: 8px; }\n'
(out/'globals.css').write_text(s,'utf-8')

s=(D/'before/creation-panel.html').read_text('utf-8')
# Remove static introductions only; keep IDs and dynamic error/status containers.
s=re.sub(r'<p class="(?:muted|hint)">[^<]*</p>','',s)
s=re.sub(r'<div class="step">[^<]*</div>','',s)
for old,new in {
 '支持 .docx，最大 5MB。保存原文件、上传时间与版本记录；上传不会自动触发分析或创作。上传完成后请告诉助手分析哪些产品。':'支持 .docx，最大 5MB。',
 '支持 JPG、PNG、WebP，每张最大 5MB；支持多选图片或整个文件夹，自动跳过其他文件。记录原文件名、尺寸和上传时间。':'支持 JPG、PNG、WebP，每张最大 5MB。',
 '填写后汇总所有问题的当天素材，去重后按任务总篇数分配，优先兼顾科普与排行；不足时显示缺口。':'',
 '可分别配置排行、测评和科普目标篇数。实际成稿需通过审稿，素材不足会显示缺口。':'',
 '含共享分析费用；达到任务或共享预算上限时保留进度并等待处理。':'',
 '文档中的产品声明、功效数据和专利作为原始资料保存，继续接受事实与审稿检查。':'',
 '排行类和科普类分别最多此篇数，未通过审核的文章不作为成稿。':'',
 '仅使用你提供的资料。原有资料出处和审核限制会保留。':'',
 '专用采集的数据仅供创作使用，不计入大 GEO 监测。':'',
 '成分、规格和有条件的检测摘要按知识库展开。检测摘要保留来源与试验边界；篇数不足时显示缺额，不以另一类别顶替。':'',
 '查看自动识别依据':'识别依据',
 '开始一项新创作':'临时创作',
 '高级操作：用已有素材临时创作，或查看历史单项任务':'临时创作与历史任务',
 '可下载的成稿':'成稿下载',
 '文件完整性校验通过，已开始保存。压缩包请先完整解压，再打开其中的Word。':'下载已开始',
 ' · 账号身份以原文记录为准':'',
 }.items():s=s.replace(old,new)
s=re.sub(r'<div class="hint"><b>3\. 开始后去哪里看？</b>.*?</div>','',s)
s=re.sub(r'<small>\s*</small>','',s)
s=s.replace("const hint=$('wizardFeedback');hint.hidden=false;hint.className='hint';", "const hint=$('wizardFeedback');hint.hidden=!kbDirty;hint.className='hint';")
s=s.replace("n===1?'选择已建好的产品知识库，再配置问题。':n===2?'填写监测问题并选择采集渠道。':'填写执行时间与创作预算，然后保存任务。'", "''")
s=s.replace("'填写三步配置后保存，新任务才会加入队列。'", "''")
s=s.replace("'确认产品、问题、采集时间后保存；素材未完成时自动等待。'", "''")
s=s.replace("'保存任务后按设置执行。素材未齐时等待；达到预算上限保留进度。'", "''")
s=s.replace(' · 与成稿区产品、日期筛选联动；默认查看今天。','').replace('（北京时间），任务队列同时列出未来计划。','（北京时间）')
s=s.replace(' · 产品、任务日期同时筛选下方创作任务','').replace('。成稿不会自动发布。','。')
# IDs remain for existing event handlers, but empty introductory scaffolding is gone.
s=re.sub(r'(<p id="(?:editorMode|wizardFeedback)"[^>]*>)[^<]*(</p>)',r'\1\2',s)
s=s.replace('</head>','<style>body[data-embedded="true"] #workspaceTop h1{display:none}body[data-embedded="true"] main{padding-top:0}#editorMode:empty,#planHint:empty{display:none}</style></head>')
s=s.replace("const API='/api/';", "document.body.dataset.embedded=String(window.parent!==window);\nconst API='/api/';")
(D/'creation-panel.html').write_text(s,'utf-8')

s=(D/'before/capture-panel.html').read_text('utf-8')
for cls in ['side-note','eyebrow']:
 s=re.sub(r'<div class="'+cls+r'">.*?</div>','',s)
s=s.replace('<small>COLLECTION OPS</small>','').replace('采集通道 / CHANNELS','采集通道')
s=re.sub(r'<p(?: class="(?:subtle|hint|form-intro)")?>[^<]*</p>','',s)
s=s.replace('<span>GEO · 模型采集管理</span>','')
s=s.replace('全部校验已通过，可以开始新任务；历史任务与回执保留。','校验通过，可以开始新任务。')
s=s.replace('；超出目标的历史观测仍保留。','。').replace(' 次；超出目标的历史观测仍保留。',' 次。')
s=s.replace('保存后立即生效；后台按今天已入库数量补足目标，不会重跑已完成的数据。','')
(D/'capture-panel.html').write_text(s,'utf-8')
print('Cleaned 5 React/CSS files and 2 embedded pages')
