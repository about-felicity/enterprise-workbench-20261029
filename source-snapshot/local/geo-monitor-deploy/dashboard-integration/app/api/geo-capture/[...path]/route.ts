/** Fixed local control gateway. Credentials stay in the original receiver. */
const upstream = "http://127.0.0.1:8803";
const prefix = "/api/geo-capture/";
const cookieName = "geo_dashboard_capture";
const controls = /^(control\/schedule|control\/(doubao1|doubao2|deepseek|deepseek2|wenxin_card|baidu_ai|yuanbao)\/(settings|new|pause|resume|stop|login|login_sync|login_open)|login\/(?:(deepseek|deepseek2|deepseek_test)\/)?input|login\/deepseek_test\/open)$/;

const embedStyle = `
body{background:transparent;min-height:0}.app{display:block;min-height:0}
aside{background:transparent;padding:0;color:#253b34}.brand,.nav-label,.sidebar-foot,.top{display:none}
.model-nav{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.nav-item{background:white;border:1px solid #dfe7e6;color:#253b34;padding:12px 10px;min-width:0;gap:8px}
.nav-item strong{font-size:13px}.nav-item small{color:#73847c;font-size:10px}.nav-icon{background:#eef5f0;color:#267354;flex-shrink:0}
.nav-item.selected{background:#eaf5ed;border-color:#75a78b}.nav-item:hover:not(:disabled){background:#eef6f0;border-color:#a1bfac}
.dot{flex-shrink:0}.dot.good{background:#32966a}.dot.warn{background:#ca983b}
main{max-width:none;padding:0}.summary{margin:18px 0;gap:12px}.card{padding:22px}.workspace{grid-template-columns:minmax(0,1.1fr) minmax(300px,.9fr);gap:16px}
.footer{margin-bottom:0;padding-bottom:8px}.history-grid{grid-template-columns:minmax(0,1.25fr) minmax(0,.75fr)}
@media(max-width:900px){.workspace{grid-template-columns:1fr}.history-grid{grid-template-columns:1fr}}
@media(max-width:650px){.model-nav{grid-template-columns:repeat(2,minmax(0,1fr))}.model-nav>.nav-item:last-child{grid-column:span 2}.summary{grid-template-columns:repeat(2,1fr)}.summary>div{padding:12px}.card{padding:17px}.nav-item small{font-size:11px}}
`;
const embedScript = `<script>(()=>{let last='';const publish=()=>{const value={type:'geo-capture:layout',height:Math.ceil(document.body.getBoundingClientRect().height)+12,channel:location.hash.slice(1)||'doubao1'};const key=JSON.stringify(value);if(key!==last){last=key;parent.postMessage(value,location.origin)}};new ResizeObserver(publish).observe(document.body);addEventListener('hashchange',publish);addEventListener('load',publish);setInterval(publish,1000);publish()})()</script>`;

function error(status: number, message: string) {
  return Response.json({ ok: false, message }, { status, headers: { "Cache-Control": "no-store" } });
}

async function proxy(request: Request) {
  const url = new URL(request.url);
  if (!["192.168.31.106", "127.0.0.1", "localhost", "1any.top"].includes(url.hostname)) return error(403, "请使用 GEO 配置的访问地址");
  const publicMount = url.hostname === "1any.top";
  if (publicMount && (request.headers.get("X-Forwarded-Prefix") !== "/geo_monitor" || request.headers.get("X-Forwarded-Proto") !== "https")) return error(403, "公网入口配置不正确，请通过 GEO 面板访问");
  const mount = publicMount ? "/geo_monitor" : "";
  const origin = publicMount ? "https://1any.top" : url.origin;
  const path = url.pathname.startsWith(prefix) ? url.pathname.slice(prefix.length) : "";
  const write = request.method === "POST";
  if (write ? !controls.test(path) : !(["panel", "status", "ui"].includes(path) || /^login\/(?:(deepseek|deepseek2|deepseek_test)\/)?(ui|state|frame|stream)$/.test(path))) return error(404, "采集接口不存在");
  if (write && (request.headers.get("Origin") !== origin || request.headers.get("Sec-Fetch-Site") === "cross-site")) return error(403, "请求来源校验失败，请从控制面板操作");
  const headers: Record<string, string> = {};
  const cookie = (request.headers.get("Cookie") || "").match(/(?:^|;\s*)geo_dashboard_capture=([a-f0-9]{64})(?:;|$)/);
  if (cookie) headers.Cookie = `geo_control=${cookie[1]}`;
  let body: string | undefined;
  if (write) {
    const csrf = request.headers.get("X-CSRF-Token") || "";
    const id = request.headers.get("X-Action-Id") || "";
    if (!/^[a-f0-9]{64}$/.test(csrf) || !/^[a-f0-9]{32}$/.test(id) || request.headers.get("Content-Type")?.split(";")[0] !== "application/json") return error(400, "控制请求格式不正确");
    body = await request.text();
    if (new TextEncoder().encode(body).length > 1_100_000) return error(413, "问题清单过大");
    headers["Content-Type"] = "application/json";
    headers.Origin = upstream;
    headers["X-CSRF-Token"] = csrf;
    headers["X-Action-Id"] = id;
  }
  try {
    const streaming = path.endsWith("/stream");
    if (streaming && !/^[a-f0-9]{32}$/.test(url.searchParams.get("flow") || "")) return error(400, "登录投屏编号无效");
    const query = streaming ? "?flow=" + url.searchParams.get("flow") : path === "panel" && url.searchParams.has("date") ? "?date=" + encodeURIComponent(url.searchParams.get("date") || "") : "";
    const response = await fetch(upstream + (path === "ui" ? "/" : "/api/" + path) + query, {
      method: request.method, headers, body, redirect: "error", cache: "no-store", signal: streaming ? request.signal : AbortSignal.timeout(35000),
    });
    const outputHeaders = new Headers({ "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "SAMEORIGIN", "Content-Security-Policy": "frame-ancestors 'self'" });
    outputHeaders.set("Content-Type", response.headers.get("Content-Type") || "application/json; charset=utf-8");
    const setCookie = response.headers.get("Set-Cookie");
    if (setCookie) {
      const value = setCookie.match(/(?:^|;\s*)geo_control=([a-f0-9]{64})(?:;|$)/);
      if (value) outputHeaders.set("Set-Cookie", `${cookieName}=${value[1]}; HttpOnly; SameSite=Strict; Path=${mount}/api/geo-capture; Max-Age=21600${publicMount ? "; Secure" : ""}`);
    }
    if (streaming && response.ok) {
      outputHeaders.set("X-Accel-Buffering", "no");
      return new Response(response.body, { status: response.status, headers: outputHeaders });
    }
    if (path.endsWith("/frame")) return new Response(await response.arrayBuffer(), { status: response.status, headers: outputHeaders });
    let output = await response.text();
    if (path.startsWith("login/") && path.endsWith("/ui") && response.ok) {
      output = output.replaceAll("'/api/login/'", `'${mount}/api/geo-capture/login/'`).replaceAll("'/api/panel'", `'${mount}/api/geo-capture/panel'`);
    }
    if (path === "ui" && response.ok) {
      output = output.replaceAll("'/api/panel'", `'${mount}/api/geo-capture/panel'`).replaceAll("'/api/control/'", `'${mount}/api/geo-capture/control/'`).replaceAll("'/api/login/'", `'${mount}/api/geo-capture/login/'`).replaceAll("'/api/login/ui'", `'${mount}/api/geo-capture/login/ui'`)
        .replace("</head>", `<style>${embedStyle}</style></head>`).replace("</body>", embedScript + "</body>");
    }
    return new Response(output, { status: response.status, headers: outputHeaders });
  } catch {
    return error(503, "采集控制服务暂时不可用，请稍后刷新；正在运行的任务仍由后台管理");
  }
}

export async function GET(request: Request) { return proxy(request); }
export async function POST(request: Request) { return proxy(request); }
