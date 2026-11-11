import { themedDocument } from "../../workbenchTheme.mjs";

const backend = "http://127.0.0.1:8016";
const permittedReads = new Set(["/", "/api/scan", "/api/download", "/api/stream", "/api/zip/progress", "/api/zip/download"]);
const localHosts = new Set(["127.0.0.1", "localhost", "192.168.31.106"]);
const publicHosts = new Set(["ifbcy.com", "1any.top"]);

function error(status: number, detail: string) {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

async function proxy(request: Request) {
  const url = new URL(request.url);
  const publicHost = publicHosts.has(url.hostname);
  if (!publicHost && !localHosts.has(url.hostname)) return error(403, "请从工作台进入素材库");
  if (publicHost && request.headers.get("X-Forwarded-Proto") !== "https") return error(403, "请从工作台进入素材库");
  const prefix = request.headers.get("X-Forwarded-Prefix");
  if (prefix && prefix !== "/geo_monitor") return error(403, "访问路径不正确");
  const match = url.pathname.match(/^(?:\/geo_monitor)?\/material-library(\/.*)?$/);
  if (!match) return error(404, "素材库页面不存在");
  const path = match[1] || "/";
  const write = request.method === "POST";
  if (write ? path !== "/api/zip/start" : !permittedReads.has(path)) return error(404, "素材库接口不存在");
  if (path !== "/" && request.headers.get("Sec-Fetch-Site") === "cross-site") return error(403, "请求来源不正确");
  if (write && request.headers.get("Origin") !== (publicHost ? `https://${url.hostname}` : url.origin)) {
    return error(403, "请求来源不正确");
  }

  let body: string | undefined;
  if (write) {
    if (request.headers.get("Content-Type")?.split(";")[0] !== "application/json") return error(415, "需要 JSON 请求");
    const reader = request.body?.getReader();
    if (!reader) return error(400, "请选择要下载的素材");
    const decoder = new TextDecoder();
    let bytes = 0;
    body = "";
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.length;
      if (bytes > 32_768) {
        await reader.cancel();
        return error(413, "选择的素材路径过多，请分批下载");
      }
      body += decoder.decode(chunk.value, { stream: true });
    }
    body += decoder.decode();
  }

  const requestHeaders = new Headers({ "Accept-Encoding": "identity" });
  if (write) requestHeaders.set("Content-Type", "application/json");
  for (const key of ["Range", "If-None-Match", "If-Modified-Since"]) {
    const value = request.headers.get(key);
    if (value) requestHeaders.set(key, value);
  }
  try {
    const response = await fetch(backend + path + (path === "/" ? "" : url.search), {
      method: request.method, headers: requestHeaders, body, cache: "no-store", redirect: "error",
      signal: request.signal,
    });
    const headers = new Headers({ "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "SAMEORIGIN" });
    for (const key of ["Content-Type", "Content-Length", "Content-Disposition", "Content-Range", "Accept-Ranges", "ETag", "Last-Modified"]) {
      const value = response.headers.get(key);
      if (value) headers.set(key, value);
    }
    if (path !== "/") headers.set("Content-Security-Policy", "sandbox; default-src 'none'");
    else headers.set("Content-Security-Policy", "default-src 'self' data: blob:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'self'; object-src 'none'; base-uri 'none'");
    if (path === "/" && response.ok && headers.get("Content-Type")?.startsWith("text/html")) {
      for (const key of ["Content-Length", "ETag", "Last-Modified"]) headers.delete(key);
      const page = (await response.text()).replace('<p class="managed-readonly">移动硬盘 · 浏览和下载</p>', "");
      return new Response(themedDocument(page, "materials", request.url), { status: response.status, headers });
    }
    return new Response(response.body, { status: response.status, headers });
  } catch {
    if (path === "/") {
      return new Response("<!doctype html><html lang=zh-CN><meta charset=utf-8><title>素材库</title><h1>素材硬盘暂时不可用</h1><p>确认移动硬盘已连接后刷新此页。</p><p><a href='./'>返回工作台</a></p></html>", {
        status: 503, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
      });
    }
    return error(503, "素材硬盘暂时不可用，请确认已连接后重试");
  }
}

export const dynamic = "force-dynamic";
export const GET = proxy;
export const POST = proxy;
