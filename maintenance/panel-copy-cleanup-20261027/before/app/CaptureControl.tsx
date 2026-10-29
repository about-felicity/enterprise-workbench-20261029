"use client";

import { useEffect, useRef, useState } from "react";
import { dashboardBasePath } from "./dashboardPaths";

const channels = new Set(["doubao1", "doubao2", "deepseek", "deepseek2", "wenxin_card", "baidu_ai", "yuanbao"]);

export function CaptureControl() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [source, setSource] = useState("");
  const [height, setHeight] = useState(1120);
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState("doubao1");

  useEffect(() => {
    const channel = window.location.hash.split("/")[1] || "doubao1";
    setSource(`${dashboardBasePath()}/api/geo-capture/ui#${channels.has(channel) ? channel : "doubao1"}`);
    setChannel(channels.has(channel) ? channel : "doubao1");
    const receive = (event: MessageEvent) => {
      if (event.origin !== window.location.origin || event.source !== frame.current?.contentWindow || event.data?.type !== "geo-capture:layout") return;
      if (Number.isFinite(event.data.height)) setHeight(Math.max(680, Math.min(12000, Math.ceil(event.data.height))));
      if (channels.has(event.data.channel)) {
        setChannel(event.data.channel);
        const hash = `#capture/${event.data.channel}`;
        if (window.location.hash !== hash) window.history.replaceState(null, "", hash);
      }
    };
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, []);

  return <section className="geo-capture-integrated" aria-label="无头采集任务控制">
    <div className="geo-capture-caption"><p>双豆包、元宝、DeepSeek、文心与百度共用任务管理，实时核对 GEO 回传。</p><a href={`${dashboardBasePath()}/api/geo-capture/ui#${channel}`} target="_blank" rel="noreferrer">独立窗口 ↗</a></div>
    {loading && <p className="geo-capture-loading" role="status">正在连接采集服务…</p>}
    {source && <iframe ref={frame} title="GEO 六通道采集控制台" src={source} style={{ height }} onLoad={() => setLoading(false)} />}
  </section>;
}
