/** Fixed creation-only upstream. Public authentication remains at the GEO mount. */
const upstream="http://127.0.0.1:8804";
const prefix="/api/geo-creation/";
function error(status:number,message:string){return Response.json({ok:false,message},{status,headers:{"Cache-Control":"no-store"}})}
async function proxy(request:Request){
  const url=new URL(request.url);
  if(!["192.168.31.106","127.0.0.1","localhost","1any.top"].includes(url.hostname))return error(403,"访问地址不正确");
  const publicMount=url.hostname==="1any.top",mount=publicMount?"/geo_monitor":"",origin=publicMount?"https://1any.top":url.origin;
  if(publicMount&&(request.headers.get("X-Forwarded-Prefix")!==mount||request.headers.get("X-Forwarded-Proto")!=="https"))return error(403,"请通过GEO公网入口访问");
  const path=url.pathname.startsWith(prefix)?url.pathname.slice(prefix.length):"",write=request.method==="POST";
  if(write?!/^control\/(new|pause|resume|balance|materials_settings|materials_pause|materials_resume|kb_import|kb_save|kb_upload|kb_edit|product_image_upload|plan_save|plan_delete|day_pause|day_resume)$/.test(path):!["ui","panel","uploads","status","catalog","download","product_image"].includes(path))return error(404,"创作接口不存在");
  if(write&&(request.headers.get("Origin")!==origin||request.headers.get("Sec-Fetch-Site")==="cross-site"))return error(403,"请求来源不正确");
  const headers:Record<string,string>={},cookie=(request.headers.get("Cookie")||"").match(/(?:^|;\s*)geo_dashboard_creation=([a-f0-9]{64})(?:;|$)/);
  if(cookie)headers.Cookie=`geo_creation=${cookie[1]}`;
  let body:string|undefined;
  if(write){
    const csrf=request.headers.get("X-CSRF-Token")||"",id=request.headers.get("X-Action-Id")||"";
    if(!/^[a-f0-9]{64}$/.test(csrf)||!/^[a-f0-9]{32}$/.test(id)||request.headers.get("Content-Type")?.split(";")[0]!=="application/json")return error(400,"控制请求格式不正确");
    body=await request.text();if(new TextEncoder().encode(body).length>(["control/kb_import","control/kb_upload","control/product_image_upload"].includes(path)?7_100_000:1_100_000))return error(413,"资料过大");
    Object.assign(headers,{Origin:upstream,"Content-Type":"application/json","X-CSRF-Token":csrf,"X-Action-Id":id});
  }
  const query=["download","product_image"].includes(path)?url.search:"";
  try{
    const response=await fetch(upstream+(path==="ui"?"/":"/api/"+path)+query,{method:request.method,headers,body,redirect:"error",cache:"no-store",signal:AbortSignal.timeout(60000)});
    const output=new Headers({"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","X-Frame-Options":"SAMEORIGIN","Content-Security-Policy":"frame-ancestors 'self'","Content-Type":response.headers.get("Content-Type")||"application/json; charset=utf-8"});
    const setCookie=response.headers.get("Set-Cookie")?.match(/(?:^|;\s*)geo_creation=([a-f0-9]{64})(?:;|$)/);
    if(setCookie)output.set("Set-Cookie",`geo_dashboard_creation=${setCookie[1]}; HttpOnly; SameSite=Strict; Path=${mount}/api/geo-creation; Max-Age=21600${publicMount?"; Secure":""}`);
    for(const name of ["Content-Disposition","X-Content-SHA256"])if(response.headers.has(name))output.set(name,response.headers.get(name)!);
    if(path==="ui"&&response.ok){const html=(await response.text()).replace("const API='/api/';",`const API='${mount}/api/geo-creation/';`);return new Response(html,{status:response.status,headers:output})}
    // DOCX must stay byte-for-byte identical; text decoding corrupts ZIP bytes.
    return new Response(await response.arrayBuffer(),{status:response.status,headers:output});
  }catch{return error(503,"创作服务暂时不可用；后台任务保留，请稍后刷新")}
}
export async function GET(request:Request){return proxy(request)}
export async function POST(request:Request){return proxy(request)}
