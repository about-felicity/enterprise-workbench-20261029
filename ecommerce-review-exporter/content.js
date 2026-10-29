(() => {
  "use strict";

  const GLOBAL_KEY = "__TAOBAO_JD_REVIEW_EXPORTER__";
  if (globalThis[GLOBAL_KEY]) {
    globalThis[GLOBAL_KEY].toggle(true);
    return;
  }

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim();
  const clip = (value, limit = 32000) => normalizeText(value).slice(0, limit);
  const isVisible = (element) => {
    if (!(element instanceof Element)) return false;
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  };

  function detectPlatform() {
    const host = location.hostname.toLowerCase();
    if (/(^|\.)jd\.com$/.test(host)) return { id: "jd", name: "京东", accent: "#e1251b" };
    if (/(^|\.)tmall\.com$/.test(host)) return { id: "tmall", name: "天猫", accent: "#ff0036" };
    if (/(^|\.)taobao\.com$/.test(host)) return { id: "taobao", name: "淘宝", accent: "#ff5000" };
    return { id: "unknown", name: "未知平台", accent: "#475569" };
  }

  const platform = detectPlatform();
  const state = {
    running: false,
    stopRequested: false,
    rows: new Map(),
    cycles: 0,
    staleCycles: 0,
    panelVisible: true,
    draftKey: "",
    storageError: "",
    readyPromise: null,
  };

  const host = document.createElement("div");
  host.id = "review-exporter-extension-host";
  host.style.cssText = "all:initial;position:fixed;right:20px;top:115px;z-index:2147483647;";
  document.documentElement.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });

  shadow.innerHTML = `
    <style>
      :host { all: initial; }
      * { box-sizing: border-box; }
      .panel {
        width: 330px; overflow: hidden; border: 1px solid rgba(15,23,42,.12); border-radius: 14px;
        background: #fff; color: #172033; box-shadow: 0 18px 55px rgba(15,23,42,.22);
        font-family: system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
      }
      .head { display:flex; align-items:center; justify-content:space-between; padding:13px 14px; color:#fff; background:${platform.accent}; }
      .title { display:flex; align-items:center; gap:9px; font-size:15px; font-weight:800; }
      .badge { padding:2px 7px; border:1px solid rgba(255,255,255,.45); border-radius:999px; font-size:11px; font-weight:600; }
      .head-actions { display:flex; gap:5px; }
      .icon-btn { width:26px; height:26px; border:0; border-radius:7px; background:rgba(255,255,255,.18); color:#fff; cursor:pointer; font-size:16px; }
      .body { padding:14px; }
      label { display:block; margin-bottom:6px; color:#475569; font-size:12px; font-weight:650; }
      .number-row { display:flex; gap:8px; }
      input[type=number] { width:100%; height:38px; padding:0 10px; border:1px solid #cbd5e1; border-radius:8px; outline:0; color:#172033; font-size:14px; }
      input[type=number]:focus { border-color:${platform.accent}; box-shadow:0 0 0 3px color-mix(in srgb, ${platform.accent} 14%, transparent); }
      .actions { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:11px; }
      button.action { height:38px; border:0; border-radius:8px; cursor:pointer; font-size:13px; font-weight:750; }
      .start { background:${platform.accent}; color:#fff; }
      .stop { background:#fff1f2; color:#be123c; border:1px solid #fecdd3 !important; }
      .export { grid-column:1 / -1; background:#eff6ff; color:#1d4ed8; border:1px solid #bfdbfe !important; }
      .clear { grid-column:1 / -1; background:#f8fafc; color:#64748b; border:1px solid #e2e8f0 !important; }
      button:disabled { cursor:not-allowed; opacity:.48; }
      .metric { display:flex; align-items:baseline; justify-content:space-between; margin-top:12px; padding:11px 12px; border-radius:9px; background:#f8fafc; }
      .metric span { color:#64748b; font-size:12px; }
      .metric strong { color:${platform.accent}; font-size:22px; }
      .progress { height:5px; margin-top:9px; overflow:hidden; border-radius:999px; background:#e8edf3; }
      .bar { width:0; height:100%; background:${platform.accent}; transition:width .25s ease; }
      .status { min-height:38px; margin-top:10px; padding:9px 10px; border-radius:8px; background:#f8fafc; color:#475569; font-size:12px; line-height:1.55; word-break:break-word; }
      .status.error { background:#fff1f2; color:#b42318; }
      .hint { margin:9px 1px 0; color:#8993a3; font-size:11px; line-height:1.5; }
      .collapsed { display:none; width:48px; padding:10px 8px; border:0; border-radius:12px; background:${platform.accent}; color:#fff; box-shadow:0 10px 30px rgba(15,23,42,.24); cursor:pointer; font-size:13px; font-weight:800; line-height:1.25; }
      .hidden { display:none !important; }
    </style>
    <section class="panel" aria-label="评论导出助手">
      <header class="head">
        <div class="title">评论导出助手 <span class="badge">${platform.name}</span></div>
        <div class="head-actions">
          <button class="icon-btn" id="minimize" title="收起">−</button>
          <button class="icon-btn" id="close" title="关闭">×</button>
        </div>
      </header>
      <div class="body">
        <label for="maxCount">最大抓取条数</label>
        <div class="number-row"><input id="maxCount" type="number" min="1" max="100000" step="1" value="100"></div>
        <div class="actions">
          <button class="action start" id="start">开始抓取</button>
          <button class="action stop" id="stop" disabled>停止</button>
          <button class="action export" id="export" disabled>导出 Excel</button>
          <button class="action clear" id="clear" disabled>清空已保存的评论</button>
        </div>
        <div class="metric"><span>已采集并去重</span><strong id="count">0</strong></div>
        <div class="progress"><div class="bar" id="bar"></div></div>
        <div class="status" id="status">准备就绪。开始后会自动尝试打开全部评价。</div>
        <p class="hint">若网站没有自动进入全部评价，请手动点击页面的“查看全部评价/全部评价”，插件会继续采集。</p>
      </div>
    </section>
    <button class="collapsed" id="restore">评论<br>导出</button>
  `;

  const $ = (selector) => shadow.querySelector(selector);
  const panel = $(".panel");
  const restoreButton = $("#restore");
  const maxInput = $("#maxCount");
  const startButton = $("#start");
  const stopButton = $("#stop");
  const exportButton = $("#export");
  const clearButton = $("#clear");
  const countElement = $("#count");
  const statusElement = $("#status");
  const progressBar = $("#bar");

  function setStatus(message, error = false) {
    statusElement.textContent = message;
    statusElement.classList.toggle("error", error);
  }

  function updateMetrics(maximum) {
    const count = state.rows.size;
    countElement.textContent = String(count);
    const percent = maximum ? Math.min(100, Math.round((count / maximum) * 100)) : 0;
    progressBar.style.width = `${percent}%`;
    exportButton.disabled = count === 0;
    clearButton.disabled = count === 0 || state.running;
  }

  function setRunning(running) {
    state.running = running;
    startButton.disabled = running;
    stopButton.disabled = !running;
    maxInput.disabled = running;
    clearButton.disabled = running || state.rows.size === 0;
  }

  function toggle(forceVisible) {
    const visible = typeof forceVisible === "boolean" ? forceVisible : !state.panelVisible;
    state.panelVisible = visible;
    panel.classList.toggle("hidden", !visible);
    restoreButton.classList.toggle("hidden", visible);
  }

  $("#minimize").addEventListener("click", () => toggle(false));
  $("#close").addEventListener("click", () => { host.style.display = "none"; });
  restoreButton.addEventListener("click", () => toggle(true));

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "REVIEW_EXPORTER_TOGGLE") {
      host.style.display = "block";
      toggle(true);
      sendResponse({ ok: true, platform: platform.name, count: state.rows.size });
    }
  });

  const ENTRY_TEXTS = [
    "查看全部评价", "查看全部评论", "全部评价", "全部评论", "累计评价", "用户评价", "商品评价"
  ];

  function findClickableByTexts(texts, root = document) {
    const wanted = new Map(texts.map((text, index) => [text, texts.length - index]));
    const candidates = [];
    const elements = root.querySelectorAll("button,a,[role=button],span,div");
    for (const element of elements) {
      if (!isVisible(element)) continue;
      const text = normalizeText(element.textContent).replace(/[>›»]/g, "").trim();
      if (!wanted.has(text)) continue;
      const rect = element.getBoundingClientRect();
      if (rect.width > 700 || rect.height > 160) continue;
      let score = wanted.get(text) * 20;
      if (element.matches("button,a,[role=button]")) score += 25;
      if (element.matches("[class^='ShowButton--'],[class*=' ShowButton--']")) score += 35;
      if (/查看全部|全部评价|全部评论/.test(text)) score += 40;
      if (rect.top >= 0 && rect.top <= innerHeight) score += 5;
      // Prefer the actual child control when its parent has the same text.
      if ([...element.children].some((child) => normalizeText(child.textContent) === text)) score -= 30;
      candidates.push({ element, score, text });
    }
    candidates.sort((a, b) => b.score - a.score);
    return candidates[0] || null;
  }

  async function openAllReviews() {
    if (platform.id === "jd") {
      if (document.querySelector(".jdc-page-overlay .jdc-pc-rate-card")) return true;
      const entry = document.querySelector(".comment-root .all-btn");
      if (entry && isVisible(entry)) {
        setStatus("正在打开京东全部评价…");
        entry.scrollIntoView({ block: "center", behavior: "auto" });
        await sleep(250);
        entry.click();
        for (let attempt = 0; attempt < 6; attempt += 1) {
          await sleep(1000);
          if (document.querySelector(".jdc-page-overlay .jdc-pc-rate-card")) return true;
        }
        return false;
      }
    }
    if (['taobao', 'tmall'].includes(platform.id) && document.querySelectorAll("[class^='Comment--'],[class*=' Comment--']").length > 2) {
      setStatus("已检测到完整评价列表，开始采集…");
      return true;
    }
    const candidate = findClickableByTexts(ENTRY_TEXTS);
    if (!candidate) {
      setStatus("没有找到全部评价入口；将直接采集当前页面。必要时请手动打开全部评价。");
      return false;
    }
    setStatus(`正在打开“${candidate.text}”…`);
    candidate.element.scrollIntoView({ block: "center", behavior: "auto" });
    await sleep(250);
    if (typeof candidate.element.click === "function") candidate.element.click();
    else candidate.element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    await sleep(1800);
    return true;
  }

  const COMMON_CARD_SELECTORS = [
    ".jdc-page-overlay .jdc-pc-rate-card",
    ".comment-item", ".J-comment-item", "[class*='CommentItem']", "[class*='commentItem']",
    "[class^='Comment--']", "[class*=' Comment--']", "[class*='comment--']", "[class*='Comment_']",
    "[class*='comment-item']", "[class*='ReviewItem']", "[class*='review-item']",
    "[class*='RateItem']", "[class*='rate-item']", "[class*='EvaluateItem']",
    "[class*='evaluate-item']", "[data-guid][class*='comment']"
  ];

  const CONTENT_SELECTORS = [
    ".jdc-pc-rate-card-main-desc",
    ".comment-con", ".comment-content", ".tm-rate-fulltxt", ".rate-content",
    "[class*='CommentContent']", "[class*='commentContent']", "[class*='comment-content']",
    "[class*='ReviewContent']", "[class*='review-content']", "[class*='RateContent']",
    "[class*='rate-content']", "[class^='content--']", "[data-testid*='comment']"
  ];

  const USER_SELECTORS = [
    ".jdc-pc-rate-card-nick",
    ".user-info", ".user-name", ".nickname", ".nick", ".name",
    "[class*='UserName']", "[class*='userName']", "[class*='user-name']", "[class*='userName--']",
    "[class*='NickName']", "[class*='nickname']", "[class*='nick--']", "[class*='user-info']"
  ];

  const DATE_SELECTORS = [
    ".jdc-pc-rate-card-info .date",
    ".order-info", ".comment-time", ".date", ".time",
    "[class*='CommentTime']", "[class*='commentTime']", "[class*='comment-time']",
    "[class*='Date']", "[class*='date']", "[class*='Time']", "[class*='time']", "[class^='meta--']"
  ];

  const SKU_SELECTORS = [
    ".jdc-pc-rate-card-info .info",
    ".order-info", ".sku-info", ".product-info",
    "[class*='SkuInfo']", "[class*='skuInfo']", "[class*='sku-info']",
    "[class*='ProductInfo']", "[class*='product-info']", "[class*='auctionSku']"
  ];

  const APPEND_SELECTORS = [
    ".append-comment", ".comment-add", ".after-comment",
    "[class*='AppendComment']", "[class*='appendComment']", "[class*='append-comment']",
    "[class*='AdditionalComment']", "[class*='additional-comment']", "[class*='after-comment']"
  ];

  const DATE_RE = /(?:20\d{2})[-/.年]\d{1,2}(?:[-/.月]\d{1,2}日?)?(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?/;

  function closestPlausibleCard(element) {
    const direct = element.closest(COMMON_CARD_SELECTORS.join(","));
    if (direct) return direct;
    let current = element;
    for (let level = 0; current && level < 6; level += 1, current = current.parentElement) {
      const text = normalizeText(current.innerText);
      if (text.length >= 20 && text.length <= 6000 && (DATE_RE.test(text) || current.querySelector("img"))) {
        return current;
      }
    }
    return null;
  }

  function findReviewCards() {
    const set = new Set();
    for (const selector of COMMON_CARD_SELECTORS) {
      for (const element of document.querySelectorAll(selector)) {
        const card = closestPlausibleCard(element);
        const text = normalizeText(card?.innerText);
        const classText = String(card?.className || "");
        const itemSignal = /(?:comment|review|rate|evaluate)[-_]?(?:item|card)|Comment--|comment--/i.test(classText);
        const contentSignal = DATE_RE.test(text) || Boolean(card?.querySelector(USER_SELECTORS.join(","))) || Boolean(card?.querySelector("img"));
        if (card && isVisible(card) && text.length >= 12 && text.length <= 7000 && (itemSignal || contentSignal)) set.add(card);
      }
    }

    if (set.size === 0) {
      const dated = document.querySelectorAll(DATE_SELECTORS.join(","));
      for (const element of dated) {
        const text = normalizeText(element.textContent);
        if (!DATE_RE.test(text)) continue;
        const card = closestPlausibleCard(element);
        if (card && isVisible(card)) set.add(card);
      }
    }

    const cards = [...set];
    return cards.filter((card) => !cards.some((other) => other !== card && card.contains(other)));
  }

  function isPreviewOnly(cards) {
    if (platform.id === "jd") {
      return Boolean(document.querySelector(".comment-root") && !document.querySelector(".jdc-page-overlay .jdc-pc-rate-card"));
    }
    if (!['taobao', 'tmall'].includes(platform.id) || cards.length > 2) return false;
    const preview = document.querySelector('[class^="Comments--"], [class*=" Comments--"]');
    return Boolean(preview && cards.length > 0 && cards.every((card) => preview.contains(card)));
  }

  async function expandCard(card) {
    const words = /^(展开|全文|查看全文|显示全部|展开全文|更多)$/;
    let clicks = 0;
    for (const element of card.querySelectorAll("button,a,[role=button],span,div")) {
      if (clicks >= 3) break;
      const text = normalizeText(element.textContent).replace(/[>›»…]/g, "").trim();
      if (!words.test(text) || !isVisible(element)) continue;
      const rect = element.getBoundingClientRect();
      if (rect.width > 180 || rect.height > 70) continue;
      if (typeof element.click === "function") element.click();
      else element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      clicks += 1;
    }
    if (clicks) await sleep(120);
    return clicks;
  }

  function firstUsefulText(root, selectors, maxLength = 4000) {
    for (const selector of selectors) {
      const values = [...root.querySelectorAll(selector)]
        .map((element) => normalizeText(element.innerText || element.textContent))
        .filter((text) => text && text.length <= maxLength);
      if (values.length) return values.sort((a, b) => b.length - a.length)[0];
    }
    return "";
  }

  function commentContent(card) {
    for (const selector of CONTENT_SELECTORS) {
      const values = [...card.querySelectorAll(selector)].filter(isVisible)
        .map((node) => {
          const shown = normalizeText(node.innerText || node.textContent);
          const full = normalizeText(node.getAttribute("title"));
          return full.length > shown.length ? full : shown;
        })
        .filter((value) => value && value.length <= 5000);
      if (values.length) return values.sort((a, b) => b.length - a.length)[0];
    }
    return "";
  }

  function genericCommentText(card) {
    const candidates = [];
    for (const element of card.querySelectorAll("p,span,div")) {
      if (!isVisible(element)) continue;
      const text = normalizeText(element.innerText || element.textContent);
      if (text.length < 6 || text.length > 3000 || DATE_RE.test(text) && text.length < 60) continue;
      if (/^(有用|点赞|回复|购买于|规格|颜色|尺码|展开|全文|查看全文)/.test(text)) continue;
      const longChild = [...element.children].some((child) => normalizeText(child.textContent).length > text.length * 0.72);
      if (longChild) continue;
      let score = Math.min(text.length, 240);
      if (/[。！？!?，,]/.test(text)) score += 20;
      if (/追评|追加/.test(text)) score -= 25;
      candidates.push({ text, score });
    }
    candidates.sort((a, b) => b.score - a.score);
    return candidates[0]?.text || "";
  }

  function extractDate(card) {
    const preferred = firstUsefulText(card, DATE_SELECTORS, 300);
    const match = (preferred || normalizeText(card.innerText)).match(DATE_RE);
    if (match) return match[0];
    // JD currently renders review dates as MM-DD without a year.
    if (platform.id === "jd") return preferred.match(/^\d{1,2}-\d{1,2}$/)?.[0] || "";
    return "";
  }

  function extractRating(card) {
    const nodes = card.querySelectorAll("[aria-label*='星'],[title*='星'],[class*='star'],[class*='Star']");
    for (const node of nodes) {
      const source = `${node.getAttribute("aria-label") || ""} ${node.getAttribute("title") || ""} ${node.className || ""}`;
      const match = source.match(/(?:star|星|评分)[^0-9]*([1-5])|([1-5])[^0-9]*(?:星|分)/i);
      if (match) return match[1] || match[2];
    }
    return "";
  }

  function extractLikes(card) {
    const nodes = card.querySelectorAll("[class*='like'],[class*='Like'],[class*='praise'],[class*='useful']");
    for (const node of nodes) {
      const text = normalizeText(node.textContent);
      const match = text.match(/\d+/);
      if (match) return match[0];
    }
    return "";
  }

  function mediaUrls(card) {
    const imageUrls = [];
    for (const image of card.querySelectorAll("img")) {
      if (image.closest("[class*='avatar'],[class*='Avatar'],[class*='user-head']")) continue;
      const url = image.currentSrc || image.src || image.dataset.src || image.getAttribute("data-lazy-img") || "";
      if (!url || url.startsWith("data:")) continue;
      const rect = image.getBoundingClientRect();
      if (rect.width && rect.height && rect.width < 55 && rect.height < 55) continue;
      imageUrls.push(url.startsWith("//") ? `https:${url}` : url);
    }
    const videoUrls = [];
    for (const video of card.querySelectorAll("video,video source")) {
      const url = video.currentSrc || video.src || video.getAttribute("src") || "";
      if (url && !url.startsWith("blob:")) videoUrls.push(url.startsWith("//") ? `https:${url}` : url);
    }
    return {
      images: [...new Set(imageUrls)].join("\n"),
      videos: [...new Set(videoUrls)].join("\n"),
    };
  }

  function productInfo() {
    const titleSelectors = ["h1", ".sku-name", "[class*='ItemTitle']", "[class*='item-title']", "[class*='Title--']"];
    let title = "";
    for (const selector of titleSelectors) {
      const element = [...document.querySelectorAll(selector)].find((item) => isVisible(item) && normalizeText(item.textContent).length > 3);
      if (element) { title = normalizeText(element.textContent); break; }
    }
    const url = new URL(location.href);
    // JD may redirect a long-running review session to its risk-check page.
    // Keep the original product identity so the saved draft can be recovered.
    const returnUrl = url.searchParams.get("returnurl") || url.searchParams.get("returnUrl");
    let sourceUrl = url;
    if (platform.id === "jd" && returnUrl) {
      try { sourceUrl = new URL(returnUrl); } catch { /* Use the current URL. */ }
    }
    let productId = sourceUrl.searchParams.get("id") || "";
    if (!productId && platform.id === "jd") productId = sourceUrl.pathname.match(/\/(\d+)\.html/)?.[1] || "";
    return { title: title || document.title, url: sourceUrl.href, productId };
  }

  const DRAFT_PREFIX = "review_exporter_draft_v1_";
  const activeDraftKey = `${DRAFT_PREFIX}active_${platform.id}`;

  async function restoreDraft() {
    try {
      const info = productInfo();
      const active = await chrome.storage.local.get(activeDraftKey);
      const key = info.productId
        ? `${DRAFT_PREFIX}${platform.id}_${info.productId}`
        : active[activeDraftKey];
      state.draftKey = key || "";
      if (!key) return;
      const stored = (await chrome.storage.local.get(key))[key];
      if (!stored || !Array.isArray(stored.rows)) return;
      if (info.productId && stored.productId !== info.productId) return;
      state.rows = new Map(stored.rows.filter((row) => row?.key).map((row) => [row.key, row]));
      updateMetrics(Number.parseInt(maxInput.value, 10) || 100);
      if (state.rows.size) setStatus(`已恢复 ${state.rows.size} 条未导出评论，可继续抓取或直接导出。`);
    } catch (error) {
      state.storageError = String(error?.message || error);
      setStatus(`无法读取本地草稿：${state.storageError}。请勿继续抓取。`, true);
    }
  }

  async function saveDraft() {
    if (!state.rows.size) return;
    const info = productInfo();
    const productId = info.productId || state.rows.values().next().value?.productId;
    if (!productId) throw new Error("无法识别商品 ID，评论未能安全保存");
    const key = `${DRAFT_PREFIX}${platform.id}_${productId}`;
    const draft = {
      productId,
      productTitle: state.rows.values().next().value?.productTitle || info.title,
      productUrl: state.rows.values().next().value?.productUrl || info.url,
      updatedAt: new Date().toISOString(),
      rows: [...state.rows.values()],
    };
    await chrome.storage.local.set({ [key]: draft, [activeDraftKey]: key });
    state.draftKey = key;
  }

  function extractReview(card) {
    const info = productInfo();
    const username = firstUsefulText(card, USER_SELECTORS, 120);
    let content = commentContent(card);
    if (!content || content.length < 6) content = genericCommentText(card);
    const additional = firstUsefulText(card, APPEND_SELECTORS, 4000);
    if (additional && content.includes(additional)) content = content.replace(additional, "").trim();
    const date = extractDate(card);
    const sku = firstUsefulText(card, SKU_SELECTORS, 500);
    const media = mediaUrls(card);
    if (!content || content.length < 2) return null;

    const row = {
      platform: platform.name,
      productId: info.productId,
      productTitle: info.title,
      productUrl: info.url,
      username: username || "匿名用户",
      rating: extractRating(card),
      content: clip(content),
      additional: clip(additional),
      date,
      sku: clip(sku, 500),
      likes: extractLikes(card),
      images: media.images,
      videos: media.videos,
      collectedAt: new Date().toLocaleString("zh-CN", { hour12: false }),
    };
    row.key = [row.username, row.date, row.content.slice(0, 180), row.images.split("\n")[0] || ""].join("|");
    return row;
  }

  function findNextOrMoreButton() {
    // JD's current drawer is an infinite virtual list; generic “查看更多”
    // controls inside it can belong to replies rather than pagination.
    if (platform.id === "jd" && document.querySelector(".jdc-page-overlay .jdc-pc-rate-card")) return null;
    const texts = ["下一页", "加载更多", "查看更多", "更多评价", "继续加载"];
    const root = platform.id === "jd" ? document.querySelector(".jdc-page-overlay") : document;
    const result = findClickableByTexts(texts, root || document);
    if (!result) {
      const aria = [...(root || document).querySelectorAll("button[aria-label],a[aria-label]")].find((element) => {
        const label = normalizeText(element.getAttribute("aria-label"));
        return /下一页|next/i.test(label) && isVisible(element);
      });
      return aria || null;
    }
    const element = result.element;
    const disabled = element.matches(":disabled,[disabled],[aria-disabled='true']") || /disabled|is-disabled/.test(String(element.className));
    return disabled ? null : element;
  }

  function reviewScrollContainer(cards) {
    if (!cards.length) return null;
    const candidates = [];
    for (const card of [cards[0], cards[cards.length - 1]]) {
      let current = card.parentElement;
      while (current && current !== document.body && current !== document.documentElement) {
        const style = getComputedStyle(current);
        const range = current.scrollHeight - current.clientHeight;
        if (/(auto|scroll|overlay)/.test(style.overflowY) && current.clientHeight >= 180 && range > 120) {
          candidates.push({ element: current, range });
        }
        current = current.parentElement;
      }
    }
    // The reviews drawer has its own scrollbar. Choose the scrollable ancestor
    // that actually contains the cards, rather than the product page.
    candidates.sort((a, b) => b.range - a.range);
    return candidates[0]?.element || null;
  }

  async function requestMore(cards) {
    const button = findNextOrMoreButton();
    if (button) {
      button.scrollIntoView({ block: "center", behavior: "auto" });
      if (typeof button.click === "function") button.click();
      else button.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      await sleep(1500);
      return { message: "已点击下一页/加载更多", moved: false };
    }

    const container = reviewScrollContainer(cards);
    if (container) {
      const before = container.scrollTop;
      const bottom = Math.max(0, container.scrollHeight - container.clientHeight);
      // Virtualized review lists replace off-screen cards. Capture each screen
      // before moving on, instead of jumping over all intermediate reviews.
      const step = Math.max(200, Math.round(container.clientHeight * 0.7));
      container.scrollTop = Math.min(bottom, before + step);
      await sleep(1700);
      const moved = container.scrollTop > before + 5;
      return {
        message: moved ? `已逐屏滚动评价弹层到 ${Math.round(container.scrollTop)}/${Math.round(bottom)}` : "评价弹层已到底部，正在等待加载",
        moved,
      };
    }

    const before = window.scrollY;
    window.scrollTo({ top: Math.max(0, document.documentElement.scrollHeight - innerHeight), behavior: "auto" });
    await sleep(1700);
    const moved = window.scrollY > before + 5;
    return { message: moved ? "已滚动页面到底部" : "页面已到底部，正在等待加载", moved };
  }

  async function scrape(maximum) {
    state.stopRequested = false;
    state.cycles = 0;
    state.staleCycles = 0;
    updateMetrics(maximum);
    setRunning(true);

    try {
      if (state.rows.size >= maximum) {
        setStatus(`已保存 ${state.rows.size} 条评论，达到当前最大条数；可直接导出。`);
        return;
      }
      if (platform.id === "jd" && /\/risk_handler\//.test(location.pathname)) {
        setStatus("当前是京东安全验证页。已保存的评论可直接导出；如需继续抓取，请先自行完成验证并返回商品页。", true);
        return;
      }
      await openAllReviews();
      while (!state.stopRequested && state.rows.size < maximum) {
        state.cycles += 1;
        const before = state.rows.size;
        const cards = findReviewCards();
        const previewOnly = isPreviewOnly(cards);

        if (previewOnly) {
          setStatus("目前只显示商品页预览评价。“查看全部评价”没有成功展开；请先在网页中打开完整评价列表，再重新开始。", true);
          break;
        }

        for (const card of cards) {
          if (state.stopRequested || state.rows.size >= maximum) break;
          await expandCard(card);
          const row = extractReview(card);
          if (row && !state.rows.has(row.key)) state.rows.set(row.key, row);
        }

        const added = state.rows.size - before;
        updateMetrics(maximum);
        if (added) await saveDraft();

        if (!cards.length) {
          setStatus(`第 ${state.cycles} 轮未识别到评论。请手动打开“全部评价”，插件正在继续检测…`);
        } else {
          setStatus(`第 ${state.cycles} 轮：识别 ${cards.length} 个评论卡片，本轮新增 ${added} 条。`);
        }

        if (state.rows.size >= maximum) break;
        const action = await requestMore(cards);
        state.staleCycles = added === 0 && !action.moved ? state.staleCycles + 1 : 0;
        setStatus(`${action.message}；已采集 ${state.rows.size}/${maximum} 条。`);
        if (state.staleCycles >= 5) {
          setStatus(`评价列表已到底部且多轮没有新评论，已结束。共采集 ${state.rows.size} 条。`);
          break;
        }
        if (state.cycles >= 300) {
          setStatus(`达到安全轮次上限，已停止。共采集 ${state.rows.size} 条，可继续导出。`);
          break;
        }
      }

      if (state.stopRequested) setStatus(`已停止，共采集 ${state.rows.size} 条，可导出 Excel。`);
      else if (state.rows.size >= maximum) setStatus(`已达到最大条数 ${maximum}，抓取完成。`);
      else if (!state.rows.size) setStatus("没有抓到评论。请先手动打开全部评价并确认评论在页面中可见，然后重试。", true);
    } catch (error) {
      console.error("[评论导出助手]", error);
      setStatus(`抓取出现错误：${error.message || error}`, true);
    } finally {
      setRunning(false);
      updateMetrics(maximum);
    }
  }

  function xmlEscape(value) {
    return String(value ?? "")
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  function columnName(index) {
    let result = "";
    for (let value = index + 1; value > 0; value = Math.floor((value - 1) / 26)) {
      result = String.fromCharCode(65 + ((value - 1) % 26)) + result;
    }
    return result;
  }

  function xlsxCell(value, rowIndex, columnIndex, styleIndex = 0) {
    const reference = `${columnName(columnIndex)}${rowIndex}`;
    const style = styleIndex ? ` s="${styleIndex}"` : "";
    return `<c r="${reference}" t="inlineStr"${style}><is><t xml:space="preserve">${xmlEscape(clip(value))}</t></is></c>`;
  }

  function crc32(bytes) {
    if (!crc32.table) {
      crc32.table = Array.from({ length: 256 }, (_, index) => {
        let value = index;
        for (let bit = 0; bit < 8; bit += 1) value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
        return value >>> 0;
      });
    }
    let crc = 0xffffffff;
    for (const byte of bytes) crc = crc32.table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }

  function zipFiles(files) {
    const encoder = new TextEncoder();
    const localParts = [];
    const centralParts = [];
    let offset = 0;
    const now = new Date();
    const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | Math.floor(now.getSeconds() / 2);
    const dosDate = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();

    const makeView = (length) => {
      const buffer = new ArrayBuffer(length);
      return { bytes: new Uint8Array(buffer), view: new DataView(buffer) };
    };

    for (const [name, contents] of Object.entries(files)) {
      const nameBytes = encoder.encode(name);
      const data = typeof contents === "string" ? encoder.encode(contents) : contents;
      const checksum = crc32(data);
      const local = makeView(30 + nameBytes.length);
      local.view.setUint32(0, 0x04034b50, true);
      local.view.setUint16(4, 20, true);
      local.view.setUint16(6, 0x0800, true);
      local.view.setUint16(8, 0, true);
      local.view.setUint16(10, dosTime, true);
      local.view.setUint16(12, dosDate, true);
      local.view.setUint32(14, checksum, true);
      local.view.setUint32(18, data.length, true);
      local.view.setUint32(22, data.length, true);
      local.view.setUint16(26, nameBytes.length, true);
      local.view.setUint16(28, 0, true);
      local.bytes.set(nameBytes, 30);
      localParts.push(local.bytes, data);

      const central = makeView(46 + nameBytes.length);
      central.view.setUint32(0, 0x02014b50, true);
      central.view.setUint16(4, 20, true);
      central.view.setUint16(6, 20, true);
      central.view.setUint16(8, 0x0800, true);
      central.view.setUint16(10, 0, true);
      central.view.setUint16(12, dosTime, true);
      central.view.setUint16(14, dosDate, true);
      central.view.setUint32(16, checksum, true);
      central.view.setUint32(20, data.length, true);
      central.view.setUint32(24, data.length, true);
      central.view.setUint16(28, nameBytes.length, true);
      central.view.setUint16(30, 0, true);
      central.view.setUint16(32, 0, true);
      central.view.setUint16(34, 0, true);
      central.view.setUint16(36, 0, true);
      central.view.setUint32(38, 0, true);
      central.view.setUint32(42, offset, true);
      central.bytes.set(nameBytes, 46);
      centralParts.push(central.bytes);
      offset += local.bytes.length + data.length;
    }

    const centralSize = centralParts.reduce((sum, part) => sum + part.length, 0);
    const end = makeView(22);
    end.view.setUint32(0, 0x06054b50, true);
    end.view.setUint16(4, 0, true);
    end.view.setUint16(6, 0, true);
    end.view.setUint16(8, centralParts.length, true);
    end.view.setUint16(10, centralParts.length, true);
    end.view.setUint32(12, centralSize, true);
    end.view.setUint32(16, offset, true);
    end.view.setUint16(20, 0, true);
    return new Blob([...localParts, ...centralParts, end.bytes], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
  }

  function createXlsx(rows, columns, widths) {
    const sheetRows = [];
    sheetRows.push(`<row r="1" ht="26" customHeight="1">${columns.map(([label], index) => xlsxCell(label, 1, index, 1)).join("")}</row>`);
    rows.forEach((row, rowOffset) => {
      const rowIndex = rowOffset + 2;
      sheetRows.push(`<row r="${rowIndex}">${columns.map(([, key], index) => xlsxCell(row[key], rowIndex, index)).join("")}</row>`);
    });
    const cols = widths.map((width, index) => `<col min="${index + 1}" max="${index + 1}" width="${Math.max(8, width / 7)}" customWidth="1"/>`).join("");
    const lastCell = `${columnName(columns.length - 1)}${rows.length + 1}`;
    const sheet = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:${lastCell}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="18"/><cols>${cols}</cols><sheetData>${sheetRows.join("")}</sheetData><autoFilter ref="A1:${columnName(columns.length - 1)}1"/></worksheet>`;
    const color = platform.id === "jd" ? "FFE1251B" : "FFFF5000";
    const styles = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="10"/><name val="Microsoft YaHei"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="10"/><name val="Microsoft YaHei"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="${color}"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
    const files = {
      "[Content_Types].xml": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>`,
      "_rels/.rels": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`,
      "xl/workbook.xml": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="${xmlEscape(platform.name)}评论" sheetId="1" r:id="rId1"/></sheets></workbook>`,
      "xl/_rels/workbook.xml.rels": `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`,
      "xl/styles.xml": styles,
      "xl/worksheets/sheet1.xml": sheet,
    };
    return zipFiles(files);
  }

  function exportExcel() {
    const rows = [...state.rows.values()];
    if (!rows.length) {
      setStatus("当前没有可导出的评论。", true);
      return;
    }

    const columns = [
      ["平台", "platform"], ["商品ID", "productId"], ["商品标题", "productTitle"],
      ["商品链接", "productUrl"], ["用户昵称", "username"], ["评分", "rating"],
      ["评论内容", "content"], ["追评内容", "additional"], ["评论日期", "date"],
      ["商品规格", "sku"], ["点赞数", "likes"], ["图片链接", "images"],
      ["视频链接", "videos"], ["采集时间", "collectedAt"]
    ];
    const widths = [70, 95, 280, 260, 110, 55, 420, 300, 130, 180, 70, 350, 300, 145];
    const blob = createXlsx(rows, columns, widths);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const safeTitle = (rows[0].productTitle || productInfo().title).replace(/[\\/:*?"<>|]/g, "_").slice(0, 45);
    const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
    anchor.href = url;
    anchor.download = `${platform.name}评论_${safeTitle}_${stamp}.xlsx`;
    document.documentElement.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 3000);
    setStatus(`已导出 ${rows.length} 条评论。`);
  }

  startButton.addEventListener("click", async () => {
    if (state.running) return;
    await state.readyPromise;
    if (state.storageError) {
      setStatus(`本地草稿不可用，已阻止抓取以免再次丢失：${state.storageError}`, true);
      return;
    }
    const maximum = Math.max(1, Math.min(100000, Number.parseInt(maxInput.value, 10) || 100));
    maxInput.value = String(maximum);
    scrape(maximum);
  });

  stopButton.addEventListener("click", () => {
    state.stopRequested = true;
    setStatus("正在停止，将在当前页面操作完成后结束…");
  });

  exportButton.addEventListener("click", exportExcel);

  clearButton.addEventListener("click", async () => {
    await state.readyPromise;
    if (!state.rows.size || state.running) return;
    if (!window.confirm(`确定清空当前商品已保存的 ${state.rows.size} 条评论吗？清空后无法恢复。`)) return;
    try {
      const active = await chrome.storage.local.get(activeDraftKey);
      await chrome.storage.local.remove(active[activeDraftKey] === state.draftKey
        ? [state.draftKey, activeDraftKey] : [state.draftKey]);
      state.rows.clear();
      state.draftKey = "";
      updateMetrics(Number.parseInt(maxInput.value, 10) || 100);
      setStatus("已清空当前商品的本地评论草稿。");
    } catch (error) {
      setStatus(`清空失败：${error.message || error}`, true);
    }
  });

  state.readyPromise = restoreDraft();

  globalThis[GLOBAL_KEY] = { toggle, state };
})();
