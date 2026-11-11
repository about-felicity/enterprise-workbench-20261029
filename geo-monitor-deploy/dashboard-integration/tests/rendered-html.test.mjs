import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const app = new URL("../app/", import.meta.url);

test("工作台保留视频台账和二级词入口、直达链接及页面样式", async () => {
  const [source, css] = await Promise.all([
    readFile(new URL("Dashboard.tsx", app), "utf8"),
    readFile(new URL("globals.css", app), "utf8"),
  ]);
  const modules = [
    ["creator-videos", "达人视频数据"],
    ["paid-media-videos", "付费媒体视频数据"],
    ["employee-videos", "自有员工视频数据"],
    ["keywords", "二级词监控"],
  ];
  const deepLinks = source.match(/const hashViews[^=]*=\s*\[([^\]]*)\]/)?.[1] || "";
  for (const [id, label] of modules) {
    assert.ok(source.includes(`id: "${id}", label: "${label}"`), `左侧栏缺少${label}`);
    assert.ok(deepLinks.includes(`"${id}"`), `刷新后无法打开${label}`);
  }
  assert.ok(source.includes('view === "paid-media-videos"'));
  assert.ok(source.includes('<CreatorVideos key={view} ledger={view}'));
  assert.ok(source.includes('view === "keywords" && <KeywordMonitoring'));
  assert.match(css, /@import "\.\/CreatorVideos\.css"/);
  assert.match(css, /\.keyword-board-table/);
  assert.match(source, /href="\.\/asset-management"/);
});

test("统一面板由后端模型目录驱动并提供完整分析工作视图", async () => {
  const source = await readFile(new URL("Dashboard.tsx", app), "utf8");
  assert.match(source, /\/api\/models/);
  assert.match(source, /\/api\/analytics/);
  assert.match(source, /模型总览/);
  assert.match(source, /问题对比/);
  assert.match(source, /信源洞察/);
  assert.match(source, /品牌与产品/);
  assert.match(source, /回答审计/);
  assert.match(source, /采集控制/);
  assert.doesNotMatch(source, /modelRegistry/);
  assert.doesNotMatch(source, /item\.id !== "deepseek"/);
  assert.match(source, /const visibleModelCatalog = analytics\.model_catalog;/);
  assert.match(source, /filter\(\(item\) => !model \|\| item\.id === model\)/);
  assert.doesNotMatch(source, /item\.ingest_only \|\| item\.id === model \|\| item\.runs > 0/);
  assert.match(source, /const participatingModelCount = selectedModels\.filter/);
  assert.match(source, /有数据模型 \/ 设备/);
});

test("采集控制包含问题计划、账号校验及启停能力", async () => {
  const [source, control] = await Promise.all([
    readFile(new URL("Dashboard.tsx", app), "utf8"),
    readFile(new URL("CaptureControl.tsx", app), "utf8"),
  ]);
  assert.match(source, /<CaptureControl\s*\/>/);
  assert.match(control, /\/api\/geo-capture\/ui#/);
  assert.match(source, /每行一个，启动前自动保存/);
  assert.match(source, /仅保存问题/);
  assert.match(source, /校验模拟器 \/ 网页账号/);
  assert.match(source, /account-check/);
  assert.match(source, /api\/control\/\$\{modelId\}/);
  assert.match(source, /实时回传日志/);
  assert.match(source, /api\/models\/\$\{id\}\/activity/);
  assert.match(source, /每 3 秒刷新/);
  assert.match(source, /启动请求已接收/);
  assert.match(source, /正在启动…/);
  assert.match(source, /api\/control\/\$\{modelId\}\/panel/);
});

test("信源分析区显示每日 Top 25、关键词和三模型自有链接交集", async () => {
  const source = await readFile(new URL("Dashboard.tsx", app), "utf8");
  assert.match(source, /高频文章 Top 25/);
  assert.match(source, /高频视频 Top 25/);
  assert.match(source, /文章文案关键词/);
  assert.match(source, /视频文案关键词/);
  assert.match(source, /自有品牌/);
  assert.match(source, /文章标题关键词每日变化/);
  assert.match(source, /正文产品提及率与每日名次/);
  assert.match(source, /selectedSourceEligible/);
  assert.match(source, /selectedSourcePending/);
  assert.match(source, /items=\{threeIntersectionItems\}\s+mode="three"/);
  assert.match(source, /items=\{twoIntersectionItems\}\s+mode="two"/);
  assert.match(source, /选择对象/);
  assert.match(source, /竞品（文章正文命中）/);
  assert.match(source, /common_competitor_sources/);
  assert.match(source, /two_model_competitor_sources/);
  assert.match(source, /全部非自有竞品/);
  assert.match(source, /allCompetitors/);
  assert.match(source, /api\/analytics\/source-intersections/);
  assert.match(source, /sourceIntersectionsMatch/);
});

test("总览提供每日自有产品跨模型上榜看板并区分缺数与负样本", async () => {
  const source = await readFile(new URL("Dashboard.tsx", app), "utf8");
  assert.match(source, /我的产品每日上榜情况/);
  assert.match(source, /status\.state === "not_collected"/);
  assert.match(source, /status\.state === "listed"/);
  assert.match(source, /status\.state === "pending"/);
  assert.match(source, /已上榜/);
  assert.match(source, /未上榜/);
  assert.match(source, /待复核/);
  assert.match(source, /未采集/);
  assert.match(source, /\$\{mentionRate\.toFixed\(1\)\}%/);
  assert.match(source, /<OwnedProductStateCard \{\.\.\.display\}/);
  assert.match(source, /owned_product_daily/);
  assert.match(source, /owned_product_summary/);
  assert.match(source, /已跑天数汇总/);
  assert.match(source, /value=\{summaryMonth\} onChange=\{\(event\) => onSummaryMonthChange/);
  assert.match(source, /平均每天提及率/);
  assert.match(source, /observed_model_days/);
  assert.match(source, /row\.average_daily_mention_rate\.toFixed\(1\)/);
  assert.match(source, /platformColumns\.map\(\(\[id, label\]\) => <th/);
  assert.match(source, /const display = stateText\(row\.models\[item\.id\]\)/);
});

test("页面元数据使用通用多模型产品名称", async () => {
  const layout = await readFile(new URL("layout.tsx", app), "utf8");
  assert.match(layout, /title: "企业工作台"/);
  assert.doesNotMatch(layout, /Starter Project|codex-preview|豆包 × 元宝/);
});

test("日期筛选首屏按北京时间一次性初始化", async () => {
  const source = await readFile(new URL("Dashboard.tsx", app), "utf8");
  assert.match(source, /const \[date, setDate\] = useState\(\(\) => new Intl\.DateTimeFormat/);
  assert.doesNotMatch(source, /localStorage\.getItem\("monitorSelectedDate"\)/);
  assert.match(source, /localStorage\.setItem\("monitorSelectedDate", date\)/);
  assert.match(source, /timeZone: "Asia\/Shanghai"/);
  assert.match(source, /const filtersReady = true/);
  assert.match(source, /if \(!filtersReady\) return/);
  assert.doesNotMatch(source, /setFiltersReady/);
});

test("分析刷新不做日期预取并使用低开销条件轮询", async () => {
  const source = await readFile(new URL("Dashboard.tsx", app), "utf8");
  assert.doesNotMatch(source, /analyticsPrefetches|datesToWarm/);
  assert.doesNotMatch(source, /targetView of \["brands", "compare", "sources"\]/);
  assert.match(source, /silent && analyticsRequest\.current/);
  assert.match(source, /setInterval\(refreshLiveData, 15000\)/);
  assert.match(source, /analyticsResponseEtag/);
  assert.match(source, /cache: "no-cache"/);
  assert.match(source, /A filter label must never be paired with the previous filter's rows/);
  assert.doesNotMatch(source, /analyticsPayload\.questions\.includes\(question\).*setQuestion/);
  assert.doesNotMatch(source, /analyticsPayload\.dates\.includes\(date\).*setDate/);
  assert.match(source, /selectors must remain controlled by the user's last action/);
  assert.match(source, /filters\?\.view \|\| ""/);
  assert.match(source, /if \(view === "control" \|\| hashViews\.includes\(view\)\)/);
  assert.match(source, /const showAnalytics = view !== "control" && !hashViews\.includes\(view\)/);
  assert.match(source, /CreationControl/);
  assert.match(source, /analytics\.cache_status/);
});
