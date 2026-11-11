export type VideoLedger = "creator-videos" | "employee-videos" | "paid-media-videos";

const services = {
  "creator-videos": { url: "http://127.0.0.1:8812/works", label: "达人视频" },
  "employee-videos": { url: process.env.GEO_EMPLOYEE_VIDEO_URL || "http://127.0.0.1:8813/works", label: "员工视频" },
  "paid-media-videos": { url: process.env.GEO_PAID_MEDIA_VIDEO_URL || "http://127.0.0.1:8814/works", label: "付费媒体视频" },
};

function error(status: number, message: string) {
  return Response.json({ error: message }, { status, headers: { "Cache-Control": "no-store" } });
}

async function proxy(request: Request, ledger: VideoLedger, body?: ArrayBuffer) {
  const day = new URL(request.url).searchParams.get("day");
  if (day && !/^\d{4}-\d{2}-\d{2}$/.test(day)) return error(400, "数据日期格式不正确");
  const headers = new Headers(body ? { "Content-Type": "application/json" } : undefined);
  try {
    // Read the signed session at the auth service. Ignore identity headers supplied by clients.
    const identity = await fetch(process.env.GEO_VIDEO_AUTH_URL || "http://127.0.0.1:19766/auth", {
      headers: {
        Cookie: request.headers.get("cookie") || "",
        "X-Original-URI": `/geo_monitor/api/geo-capture/${ledger}`,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    const username = identity.headers.get("x-geo-user");
    if (identity.status === 204 && username) {
      headers.set("X-Geo-User", username);
    } else if (ledger === "employee-videos") {
      return error(401, "请先登录工作台");
    } else if (ledger === "paid-media-videos" && identity.status === 403) {
      return error(403, "当前账号无权访问付费媒体视频数据");
    }
    const upstream = services[ledger].url;
    const response = await fetch(day ? `${upstream}?day=${day}` : upstream, {
      method: body ? "POST" : "GET",
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    return new Response(response.body, {
      status: response.status,
      headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
    });
  } catch {
    return error(503, `${services[ledger].label}服务暂时不可用`);
  }
}

export async function getVideos(request: Request, ledger: VideoLedger = "creator-videos") {
  return proxy(request, ledger);
}

export async function postVideos(request: Request, ledger: VideoLedger = "creator-videos") {
  const origin = request.headers.get("origin");
  const fetchSite = request.headers.get("sec-fetch-site");
  // The public reverse proxy terminates HTTPS before forwarding to Next.js.
  const host = request.headers.get("x-forwarded-host") || request.headers.get("host");
  const scheme = request.headers.get("x-forwarded-proto") || new URL(request.url).protocol.slice(0, -1);
  if (!host || !["http", "https"].includes(scheme) || origin !== `${scheme}://${host}` ||
      (fetchSite && fetchSite !== "same-origin")) {
    return error(403, "请从工作台打开并操作");
  }
  const length = Number(request.headers.get("content-length"));
  if (!Number.isInteger(length) || length < 1 || length > 32768) {
    return error(400, "分享文案过长或为空");
  }
  if (request.headers.get("content-type")?.split(";")[0] !== "application/json") {
    return error(400, "需要 JSON 数据");
  }
  const body = await request.arrayBuffer();
  if (body.byteLength !== length) return error(400, "请求长度不正确");
  return proxy(request, ledger, body);
}
