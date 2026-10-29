const button = document.getElementById("openPanel");
const message = document.getElementById("message");

function showMessage(text, type = "") {
  message.textContent = text;
  message.className = `message ${type}`.trim();
}

async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function isSupported(url = "") {
  try {
    const host = new URL(url).hostname;
    return /(^|\.)(taobao|tmall|jd)\.com$/i.test(host);
  } catch {
    return false;
  }
}

async function sendToggle(tabId) {
  try {
    return await chrome.tabs.sendMessage(tabId, { type: "REVIEW_EXPORTER_TOGGLE" });
  } catch {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
    return chrome.tabs.sendMessage(tabId, { type: "REVIEW_EXPORTER_TOGGLE" });
  }
}

button.addEventListener("click", async () => {
  button.disabled = true;
  try {
    const tab = await currentTab();
    if (!tab?.id || !isSupported(tab.url)) {
      showMessage("当前不是淘宝、天猫或京东商品页面。", "error");
      return;
    }
    await sendToggle(tab.id);
    showMessage("抓取面板已显示在页面右侧。", "ok");
    setTimeout(() => window.close(), 450);
  } catch (error) {
    showMessage(`无法打开面板：${error.message || error}`, "error");
  } finally {
    button.disabled = false;
  }
});

(async () => {
  const tab = await currentTab();
  if (tab && isSupported(tab.url)) {
    showMessage("已识别支持的商品页面。", "ok");
  }
})();
