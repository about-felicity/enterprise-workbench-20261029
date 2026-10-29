/* Display the server-provided mini-program QR already held by the official
 * face-verification component. Never read or change the verification result,
 * safeVerifyCode, request logic, polling, callbacks, or authorization state. */
(function () {
  if (location.hostname !== 'yuanbao.tencent.com' || !/^\/(e\/)?login\/?$/.test(location.pathname)) return;
  if (window.__geoOfficialFaceQrDisplay) return;
  window.__geoOfficialFaceQrDisplay = true;
  function show() {
    const section = document.querySelector('.face-recognition-faceRecognitionSection');
    if (!section) return;
    let root;
    for (const element of document.querySelectorAll('body *')) {
      const key = Object.keys(element).find(k => k.startsWith('__reactFiber$'));
      if (key) { root = element[key]; break; }
    }
    if (!root) return;
    while (root.return) root = root.return;
    root = root.stateNode && root.stateNode.current || root;
    const stack = [root];
    let count = 0, picture;
    while (stack.length && count++ < 15000) {
      const fiber = stack.pop();
      if (fiber.child) stack.push(fiber.child);
      if (fiber.sibling) stack.push(fiber.sibling);
      let hook = fiber.memoizedState;
      for (let i = 0; hook && i < 100; i++, hook = hook.next) {
        const state = hook.memoizedState;
        if (state && typeof state === 'object' && typeof state.qrcode === 'string' &&
            typeof state.page === 'string' && typeof state.params === 'string' && state.qrcode.length > 100) {
          picture = state.qrcode;
          break;
        }
      }
      if (picture) break;
    }
    if (!picture) return;
    const source = picture.startsWith('data:image/') ? picture : 'data:image/png;base64,' + picture;
    if (!/^data:image\/(png|jpeg|jpg);base64,[A-Za-z0-9+/=\r\n]+$/.test(source)) return;
    let image = document.getElementById('geo-official-verification-qr');
    if (!image) {
      image = document.createElement('img');
      image.id = 'geo-official-verification-qr';
      image.alt = '官方微信小程序安全验证二维码';
      image.style.cssText = 'display:block;width:220px;height:220px;max-width:85vw;object-fit:contain;margin:0 auto 12px;background:white';
      const icon = section.querySelector('svg');
      if (icon) icon.style.display = 'none';
      section.prepend(image);
      const note = document.createElement('div');
      note.textContent = '请用手机微信扫描此官方验证二维码，按提示完成本人核验';
      note.style.cssText = 'font-size:15px;text-align:center;line-height:1.5;margin:8px 12px';
      section.append(note);
    }
    if (image.src !== source) image.src = source;
  }
  show();
  const timer = setInterval(show, 1500);
  setTimeout(() => clearInterval(timer), 30 * 60 * 1000);
})();
