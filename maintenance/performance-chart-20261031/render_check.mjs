import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";
import assert from "node:assert/strict";
const server = await createServer({ configFile: false, root: "/dashboard", server: { middlewareMode: true }, appType: "custom", oxc: { jsx: { runtime: "automatic" } } });
try {
  const { PerformanceTrend } = await server.ssrLoadModule("/app/PerformanceTrend.tsx");
  const response = await fetch("http://127.0.0.1:8765/api/performance?month=2026-10&as_of=2026-10-31", { signal: AbortSignal.timeout(60000) });
  assert.equal(response.status, 200);
  const data = await response.json();
  for (const person of data.people) {
    const html = renderToStaticMarkup(React.createElement(PerformanceTrend, { name: person.name, days: person.daily, selectedDate: person.current.date, onSelect() {} }));
    assert.equal((html.match(/data-series=/g) || []).length, 5);
    assert.equal((html.match(/class="performance-trend-hit"/g) || []).length, person.daily.length);
    assert(html.includes('aria-label="选择绩效计算日期"'));
    assert(!html.includes("NaN") && !html.includes("Infinity"));
    assert(html.includes("2026-10-31"));
  }
  const one = [{date:"2026-10-31",score:null,scores:{traffic:null,budget:null,mention:null,values:100},provisional:true}];
  const empty = renderToStaticMarkup(React.createElement(PerformanceTrend,{name:"缺失数据",days:one,selectedDate:"2026-10-31",onSelect(){}}));
  assert(empty.includes("待补数据") && !empty.includes("NaN"));
  assert.equal(renderToStaticMarkup(React.createElement(PerformanceTrend,{name:"空月份",days:[],selectedDate:"",onSelect(){}})),"");
  console.log("CHART_RENDER_OK five employees; five series; all date targets; missing/single/empty data");
} finally { await server.close(); }
