"""Read the current App UI without navigating or submitting any question."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent/'tools'))
from wechat_qr_compat import validate


def check():
    validate()
    os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
    import uiautomator2 as u2
    d=u2.connect('127.0.0.1:5559')
    if d.app_current().get('package')!='com.tencent.hunyuan.app.chat':
        return {'status':'unknown','message':'元宝不在前台，保留当前界面；未发送问题'}
    if any(d(text=text).exists for text in ('登录','安全验证','微信扫码登录','人脸识别验证','登录即可体验更多功能')):
        return {'status':'login_required','message':'元宝当前需要本人登录或安全验证；未发送问题'}
    if d(description='新建对话').exists or d(textMatches=r'Hi[，,].+').exists:
        return {'status':'locally_logged_in','message':'元宝本机已登录；服务端有效性以实际采集为准；未发送问题'}
    return {'status':'unknown','message':'元宝当前页面无法确认本机登录；未发送问题'}


if __name__=='__main__':
    try:value=check()
    except Exception as error:value={'status':'unknown','message':'校验未完成；未发送问题','error_kind':type(error).__name__}
    print(json.dumps(value,ensure_ascii=False))
