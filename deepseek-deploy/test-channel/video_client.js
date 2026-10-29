// scrcpy-video start
let videoConnection=null,latestJpeg=null,painting=false;
function stopVideo(){if(videoConnection)videoConnection.abort();videoConnection=null;latestJpeg=null}
function jpegParser(deliver){
 let pending=new Uint8Array(0);
 return chunk=>{
  const merged=new Uint8Array(pending.length+chunk.length);merged.set(pending);merged.set(chunk,pending.length);pending=merged;
  if(pending.length>4000000)throw Error('投屏帧过大，请重连');
  for(;;){
   let begin=-1,end=-1;
   for(let i=0;i<pending.length-1;i++)if(pending[i]===255&&pending[i+1]===216){begin=i;break}
   if(begin<0){pending=pending.slice(-1);return}
   for(let i=begin+2;i<pending.length-1;i++)if(pending[i]===255&&pending[i+1]===217){end=i+2;break}
   if(end<0){pending=pending.slice(begin);return}
   deliver(pending.slice(begin,end));pending=pending.slice(end);
  }
 };
}
async function paintLatest(connection){
 if(painting)return;painting=true;
 try{
  while(latestJpeg&&videoConnection===connection){
   const bytes=latestJpeg;latestJpeg=null;
   const bitmap=await createImageBitmap(new Blob([bytes],{type:'image/jpeg'}));
   try{if(videoConnection!==connection)return;if(screen.width!==bitmap.width||screen.height!==bitmap.height){screen.width=bitmap.width;screen.height=bitmap.height}screen.getContext('2d',{alpha:false}).drawImage(bitmap,0,0);screen.naturalWidth=bitmap.width}finally{bitmap.close()}
  }
 }finally{painting=false;if(latestJpeg&&videoConnection&&!finished)paintLatest(videoConnection)}
}
async function startCanvasVideo(url){
 stopVideo();const connection=new AbortController();videoConnection=connection;
 try{
  const response=await fetch(url,{cache:'no-store',signal:connection.signal});if(!response.ok||!response.body)throw Error('投屏连接未就绪');
  const reader=response.body.getReader();
  const parse=jpegParser(bytes=>{latestJpeg=bytes;paintLatest(connection).catch(()=>{message.textContent='画面解码失败，请重连画面'})});
  try{while(videoConnection===connection){const {done,value}=await reader.read();if(done)throw Error('投屏连接已中断');parse(value)}}finally{reader.cancel().catch(()=>{})}
 }catch(e){if(connection.signal.aborted||videoConnection!==connection)return;streamFlow='';if(waiting&&!finished){message.textContent='投屏连接中断，正在重连画面…';setTimeout(connectStream,1500)}}
}
// scrcpy-video end
