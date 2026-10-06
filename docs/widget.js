/*
 * OU AI RSS widget.
 * Embed:
 *   <div class="ou-ai-rss" data-feed="https://HOST/REPO/all.xml" data-limit="5"></div>
 *   <script src="https://HOST/REPO/widget.js" defer></script>
 * Options (data-*): feed (required), limit (default 5), title (heading text, "" for none),
 *                   subscribe ("false" hides the Subscribe link), dates ("false" hides dates)
 */
(function () {
  "use strict";
  var CSS =
    ".ou-ai-rss{font-family:inherit;line-height:1.4}" +
    ".ou-ai-rss h3{margin:0 0 .5em}" +
    ".ou-ai-rss ul{list-style:none;margin:0;padding:0}" +
    ".ou-ai-rss li{padding:.6em 0;border-bottom:1px solid rgba(0,0,0,.12)}" +
    ".ou-ai-rss li:last-child{border-bottom:0}" +
    ".ou-ai-rss a.ou-ai-rss-item{font-weight:600;text-decoration:none;color:#841617}" +
    ".ou-ai-rss a.ou-ai-rss-item:hover{text-decoration:underline}" +
    ".ou-ai-rss .ou-ai-rss-meta{font-size:.85em;opacity:.75;margin-top:.15em}" +
    ".ou-ai-rss .ou-ai-rss-sub{display:inline-flex;align-items:center;gap:.4em;margin-top:.75em;font-size:.9em;color:#841617}" +
    ".ou-ai-rss .ou-ai-rss-sub svg{width:1em;height:1em}";

  var RSS_ICON =
    '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6.18 15.64a2.18 2.18 0 1 1 0 4.36 2.18 2.18 0 0 1 0-4.36zM4 4.44A15.56 15.56 0 0 1 19.56 20h-2.83A12.73 12.73 0 0 0 4 7.27zm0 5.66a9.9 9.9 0 0 1 9.9 9.9h-2.83A7.07 7.07 0 0 0 4 12.93z"/></svg>';

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtDate(str, isEvent) {
    var d = new Date(str);
    if (isNaN(d)) return "";
    var opts = { month: "long", day: "numeric", year: "numeric", timeZone: "America/Chicago" };
    if (isEvent) { opts.hour = "numeric"; opts.minute = "2-digit"; }
    return d.toLocaleString("en-US", opts);
  }

  function render(el, xmlText) {
    var doc = new DOMParser().parseFromString(xmlText, "application/xml");
    var limit = parseInt(el.getAttribute("data-limit") || "5", 10);
    if (isNaN(limit) || limit < 0) limit = 5;
    var showDates = el.getAttribute("data-dates") !== "false";
    var title = el.getAttribute("data-title");
    var items = Array.prototype.slice.call(doc.getElementsByTagName("item"), 0, limit);
    var html = "";
    if (title) html += "<h3>" + esc(title) + "</h3>";
    if (limit > 0 && !items.length) html += "<p>No items right now.</p>";
    if (limit > 0) html += "<ul>";
    items.forEach(function (it) {
      var get = function (t) { var n = it.getElementsByTagName(t)[0]; return n ? n.textContent : ""; };
      var cat = get("category");
      var isEvent = cat === "Event";
      var meta = [];
      if (cat) meta.push(cat);
      if (showDates) { var d = fmtDate(get("pubDate"), isEvent); if (d) meta.push(d); }
      html += '<li><a class="ou-ai-rss-item" href="' + esc(get("link")) + '">' + esc(get("title")) + "</a>";
      if (meta.length) html += '<div class="ou-ai-rss-meta">' + esc(meta.join(" · ")) + "</div>";
      html += "</li>";
    });
    if (limit > 0) html += "</ul>";
    if (el.getAttribute("data-subscribe") !== "false") {
      html += '<a class="ou-ai-rss-sub" href="' + esc(el.getAttribute("data-feed")) + '">' + RSS_ICON + "Subscribe via RSS</a>";
    }
    el.innerHTML = html;
  }

  function init() {
    if (!document.getElementById("ou-ai-rss-css")) {
      var st = document.createElement("style");
      st.id = "ou-ai-rss-css";
      st.textContent = CSS;
      document.head.appendChild(st);
    }
    var nodes = document.querySelectorAll(".ou-ai-rss[data-feed]");
    Array.prototype.forEach.call(nodes, function (el) {
      if (el.getAttribute("data-loaded")) return;
      el.setAttribute("data-loaded", "1");
      fetch(el.getAttribute("data-feed"), { cache: "no-cache" })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(function (t) { render(el, t); })
        .catch(function () {
          el.innerHTML = '<a class="ou-ai-rss-sub" href="' + esc(el.getAttribute("data-feed")) + '">' + RSS_ICON + "Subscribe via RSS</a>";
        });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
