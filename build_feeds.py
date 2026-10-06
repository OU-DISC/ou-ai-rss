#!/usr/bin/env python3
"""
Build RSS feeds for the OU Artificial Intelligence website (www.ou.edu/ai).

Sources
  News   - the "News" article list on https://www.ou.edu/ai/news-and-events.
           In AEM this is an article-list component that pulls OU pages tagged
           `ou:ai` (from /content/news, /content/disc/news-events, etc.). AEM has
           no working public RSS for it, so we read the rendered list and each
           article's metadata.
  Events - the OU LiveWhale calendar (calendar.ou.edu), which already publishes
           RSS. We mirror it so subscribers get one stable URL we control.

Output (written to docs/, served by GitHub Pages)
  news.xml    AI news only
  events.xml  upcoming DISC/AI events only
  all.xml     news + events combined
  state.json  remembers each news item's first-seen date so pubDates stay stable

Standard library only. Run:  python build_feeds.py
"""

from __future__ import annotations

import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser

# ---------------------------------------------------------------- config ----
SITE_ROOT = "https://www.ou.edu"
NEWS_PAGE = os.environ.get("NEWS_PAGE", "https://www.ou.edu/ai/news-and-events")
EVENTS_RSS = os.environ.get(
    "EVENTS_RSS",
    "https://calendar.ou.edu/live/rss/events/group/"
    "Data%20Institute%20for%20Societal%20Challenges",
)
OUT_DIR = os.environ.get("OUT_DIR", os.path.join(os.path.dirname(__file__), "docs"))
MAX_NEWS = int(os.environ.get("MAX_NEWS", "25"))  # items kept in news feed
USER_AGENT = "OU-AI-RSS/1.0 (+https://www.ou.edu/ai; ai@ou.edu)"
GENERIC_DESCRIPTIONS = {"the university of oklahoma", ""}


def feed_base_url() -> str:
    """Public URL where the feeds live, e.g. https://org.github.io/repo/."""
    if os.environ.get("FEED_BASE_URL"):
        return os.environ["FEED_BASE_URL"].rstrip("/") + "/"
    repo = os.environ.get("GITHUB_REPOSITORY")  # set automatically in Actions
    if repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}/"
    return "https://example.github.io/ou-ai-rss/"


# --------------------------------------------------------------- fetching ---
def fetch(url: str, retries: int = 3) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                charset = r.headers.get_content_charset() or "utf-8"
                return r.read().decode(charset, errors="replace")
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            print(f"  retry {url}: {e}", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def public_url(href: str) -> str:
    """AEM links come as /content/<site>/...; the public URL drops /content."""
    path = urllib.parse.urljoin(SITE_ROOT + "/", href)
    parts = urllib.parse.urlsplit(path)
    p = parts.path
    if p.startswith("/content/"):
        p = p[len("/content"):]
    if p.endswith(".html"):
        p = p[:-5]
    return urllib.parse.urlunsplit(("https", "www.ou.edu", p, "", ""))


# ---------------------------------------------------------------- parsing ---
class NewsListParser(HTMLParser):
    """Collect <a> inside <li class="news-list-item">."""

    def __init__(self):
        super().__init__()
        self.in_li = 0
        self.cur = None
        self.items: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li" and "news-list-item" in (a.get("class") or "").split():
            self.in_li += 1
        elif tag == "a" and self.in_li and a.get("href"):
            self.cur = [a["href"], ""]

    def handle_data(self, data):
        if self.cur is not None:
            self.cur[1] += data

    def handle_endtag(self, tag):
        if tag == "a" and self.cur is not None:
            self.items.append((self.cur[0], " ".join(self.cur[1].split())))
            self.cur = None
        elif tag == "li" and self.in_li:
            self.in_li -= 1


class ArticleParser(HTMLParser):
    """Pull og/meta tags, first real paragraph and the 'Updated m/d/yyyy' footer."""

    def __init__(self):
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title = ""
        self._in_title = False
        self._in_p = False
        self._p = ""
        self.paragraphs: list[str] = []
        self.text_chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key and a.get("content") is not None:
                self.meta.setdefault(key.lower(), a["content"])
        elif tag == "title":
            self._in_title = True
        elif tag == "p":
            self._in_p, self._p = True, ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "p" and self._in_p:
            self._in_p = False
            t = " ".join(self._p.split())
            if len(t) > 60:
                self.paragraphs.append(t)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_p:
            self._p += data
        self.text_chunks.append(data)


def parse_article(url: str) -> dict:
    p = ArticleParser()
    p.feed(fetch(url))
    m = p.meta
    title = m.get("og:title") or p.title.strip()
    desc = (m.get("og:description") or m.get("description") or "").strip()
    if desc.lower() in GENERIC_DESCRIPTIONS and p.paragraphs:
        desc = p.paragraphs[0]
    if len(desc) > 400:
        desc = desc[:397].rsplit(" ", 1)[0] + "..."
    image = m.get("og:image") or ""
    if image and not image.startswith("http"):
        image = urllib.parse.urljoin(SITE_ROOT, image)
    if image.rstrip("/").endswith(("ou.edu", "/content/dam")):
        image = ""
    updated = None
    mt = re.search(r"Updated\s+(\d{1,2})/(\d{1,2})/(\d{4})", " ".join(p.text_chunks))
    if mt:
        mo, d, y = map(int, mt.groups())
        updated = datetime(y, mo, d, 12, tzinfo=timezone.utc)
    return {"title": html.unescape(title), "description": html.unescape(desc),
            "image": image, "updated": updated}


# ------------------------------------------------------------------ state ---
def load_state(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"news": {}}


def save_state(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")


# ------------------------------------------------------------------ build ---
def collect_news(state: dict) -> list[dict]:
    print(f"News: {NEWS_PAGE}")
    lp = NewsListParser()
    lp.feed(fetch(NEWS_PAGE))
    if not lp.items:
        raise RuntimeError("No news items found - page layout may have changed.")
    now = datetime.now(timezone.utc)
    seen = state.setdefault("news", {})
    current = []
    for order, (href, text) in enumerate(lp.items):
        url = public_url(href)
        current.append(url)
        rec = seen.get(url)
        try:
            art = parse_article(url)
        except Exception as e:  # noqa: BLE001
            print(f"  ! could not read {url}: {e}", file=sys.stderr)
            art = {"title": text, "description": "", "image": "", "updated": None}
        if rec is None:
            # First time we see it. On the very first run use the page's
            # "Updated" date; afterwards, the date we discovered it.
            first_run = not state.get("initialized")
            date = art["updated"] if (first_run and art["updated"]) else now
            rec = {"first_seen": date.isoformat()}
            print(f"  + {art['title'] or text}")
        rec.update({
            "title": art["title"] or text,
            "description": art["description"],
            "image": art["image"],
            "list_order": order,
        })
        seen[url] = rec
    state["initialized"] = True
    # Keep items no longer on the page (the page only shows 10) for history.
    items = [dict(url=u, **r) for u, r in seen.items()]
    items.sort(key=lambda r: (r["first_seen"], -r.get("list_order", 99)), reverse=True)
    # Prune state to a bounded size.
    keep = {i["url"] for i in items[: MAX_NEWS * 2]} | set(current)
    state["news"] = {u: r for u, r in seen.items() if u in keep}
    return items[:MAX_NEWS]


def collect_events() -> list[dict]:
    print(f"Events: {EVENTS_RSS}")
    root = ET.fromstring(fetch(EVENTS_RSS).encode("utf-8"))
    out = []
    for it in root.iter("item"):
        def g(tag):
            el = it.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        image = ""
        for el in it:
            if el.tag.endswith("}image") and el.text:
                image = el.text.strip()
        location = ""
        for el in it:
            if el.tag.endswith("}featurename") and el.text:
                location = el.text.strip()
        out.append({
            "title": g("title"), "url": g("link"), "guid": g("guid") or g("link"),
            "description": g("description"), "pubDate": g("pubDate"),
            "image": image, "location": location,
        })
    return out


# ----------------------------------------------------------------- output ---
def rfc822(iso_or_rfc: str) -> str:
    if not iso_or_rfc:
        return email.utils.format_datetime(datetime.now(timezone.utc))
    if "T" in iso_or_rfc:
        return email.utils.format_datetime(datetime.fromisoformat(iso_or_rfc))
    return iso_or_rfc


def sort_key(item: dict) -> float:
    try:
        return email.utils.parsedate_to_datetime(item["pubDate"]).timestamp()
    except Exception:  # noqa: BLE001
        return 0.0


def write_rss(path: str, title: str, link: str, desc: str, self_url: str,
              items: list[dict]) -> None:
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
    ET.register_namespace("media", "http://search.yahoo.com/mrss/")
    A = "{http://www.w3.org/2005/Atom}"
    M = "{http://search.yahoo.com/mrss/}"
    rss = ET.Element("rss", {"version": "2.0"})
    ch = ET.SubElement(rss, "channel")
    ET.SubElement(ch, "title").text = title
    ET.SubElement(ch, "link").text = link
    ET.SubElement(ch, "description").text = desc
    ET.SubElement(ch, "language").text = "en-us"
    ET.SubElement(ch, "lastBuildDate").text = email.utils.format_datetime(
        datetime.now(timezone.utc))
    ET.SubElement(ch, "ttl").text = "180"
    ET.SubElement(ch, A + "link", {"href": self_url, "rel": "self",
                                    "type": "application/rss+xml"})
    for it in items:
        e = ET.SubElement(ch, "item")
        ET.SubElement(e, "title").text = it["title"]
        ET.SubElement(e, "link").text = it["url"]
        ET.SubElement(e, "guid", {"isPermaLink": "true" if it["guid"] == it["url"]
                                   else "false"}).text = it["guid"]
        ET.SubElement(e, "pubDate").text = it["pubDate"]
        if it.get("category"):
            ET.SubElement(e, "category").text = it["category"]
        if it.get("description"):
            ET.SubElement(e, "description").text = it["description"]
        if it.get("image"):
            ET.SubElement(e, M + "content", {"url": it["image"], "medium": "image"})
    ET.indent(rss, space="  ")
    data = ET.tostring(rss, encoding="unicode", xml_declaration=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<?xml-stylesheet type="text/xsl" href="feed.xsl"?>\n')
        f.write(data + "\n")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    base = feed_base_url()
    state_path = os.path.join(OUT_DIR, "state.json")
    state = load_state(state_path)

    news_raw = collect_news(state)
    news = [{
        "title": n["title"], "url": n["url"], "guid": n["url"],
        "pubDate": rfc822(n["first_seen"]), "description": n["description"],
        "image": n["image"], "category": "News",
    } for n in news_raw]

    try:
        events_raw = collect_events()
    except Exception as e:  # noqa: BLE001  - events failing shouldn't kill news
        print(f"  ! events feed unavailable: {e}", file=sys.stderr)
        events_raw = []
    events = []
    for ev in events_raw:
        d = ev["description"]
        if ev["location"]:
            d = f"<p><strong>Location:</strong> {html.escape(ev['location'])}</p>" + d
        events.append({**ev, "description": d, "category": "Event"})

    write_rss(os.path.join(OUT_DIR, "news.xml"), "OU Artificial Intelligence - News",
              NEWS_PAGE, "News about artificial intelligence at the University of Oklahoma.",
              base + "news.xml", news)
    if events_raw:
        write_rss(os.path.join(OUT_DIR, "events.xml"),
                  "OU Artificial Intelligence - Events", NEWS_PAGE,
                  "Upcoming AI and DISC events at the University of Oklahoma.",
                  base + "events.xml", events)
    # Upcoming events (soonest first) then news (newest first). RSS readers
    # re-sort by date anyway; this order is what the embed widget shows.
    combined = sorted(events, key=sort_key) + news
    write_rss(os.path.join(OUT_DIR, "all.xml"),
              "OU Artificial Intelligence - News & Events", NEWS_PAGE,
              "News and events about artificial intelligence at the University of Oklahoma.",
              base + "all.xml", combined)
    save_state(state_path, state)
    print(f"Done: {len(news)} news, {len(events)} events -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
