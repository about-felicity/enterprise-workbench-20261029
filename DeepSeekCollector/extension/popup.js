"use strict";

const button = document.getElementById("capture");
const status = document.getElementById("status");
const historyPanel = document.getElementById("history");

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "正在读取回答和信源…";
  try {
    const response = await chrome.runtime.sendMessage({ type: "CAPTURE_CURRENT" });
    if (!response?.ok) throw new Error(response?.error || "回传失败");
    status.textContent = response.synced
      ? `本机接收器已接收，含 ${response.sourceCount} 条信源。公网回传由接收器处理。`
      : "已保存到插件，本机接收器暂不可用，恢复后会自动补传。";
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

historyPanel.parentElement.addEventListener("toggle", async () => {
  if (!historyPanel.parentElement.open) return;
  try {
    const { recentResults = [] } = await chrome.storage.local.get("recentResults");
    historyPanel.replaceChildren();
    if (!recentResults.length) historyPanel.textContent = "暂无记录";
    for (const result of recentResults.slice(-20).reverse()) {
      const item = document.createElement("details");
      const title = document.createElement("summary");
      title.textContent = result.prompt || "未命名问题";
      const body = document.createElement("pre");
      body.className = "resultReply";
      body.textContent = result.reply || result.skip_reason || "";
      item.append(title, body);
      for (const source of result.sources || []) {
        if (!/^https?:\/\//i.test(source.url)) continue;
        const row = document.createElement("div");
        const link = document.createElement("a");
        link.href = source.url;
        link.textContent = source.title || source.url;
        link.target = "_blank";
        link.rel = "noreferrer";
        row.append(link);
        item.append(row);
      }
      historyPanel.append(item);
    }
  } catch (error) {
    historyPanel.textContent = error.message;
  }
});
