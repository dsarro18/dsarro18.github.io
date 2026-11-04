import os, re, sys, json, html
from datetime import datetime
from urllib.parse import quote

ROOT = sys.argv[1]
BASE = "https://dsarro18.github.io/"
AUTHOR = "Dominic Sarro"
SITE = "Fragments"
SITE_DESC = ("Fragments by Dominic Sarro: short essays on institutional decay, authenticity, "
             "and systems that substitute proxies for substance.")
MARK = "<!-- seo -->"

def url_for(fname):
    return BASE + quote(fname)

def strip_tags(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()

def excerpt(body):
    paras = re.findall(r"<p>(.*?)</p>", body, flags=re.S)
    text = ""
    for p in paras:
        t = strip_tags(p)
        if not t or re.fullmatch(r"[A-Z][a-z]+ \d{1,2}, \d{4}", t) or "Return to Home" in t:
            continue
        text = (text + " " + t).strip()
        if len(text) >= 140:
            break
    if len(text) > 160:
        text = text[:157].rsplit(" ", 1)[0] + "…"
    return text

def esc(s):
    return html.escape(s, quote=True)

def head_block(title, desc, url, kind, date_iso=None, h1=None):
    lines = [
        MARK,
        f'<meta name="description" content="{esc(desc)}" />',
        f'<meta name="author" content="{AUTHOR}" />',
        f'<link rel="canonical" href="{url}" />',
        f'<meta property="og:type" content="{kind}" />',
        f'<meta property="og:site_name" content="{SITE}" />',
        f'<meta property="og:title" content="{esc(h1 or title)}" />',
        f'<meta property="og:description" content="{esc(desc)}" />',
        f'<meta property="og:url" content="{url}" />',
        '<meta name="twitter:card" content="summary" />',
    ]
    if kind == "article":
        lines.append(f'<meta property="article:published_time" content="{date_iso}" />')
        lines.append(f'<meta property="article:author" content="{AUTHOR}" />')
        ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": h1,
              "datePublished": date_iso, "author": {"@type": "Person", "name": AUTHOR, "url": BASE},
              "publisher": {"@type": "Person", "name": AUTHOR}, "description": desc,
              "mainEntityOfPage": url, "isPartOf": {"@type": "Blog", "name": SITE, "url": BASE}}
    else:
        lines.append(f'<link rel="alternate" type="application/rss+xml" title="{SITE}" href="{BASE}feed.xml" />')
        ld = {"@context": "https://schema.org", "@type": "Blog", "name": SITE, "url": BASE,
              "description": desc, "author": {"@type": "Person", "name": AUTHOR, "url": BASE}}
    lines.append('<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False) + "</script>")
    lines.append(MARK)
    return "\n".join(lines) + "\n"

def apply(path, title, block):
    s = open(path, encoding="utf-8").read()
    s = re.sub(rf"{MARK}.*?{MARK}\n?", "", s, flags=re.S)          # idempotent
    s = re.sub(r'\s*<meta name="description"[^>]*>', "", s)
    s = re.sub(r"<title>.*?</title>", f"<title>{esc(title)}</title>\n" + block.rstrip("\n"), s, count=1, flags=re.S)
    open(path, "w", encoding="utf-8").write(s)

posts = []
for f in sorted(os.listdir(ROOT)):
    m = re.match(r"(\d\d)-(\d\d)-(\d{4}) - .*\.html$", f)
    if not m:
        continue
    mm, dd, yyyy = m.groups()
    date_iso = f"{yyyy}-{mm}-{dd}"
    s = open(os.path.join(ROOT, f), encoding="utf-8").read()
    h1 = strip_tags(re.search(r"<h1>(.*?)</h1>", s, re.S).group(1))
    desc = excerpt(s)
    title = f"{h1} — {SITE} by {AUTHOR}"
    apply(os.path.join(ROOT, f), title, head_block(title, desc, url_for(f), "article", date_iso, h1))
    posts.append((date_iso, f, h1, desc))

posts.sort(reverse=True)

# Add any post missing from the homepage list, placed by date
idx_path = os.path.join(ROOT, "index.html")
idx = open(idx_path, encoding="utf-8").read()
for d, f, t, _ in sorted(posts):
    if f'href="{f}"' in idx:
        continue
    pretty = datetime.strptime(d, "%Y-%m-%d").strftime("%B %-d, %Y")
    li = f'      <li><span class="date">{pretty}</span><a href="{f}">{esc(t)}</a></li>\n'
    newer = [p for p in posts if p[0] > d and f'href="{p[1]}"' in idx]
    if newer:  # insert after the oldest post that is newer than this one
        anchor_f = min(newer)[1]
        m = re.search(rf'[ \t]*<li>.*?href="{re.escape(anchor_f)}".*?</li>\n', idx)
        idx = idx[:m.end()] + li + idx[m.end():]
    else:
        idx = re.sub(r'(<ul class="posts">\n)', lambda m: m.group(1) + li, idx, count=1)
    print("added to homepage:", f)
open(idx_path, "w", encoding="utf-8").write(idx)

apply(os.path.join(ROOT, "index.html"), f"{SITE} — Essays by {AUTHOR}",
      head_block(f"{SITE} — Essays by {AUTHOR}", SITE_DESC, BASE, "website", h1=f"{SITE} — Essays by {AUTHOR}"))

# sitemap
sm = ['<?xml version="1.0" encoding="UTF-8"?>',
      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
      f"  <url><loc>{BASE}</loc><lastmod>{posts[0][0]}</lastmod></url>"]
sm += [f"  <url><loc>{esc(url_for(f))}</loc><lastmod>{d}</lastmod></url>" for d, f, _, _ in posts]
sm.append("</urlset>")
open(os.path.join(ROOT, "sitemap.xml"), "w").write("\n".join(sm) + "\n")

open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")

# RSS feed
def rfc822(d):
    return datetime.strptime(d, "%Y-%m-%d").strftime("%a, %d %b %Y 12:00:00 +0000")
items = "".join(
    f"<item><title>{esc(t)}</title><link>{esc(url_for(f))}</link><guid>{esc(url_for(f))}</guid>"
    f"<pubDate>{rfc822(d)}</pubDate><description>{esc(ds)}</description></item>\n"
    for d, f, t, ds in posts)
rss = (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>\n'
       f"<title>{SITE}</title><link>{BASE}</link><description>{esc(SITE_DESC)}</description>"
       f"<language>en</language><lastBuildDate>{rfc822(posts[0][0])}</lastBuildDate>\n{items}</channel></rss>\n")
open(os.path.join(ROOT, "feed.xml"), "w").write(rss)
print(len(posts), "posts updated")
