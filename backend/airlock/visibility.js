() => {
  const segments = [];
  const LIMIT = 500;
  const forbidden = new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','SVG']);
  const number = value => { const n = parseFloat(value); return Number.isFinite(n) ? n : 0; };
  function rgb(value) {
    const m = (value || '').match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const nums = m[1].replace(/\//g, ',').split(/[\s,]+/).filter(Boolean).map(Number);
    return nums.length >= 3 && nums.slice(0,3).every(Number.isFinite) ? nums : null;
  }
  function luminance(c) {
    const a = c.slice(0,3).map(v => {v/=255; return v <= .04045 ? v/12.92 : Math.pow((v+.055)/1.055,2.4)});
    return .2126*a[0] + .7152*a[1] + .0722*a[2];
  }
  function bgFor(el) {
    while (el && el.nodeType === 1) {
      const c = rgb(getComputedStyle(el).backgroundColor);
      if (c && (c.length < 4 || c[3] > .95)) return c;
      el = el.parentElement;
    }
    return [255,255,255];
  }
  function hiddenReasons(node) {
    let el = node.parentElement, reasons = [];
    if (!el) return ['no parent'];
    let ancestor = el;
    while (ancestor && ancestor.nodeType === 1) {
      const s = getComputedStyle(ancestor);
      if (s.display === 'none') reasons.push('display:none');
      if (s.visibility === 'hidden' || s.visibility === 'collapse') reasons.push('visibility:hidden');
      if (number(s.opacity) <= .02) reasons.push('opacity:0');
      if (s.contentVisibility === 'hidden') reasons.push('content-visibility:hidden');
      if (s.clipPath && /inset\(\s*(?:100%|50%)/.test(s.clipPath)) reasons.push('clipped');
      if (s.clip && s.clip !== 'auto' && /rect\(\s*0(px)?[,\s]+0(px)?/.test(s.clip)) reasons.push('clipped');
      ancestor = ancestor.parentElement;
    }
    const style = getComputedStyle(el);
    if (number(style.fontSize) <= 1.5) reasons.push('tiny font');
    const fg = rgb(style.color), bg = bgFor(el);
    if (fg && (fg.length > 3 && fg[3] < .025)) reasons.push('transparent text');
    else if (fg) {
      const l1 = luminance(fg), l2 = luminance(bg);
      if ((Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05) < 1.18) reasons.push('low contrast');
    }
    const range = document.createRange();
    range.selectNodeContents(node);
    const rect = range.getBoundingClientRect();
    if (rect.width < .5 || rect.height < .5) reasons.push('zero-sized text');
    if (rect.right < -20 || rect.bottom < -20 || rect.left > 100000) reasons.push('off-screen');
    if (rect.width > 2 && rect.height > 2 && rect.left >= 0 && rect.top >= 0 &&
        rect.left < innerWidth && rect.top < innerHeight) {
      const x = Math.max(0, Math.min(innerWidth - 1, rect.left + Math.min(rect.width/2, 20)));
      const y = Math.max(0, Math.min(innerHeight - 1, rect.top + rect.height/2));
      const top = document.elementFromPoint(x,y);
      
      let transparentOverlay = false;

      for (let cover = top; cover && cover.nodeType === 1; cover = cover.parentElement) {
        if (number(getComputedStyle(cover).opacity) <= 0.02) {
          transparentOverlay = true;
          break;
        }
      }

      if (top && !transparentOverlay && !el.contains(top) && !top.contains(el)) {
        reasons.push('covered by another element');
      }
    }
    return [...new Set(reasons)];
  }
  const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode()) && segments.length < LIMIT) {
    const text = node.nodeValue.trim().replace(/\s+/g, ' ');
    if (!text || text.length > 18000) continue;
    if (node.parentElement && forbidden.has(node.parentElement.tagName)) continue;
    const reasons = hiddenReasons(node);
    const parent = node.parentElement;
    const srOnly = parent && /(?:^|\s)(?:sr-only|visually-hidden|screen-reader-text)(?:\s|$)/i.test(parent.className || '');
    const accessibility = srOnly && reasons.every(x => ['clipped','zero-sized text','off-screen','tiny font'].includes(x));
    segments.push({text, visibility: reasons.length ? (accessibility ? 'nonvisual' : 'hidden') : 'visible',
                   reasons: accessibility ? ['screen-reader-only', ...reasons] : reasons, source:'dom'});
  }
  const elements = document.querySelectorAll('[alt],[title],[aria-label]');
  for (const el of elements) {
    if (segments.length >= LIMIT) break;
    for (const key of ['alt','title','aria-label']) {
      const text = (el.getAttribute(key) || '').trim().slice(0,1500);
      if (text) segments.push({text, visibility:'nonvisual', reasons:[key + ' attribute'], source:'attribute'});
    }
  }
  const comments = document.createTreeWalker(document.documentElement, NodeFilter.SHOW_COMMENT);
  while ((node = comments.nextNode()) && segments.length < LIMIT) {
    const text = node.nodeValue.trim().slice(0,1500);
    if (text) segments.push({text, visibility:'hidden', reasons:['HTML comment'], source:'comment'});
  }
  return segments;
}
