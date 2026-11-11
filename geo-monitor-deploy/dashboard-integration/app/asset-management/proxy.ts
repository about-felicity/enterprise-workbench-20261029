import { themedDocument } from "../workbenchTheme.mjs";

/** Same-origin gateway to the private asset-management service. */
const upstream = "http://127.0.0.1:8001";
const mount = "/asset-management";

async function proxy(request: Request) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/^\/geo_monitor(?=\/)/, "");
  if (path !== mount && !path.startsWith(mount + "/")) return new Response(null, {status: 404});
  const suffix = path.slice(mount.length) || "/";
  // Serve only the UI and its API; never proxy arbitrary filesystem paths.
  if (suffix !== "/" && suffix !== "/index.html" && !suffix.startsWith("/api/") && !suffix.startsWith("/vendor/")) {
    return new Response(null, {status: 404});
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method)) {
    const expected = request.headers.get("X-Forwarded-Prefix") === "/geo_monitor"
      && request.headers.get("X-Forwarded-Proto") === "https"
      ? `https://${url.host}` : url.origin;
    const origin = request.headers.get("Origin");
    if ((origin && origin !== expected) || request.headers.get("Sec-Fetch-Site") === "cross-site") {
      return Response.json({detail: "请从企业工作台提交请求"}, {status: 403});
    }
  }
  const headers = new Headers();
  for (const name of ["Authorization", "Content-Type", "Accept"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  try {
    const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
    const response = await fetch(upstream + suffix + url.search, {
      method: request.method, headers, body, redirect: "manual", cache: "no-store",
      signal: AbortSignal.timeout(60000),
    });
    const output = new Headers({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "SAMEORIGIN"});
    for (const name of ["Content-Type", "Content-Disposition", "WWW-Authenticate", "Allow"]) {
      const value = response.headers.get(name);
      if (value) output.set(name, value);
    }
    if (request.method === "GET" && (suffix === "/" || suffix === "/index.html") &&
        response.ok && output.get("Content-Type")?.startsWith("text/html")) {
      const page = (await response.text()).replace('<p class="text-gray-500 text-sm mt-1">设备管理 · 员工管理 · 资产追踪</p>', "");
      return new Response(themedDocument(page, "assets", request.url),
        {status: response.status, headers: output});
    }
    return new Response(response.body, {status: response.status, headers: output});
  } catch {
    return Response.json({detail: "资产管理服务暂时不可用，请稍后重试"}, {status: 502, headers: {"Cache-Control": "no-store"}});
  }
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
