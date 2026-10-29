from pathlib import Path
p=Path('geo-monitor-deploy/deepseek_login.html');s=p.read_text(encoding='utf8')
old="const screen=document.getElementById('screen'),message=document.getElementById('message'),textInput=document.getElementById('textInput');"
new="""const canvasVideo=typeof createImageBitmap==='function'&&typeof ReadableStream==='function';
const screen=(()=>{const original=document.getElementById('screen');if(!canvasVideo)return original;const canvas=document.createElement('canvas');for(const attribute of original.attributes)canvas.setAttribute(attribute.name,attribute.value);canvas.setAttribute('aria-label','DeepSeek scrcpy实时投屏');canvas.naturalWidth=0;original.replaceWith(canvas);return canvas})(),message=document.getElementById('message'),textInput=document.getElementById('textInput');"""
assert old in s;s=s.replace(old,new,1)
idx=s.index('function connectStream()')
s=s[:idx]+Path('deepseek-deploy/test-channel/video_client.js').read_text(encoding='utf8')+'\n'+s[idx:]
old="streamFlow=flow;screen.src=prefix+'stream?flow='+flow+'&t='+Date.now()"
new="streamFlow=flow;const url=prefix+'stream?flow='+flow+'&t='+Date.now();if(canvasVideo)startCanvasVideo(url);else screen.src=url"
assert old in s;s=s.replace(old,new,1)
s=s.replace("screen.removeAttribute('src');","stopVideo();screen.removeAttribute('src');")
p.write_text(s,encoding='utf8')
