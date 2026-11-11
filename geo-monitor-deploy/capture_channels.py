"""Display names and journal fields for the capture control plane."""
import json

NAMES = {
    **{f'doubao{i}': f'豆包 · 安卓 {i:02d}' for i in range(1, 5)},
    'deepseek': 'DeepSeek · 服务端安卓',
    'deepseek2': 'DeepSeek · 服务端安卓 02',
    'wenxin_card': '文心 · 网页卡片',
    'baidu_ai': '百度 · 网页卡片',
    'yuanbao': '腾讯元宝 · 安卓',
}


def channel_name(model, backend=None):
    if model in ('deepseek', 'deepseek2'):
        if backend == 'desktop_extension':
            return 'DeepSeek · 本机插件'
        if backend == 'browser_extension':
            return 'DeepSeek · 服务端浏览器' + (' 02' if model == 'deepseek2' else '')
    return NAMES[model]


def log_channel(model, event, batch=None, *, backend=None, **fields):
    print(json.dumps({'channel_id': model, 'channel_name': channel_name(model, backend),
                      'event': event, 'batch': batch, **fields}, ensure_ascii=False), flush=True)
