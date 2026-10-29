import os,json
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
print(json.dumps({'wechat_login_qr':bool(d(text='微信扫码登录').exists),'security_page':bool(d(text='安全验证').exists),'face_verification':bool(d(text='人脸识别验证').exists),'official_face_qr_note':bool(d(text='请用手机微信扫描此官方验证二维码，按提示完成本人核验').exists)}))
