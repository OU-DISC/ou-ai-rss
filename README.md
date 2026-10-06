# OU AI RSS feeds

RSS feeds for the News & Events content on the OU Artificial Intelligence website
(<https://www.ou.edu/ai/news-and-events>), built automatically and hosted free on GitHub Pages.

| Feed | File | Source |
|---|---|---|
| News & Events (combined) | `all.xml` | both below |
| News | `news.xml` | The AEM "article list" on the AI News & Events page (OU stories tagged `ou:ai` from OU News, DISC, and the AI site) |
| Events | `events.xml` | OU LiveWhale calendar, DISC group (`calendar.ou.edu/live/rss/events/group/Data Institute for Societal Challenges`) |

## How it works

- `build_feeds.py` (Python standard library only) reads the public News & Events page, opens each
  linked article for its title, summary and image, mirrors the LiveWhale events RSS, and writes the
  feeds to `docs/`.
- `.github/workflows/build-feeds.yml` runs it every 3 hours (and on demand) and commits the result
  only when items change.
- GitHub Pages serves `docs/`.
- `docs/state.json` records when each story first appeared, so dates stay stable. On the first run
  it uses each page's "Updated m/d/yyyy" date, since OU article pages don't publish a date in their
  metadata.

Why not AEM's built-in feed? AEM's `.feed` selector only lists child pages of `news-and-events`
(not the tagged OU News/DISC stories), and on the public server it errors out partway through
("Cannot serve request to /content/ai/news-and-events.feed.html").

## One-time setup (about 10 minutes)

1. Create a **public** GitHub repo, e.g. `ou-ai-rss` (under the DISC GitHub org if there is one,
   so it isn't tied to one person).
2. Upload everything in this folder (keep the `.github/` and `docs/` folders).
3. **Settings → Pages**: Source = *Deploy from a branch*, Branch = `main`, Folder = `/docs`.
4. **Settings → Actions → General → Workflow permissions**: *Read and write permissions*.
5. **Actions → Build RSS feeds → Run workflow** to build the first feeds.
6. Feeds are then live at `https://<owner>.github.io/<repo>/all.xml` (plus `news.xml`, `events.xml`).
   The landing page `https://<owner>.github.io/<repo>/` has links and a live preview.

Optional: set a repo variable/secret `FEED_BASE_URL` if you later use a custom domain.

## Embed code for the OU web team

Replace `OWNER/REPO` with the real GitHub Pages path.

**Option A – Subscribe button only** (recommended; the page already lists news and events):

```html
<div class="ou-ai-rss" data-feed="https://OWNER.github.io/REPO/all.xml" data-limit="0"></div>
<script src="https://OWNER.github.io/REPO/widget.js" defer></script>
```

**Option B – Latest items + subscribe link** (e.g. for the DISC site or a sidebar):

```html
<div class="ou-ai-rss" data-feed="https://OWNER.github.io/REPO/news.xml"
     data-limit="5" data-title="Latest AI News"></div>
<script src="https://OWNER.github.io/REPO/widget.js" defer></script>
```

**Plain link** (no script, if scripts aren't allowed in that component):

```html
<a href="https://OWNER.github.io/REPO/all.xml">Subscribe via RSS</a>
```

Widget options: `data-feed` (required), `data-limit` (default 5; `0` = button only),
`data-title`, `data-subscribe="false"`, `data-dates="false"`.

## Maintenance

- If the AI News & Events page layout changes (the list items are `<li class="news-list-item">`),
  the workflow will fail with "No news items found" and GitHub emails the repo owner.
- To change which events are included, edit `EVENTS_RSS` in `build_feeds.py`
  (e.g. `.../group/Data%20Institute%20for%20Societal%20Challenges/tag/AI` for AI-tagged DISC events only).
- GitHub pauses scheduled workflows after 60 days with no repository activity; if that happens,
  re-enable it from the Actions tab.
