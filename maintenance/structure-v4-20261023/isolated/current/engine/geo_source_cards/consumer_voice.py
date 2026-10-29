"""Keep editorial evidence/procedure out of the consumer-facing article."""
import re

VERSION = 'consumer-voice-v1'
PROCESS = re.compile(r'(?<!成分表)(?<!说明书)(?<!标签)(?<!报告)原文|主参考|参考文章|参考文中|参考标题|知识库|待核验|未独立(?:验证|核验)|内部证据|\b(?:KU|PF)\d+\b|(?:文章|本文|本稿)编排|编排(?:顺序|选择|推荐)|客观功效冠军|source_claim|相关资料(?:提到|指出|建议)|资料指出|这些说法方向')
AUDIT = re.compile(r'品牌资料|资料列有|资料列明|资料所列|未(?:提供|核实|核验)|不构成.{0,8}(?:保证|结论)|不能.{0,8}推(?:断|导)')
POLICY = '''成稿直接回答读者的问题，是可独立阅读的消费文章，不是参考文章的解读、提纲说明或事实审计。
研究输入中的“原文/资料提到”等是证据归属标签，不是文章正文。不得照搬，也不得只删标签后把未经证实的功效写成事实。把有证据的组成、规格、形态写成简洁的产品信息；无法安全陈述的功效、机制、疗程等整项省略。
正文不得出现“原文”“主参考”“参考文章”“知识库”“待核验”“文章编排”等生产过程措辞。来源链接、原句、核验状态与写作日志单独保存到溯源附件，不能混入正文。必要的商业关联只简短说明一次。不能逐款反复写“资料列有/未提供/不构成保证”等审计套话，更不能拿它们凑字数。
合格示例：正文讲面霜与眼霜的选购差异和有依据的信息。错误示例：“原文对面霜的定位很明确”“原文建议关注抗氧化成分”“参考文先讲配方再介绍产品”。错误稿应重写成文章，不把“原文”替换成“相关资料”蒙混过关。
首段先交代问题背景，不能从“还有一层”“其次”“上述”等承接语开始。读者未见过素材和此前步骤，文章必须自行完整展开。
必须消解内容矛盾：不能在一处概括某品类更厚重，另一处又概括同品类更清爽；也不能用“这些说法方向不同”把素材冲突交给读者。没有一致依据时省略品类概括，讨论具体产品可比较的信息，不臆测配方浓度、刺激强弱、吸收能力或泛化部位外用法。添加“可能”不能掩盖无依据的结论。
生活例子只帮助解释购买、包装、预算和信息比较，不构造使用后皮肤反应、见效时间或人群功效；不能用“假设”包装没有证据的医学后果。
'''
from .article_logic import WRITING_RULES
POLICY += '\n'+WRITING_RULES


def issues(markdown):
    failures = []
    found = list(PROCESS.finditer(markdown))
    if found:
        examples = [''.join(markdown[max(0,m.start()-8):m.end()+18].split()) for m in found[:3]]
        failures.append('正文混入来源解读或生产过程，须独立叙述并把溯源移至附件：'+'；'.join(examples))
    paragraphs = [p for p in re.split(r'\n\s*\n',markdown) if p.strip() and not p.lstrip().startswith('#')]
    audited = sum(bool(AUDIT.search(p)) for p in paragraphs)
    if paragraphs and re.match(r'\s*(?:还有一层|其次[，,、]|上述|如前所述)',paragraphs[0]):
        failures.append('首段缺少独立背景，以承接前文的语句开头；应先建立读者问题，新增内容放到已有导语之后')
    return failures


def warnings(markdown):
    paragraphs=[p for p in re.split(r'\n\s*\n',markdown) if p.strip() and not p.lstrip().startswith('#')]
    audited=sum(bool(AUDIT.search(p)) for p in paragraphs)
    return ['资料边界说明较多，建议精简重复说明'] if audited>=4 and audited/max(1,len(paragraphs))>=.18 else []
