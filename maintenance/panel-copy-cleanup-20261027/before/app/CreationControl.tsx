"use client";
import { useEffect, useRef, useState } from "react";
import { dashboardBasePath } from "./dashboardPaths";

export function CreationControl() {
  const frame=useRef<HTMLIFrameElement>(null);
  const [source,setSource]=useState("");
  const [height,setHeight]=useState(1300);
  useEffect(()=>{
    setSource(`${dashboardBasePath()}/api/geo-creation/ui`);
    const receive=(event:MessageEvent)=>{
      if(event.origin!==location.origin || event.source!==frame.current?.contentWindow || event.data?.type!=="geo-creation:layout")return;
      if(Number.isFinite(event.data.height))setHeight(Math.max(700,Math.min(24000,event.data.height)));
    };
    addEventListener("message",receive);return()=>removeEventListener("message",receive);
  },[]);
  return <section className="geo-capture-integrated" aria-label="GEO内容创作控制">
    <div className="geo-capture-caption"><p>专用素材采集、创作与成稿下载；专用数据独立保存，不计入 GEO 监测。</p><a href={`${dashboardBasePath()}/api/geo-creation/ui`} target="_blank" rel="noreferrer">独立窗口 ↗</a></div>
    {source&&<iframe ref={frame} title="GEO 内容创作控制台" src={source} style={{height}}/>}
  </section>;
}
