// Google Analytics with cookie consent (Consent Mode v2).
// GA loads with analytics/ad storage denied by default; storage is only
// granted after the visitor clicks "Accept" in the cookie banner.
(function () {
  var GA_ID = "G-NNG4793M31";
  var STORAGE_KEY = "cookie_consent"; // "granted" | "denied"

  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;

  // Default everything to denied until the visitor chooses.
  gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "denied"
  });

  gtag("js", new Date());
  gtag("config", GA_ID);

  // Load the GA library (respects the consent state set above).
  var s = document.createElement("script");
  s.async = true;
  s.src = "https://www.googletagmanager.com/gtag/js?id=" + GA_ID;
  document.head.appendChild(s);

  function grant() {
    gtag("consent", "update", {
      ad_storage: "granted",
      ad_user_data: "granted",
      ad_personalization: "granted",
      analytics_storage: "granted"
    });
  }

  function readChoice() {
    try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
  }

  function setConsent(value) {
    try { localStorage.setItem(STORAGE_KEY, value); } catch (e) {}
    if (value === "granted") grant();
    removeBanner();
  }

  function removeBanner() {
    var b = document.getElementById("cookie-banner");
    if (b && b.parentNode) b.parentNode.removeChild(b);
  }

  function showBanner() {
    if (document.getElementById("cookie-banner")) return;
    var wrap = document.createElement("div");
    wrap.id = "cookie-banner";
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-label", "Cookie consent");
    wrap.innerHTML =
      '<div class="cb-inner">' +
        '<p class="cb-text">We use cookies for basic analytics to understand how the site is used. ' +
        'You can accept or decline. See our <a href="/privacy/">Privacy Policy</a>.</p>' +
        '<div class="cb-actions">' +
          '<button type="button" class="cb-btn cb-decline" id="cb-decline">Decline</button>' +
          '<button type="button" class="cb-btn cb-accept" id="cb-accept">Accept</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(wrap);
    document.getElementById("cb-accept").addEventListener("click", function () { setConsent("granted"); });
    document.getElementById("cb-decline").addEventListener("click", function () { setConsent("denied"); });
  }

  function init() {
    var choice = readChoice();
    if (choice === "granted") {
      grant();
    } else if (choice !== "denied") {
      showBanner();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Let a "Cookie settings" link re-open the banner (used on the privacy page).
  window.openCookieSettings = function () {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
    showBanner();
  };

  // Banner styles (self-contained so it works on every page).
  var css =
    '#cookie-banner{position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#1A2132;color:#CBD5E8;' +
    'box-shadow:0 -4px 24px rgba(0,0,0,.18);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}' +
    '#cookie-banner .cb-inner{max-width:980px;margin:0 auto;padding:16px 20px;display:flex;align-items:center;' +
    'justify-content:space-between;gap:16px;flex-wrap:wrap;}' +
    '#cookie-banner .cb-text{font-size:.875rem;line-height:1.5;margin:0;flex:1;min-width:240px;}' +
    '#cookie-banner .cb-text a{color:#7BA4E8;}' +
    '#cookie-banner .cb-actions{display:flex;gap:10px;flex-shrink:0;}' +
    '#cookie-banner .cb-btn{padding:9px 20px;border-radius:8px;font-weight:700;font-size:.85rem;cursor:pointer;border:none;}' +
    '#cookie-banner .cb-accept{background:#4A7FD4;color:#fff;}' +
    '#cookie-banner .cb-accept:hover{background:#3A6FC4;}' +
    '#cookie-banner .cb-decline{background:transparent;color:#CBD5E8;border:1px solid #3A4A66;}' +
    '#cookie-banner .cb-decline:hover{background:#2D3A56;}' +
    '@media(max-width:560px){#cookie-banner .cb-inner{flex-direction:column;align-items:stretch;}' +
    '#cookie-banner .cb-actions{justify-content:flex-end;}}';
  var st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);
})();
