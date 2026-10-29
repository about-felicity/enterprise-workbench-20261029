"""Conservative visible UI auth verdicts. Answer prose is not an account warning."""
import re
import xml.etree.ElementTree as ET

BLOCKED={'login_required','risk_blocked','verification_required'}
RISK=re.compile(r'(?:账号|帐号|账户).{0,20}(?:封禁|被封|封号|冻结|禁用|禁言|禁聊|限制|暂停|异常|风控|风险|无法使用|无法访问)|(?:account).{0,24}(?:banned|suspended|disabled|restricted|muted)|请求过于频繁|操作过于频繁|异常活动|已被封禁|已被禁用|已被禁言|风控|检测到.{0,10}(?:异常操作|异常请求)',re.I)
RESTRICTION_UNTIL=re.compile(r'(?:禁言|封禁|限制|暂停)(?:至|到|直到)\s*(\d{4})\s*(?:年|[-/.])\s*(\d{1,2})\s*(?:月|[-/.])\s*(\d{1,2})\s*日?\s*(\d{1,2})\s*[:：]\s*(\d{2})')
VERIFY=re.compile(r'安全验证|滑动验证|拖动滑块|请完成验证|人机验证|captcha|verify.{0,12}(?:identity|human)',re.I)
LOGIN={'Log in','Login','Sign in','Log in / Sign up','登录','登录/注册','验证码登录','手机验证码登录','密码登录','Welcome to DeepSeek','欢迎使用 DeepSeek'}

def classify_ui(xml,account_present,package='com.deepseek.chat'):
 root=ET.fromstring(xml);parents={c:p for p in root.iter() for c in p}
 nodes=[n for n in root.iter('node') if n.get('package')==package]
 texts={n.get('text','').strip() for n in nodes}
 modes=bool(texts & {'深度思考','智能搜索','Search','DeepThink','联网搜索'})
 editors=[n for n in nodes if n.get('class')=='android.widget.EditText' and n.get('password')!='true']
 composer=modes and bool(editors or '发消息或按住说话' in texts)
 def modal(n):
  while n is not None:
   marker=(n.get('class','')+' '+n.get('resource-id','')).lower()
   if any(k in marker for k in ('dialog','alerttitle','android:id/message')):return True
   n=parents.get(n)
  return False
 for n in nodes:
  text=n.get('text','').strip()
  if text and (modal(n) or not composer):
   if RISK.search(text):
    muted='禁言' in text or bool(re.search(r'account.{0,24}muted',text,re.I))
    result={'status':'risk_blocked','risk_reason':'account_muted' if muted else 'account_restricted',
            'message':'检测到账号禁言，已登录但当前无法正常提问；不能判定登录成功' if muted else '检测到账号限制或封禁提示，尚未通过登录校验，请在投屏中处理或更换账号'}
    until=RESTRICTION_UNTIL.search(text)
    if until:
     try:
      from datetime import datetime
      value=datetime(*map(int,until.groups())).strftime('%Y-%m-%d %H:%M')
      result.update(restriction_until_display=value,restriction_until_timezone='unspecified')
      result['message']+='；App提示限制至 '+value+'，到期后仍需实际复核'
     except ValueError:pass
    return result
   if VERIFY.search(text):return {'status':'verification_required','message':'检测到平台人工验证，完成验证并正常进入对话页后才会恢复任务'}
 if any(modal(n) and n.get('text','').strip() for n in nodes):
  return {'status':'verification_required','message':'App仍有待处理的对话提示，请在投屏中处理后再校验；尚未判定正常登录'}
 if texts & LOGIN or (not composer and any(k in ' '.join(texts) for k in ('手机号','邮箱登录','验证码','Phone number','Email address','登录或注册'))):
  return {'status':'login_required','message':'DeepSeek登录已失效，请点击登录投屏完成登录'}
 if account_present and composer:return {'status':'ready','message':'账号及对话界面正常，当前未发现阻塞性风险提示'}
 return {'status':'unknown','message':'尚未确认正常登录，请返回对话页；不会把不明确状态当作登录成功'}
