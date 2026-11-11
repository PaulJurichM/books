#!/usr/bin/env python3
"""Собирает сайт из папки content/ в папку docs/ (её публикует GitHub Pages).

Новый рассказ: положить .md в папку сборника (номер в имени файла задаёт порядок)
и запустить  python3 build.py
"""
import datetime, html, json, os, re, shutil

SRC, OUT = "content", "docs"
AUTHOR = "Павел Юрич"
SITE = "Павел Юрич. Проза"
PLACE = "Тбилиси"
BASE = "https://malari.me/books/"  # адрес сайта: канонические ссылки, карта сайта, RSS, превью
OG_DEFAULT = "assets/og.jpg"       # картинка превью для главной и страниц без иллюстрации
PUBLISHED = "published.json"       # даты появления текстов на сайте (для RSS); новые дописываются сами
URLS = []                          # (адрес, дата) для sitemap.xml
MONTHS = ("январь февраль март апрель май июнь июль август "
          "сентябрь октябрь ноябрь декабрь").split()
MONTHS_GEN = ("января февраля марта апреля мая июня июля августа "
              "сентября октября ноября декабря").split()

# Полки главной страницы, в этом порядке. Сборник встаёт на полку строкой «shelf: id»
# в _collection.md, место на полке — «place: N». Сборник без полки идёт карточкой «Вне циклов».
SHELVES = [
    ("history", "Исторические детективы",
     "Древний Рим, Китай эпохи Тан, Тифлис 1904 года, Москва 1919-го и Берлин 1936-го. По эпохам."),
    ("oxford", "Оксфорд: Морс и Льюис",
     "Одна вселенная длиной больше ста лет: от деда инспектора Морса до Льюиса после службы. "
     "Полка идёт по годам жизни героев, читать можно подряд."),
    ("homage", "Поклоны", "Рассказы в мирах и манере любимых писателей."),
    ("dark", "Тёмное", "Хоррор и триллеры. То, что находит тебя само и не отпускает."),
    ("home", "Здесь и тогда", "Дом, двор и застолье в Грузии — и байки из прошлой жизни."),
]
# «unit:» в _collection.md: чем считать тексты сборника на плитке
UNITS = {"рассказ": ("рассказ", "рассказа", "рассказов"), "повесть": ("повесть", "повести", "повестей"),
         "глава": ("глава", "главы", "глав"), "дело": ("дело", "дела", "дел")}
EXTRA = ("От автора", "Предисловие", "Послесловие")  # не считаются в числе текстов


def read(path):
    raw = open(path, encoding="utf-8").read()
    meta, body = {}, raw
    m = re.match(r"---\n(.*?)\n---\n?(.*)", raw, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body.strip()


_FN = None  # сноски текущего текста: {метка: номер}


def inline(text):
    """Экранирует текст; *так* помечается курсив, [текст](https://…) — ссылка,
    [^метка] — сноска (определение: строка «[^метка]: текст» в конце файла)."""
    t = re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", html.escape(text))
    t = re.sub(r"\[([^\]^]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
    if _FN is not None:
        def ref(m):
            k = m.group(1)
            first = k not in _FN
            n = _FN.setdefault(k, len(_FN) + 1)
            back = f' id="fnref-{n}"' if first else ""
            return f'<sup class="fn"><a{back} href="#fn-{n}">{n}</a></sup>'
        t = re.sub(r"\[\^([^\]\s]+)\]", ref, t)
    return t


def month(s):
    m = re.match(r"(\d{4})-(\d{2})$", s or "")
    return f"{MONTHS[int(m.group(2)) - 1]} {m.group(1)}" if m else ""


def signature(written, revised=""):
    """Подпись в конце текста: written: 2025-03 → «Тбилиси, март 2025»;
    с revised: 2026-10 → «Тбилиси, март 2025 — октябрь 2026» (новая редакция)."""
    w, r = month(written), month(revised)
    if not w:
        return ""
    return f'<p class="sign"><em>{PLACE}, {w}{" — " + r if r else ""}</em></p>'


def render(body):
    global _FN
    notes = {}
    def grab(m):
        notes[m.group(1)] = m.group(2).strip()
        return ""
    body = re.sub(r"^\[\^([^\]\s]+)\]:[ \t]*(.+)$", grab, body, flags=re.M)
    _FN = {} if notes else None
    out = []
    for block in re.split(r"\n\s*\n", body):
        block = block.strip("\n")
        if not block.strip():
            continue
        if block.strip() in ("⁂", "* * *"):
            out.append('<p class="sep">⁂</p>')
        elif block.startswith("## "):
            out.append(f"<h2>{html.escape(block[3:].strip())}</h2>")
        elif block.startswith(">"):
            # цитата: эпиграф, письмо, документ; пустая строка «>» делит абзацы
            text = "\n".join(re.sub(r"^>\s?", "", x) for x in block.split("\n"))
            paras = ["<p>" + "<br>\n".join(inline(x.strip()) for x in p.split("\n")) + "</p>"
                     for p in re.split(r"\n\s*\n", text) if p.strip()]
            out.append("<blockquote>" + "\n".join(paras) + "</blockquote>")
        elif "\n" in block:
            lines = "<br>\n".join(inline(x.strip()) for x in block.split("\n"))
            out.append(f'<p class="verse">{lines}</p>')
        else:
            out.append(f"<p>{inline(block.strip())}</p>")
    if notes:
        items = []
        for k, n in sorted(_FN.items(), key=lambda kv: kv[1]):
            items.append(f'<li id="fn-{n}">{inline(notes.get(k, ""))} '
                         f'<a class="back" href="#fnref-{n}" aria-label="Вернуться к тексту">↩</a></li>')
        out.append('<section class="notes"><h2>Примечания</h2><ol>' + "\n".join(items) + "</ol></section>")
    _FN = None
    return "\n".join(out)


def plain(text):
    """Текст без разметки: для описаний в поиске и превью."""
    t = re.sub(r"\[\^[^\]\s]+\]", "", text)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"[*_#>]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def snippet(body, limit=180):
    """Описание страницы: первый обычный абзац текста (без эпиграфов, заголовков и стихов),
    обрезанный по слову."""
    body = re.sub(r"^\[\^[^\]\s]+\]:.*$", "", body, flags=re.M)
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if not b or b.startswith(("##", ">", "⁂", "* * *")) or "\n" in b:
            continue
        t = plain(b)
        if len(t) < 80:
            continue
        if len(t) > limit:
            t = t[:limit].rsplit(" ", 1)[0].rstrip(",;:—–- ") + "…"
        return t
    return ""


def minutes(body):
    return max(1, round(len(body.split()) / 180))


def page(title, content, root, crumbs="", wide=False, url=None, desc="", image="",
         kind="website", ld=None, date=""):
    """url — адрес страницы относительно BASE (None: страница не идёт в карту сайта)."""
    mcls = ' class="wide"' if wide else ""
    head = ""
    if url is not None:
        full = BASE + re.sub(r"(^|/)index\.html$", r"\1", url)
        URLS.append((full, date))
        img = BASE + (image or OG_DEFAULT)
        d = html.escape(desc)
        head = (f'<meta name="description" content="{d}">\n'
                f'<link rel="canonical" href="{full}">\n'
                f'<meta property="og:type" content="{kind}">\n'
                f'<meta property="og:site_name" content="{html.escape(SITE)}">\n'
                f'<meta property="og:locale" content="ru_RU">\n'
                f'<meta property="og:title" content="{html.escape(title)}">\n'
                f'<meta property="og:description" content="{d}">\n'
                f'<meta property="og:url" content="{full}">\n'
                f'<meta property="og:image" content="{img}">\n'
                f'<meta name="twitter:card" content="summary_large_image">\n')
        if ld:
            ld = dict(ld, url=full, image=img)
            head += ('<script type="application/ld+json">'
                     + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n")
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{head}<link rel="alternate" type="application/rss+xml" title="{html.escape(SITE)}: новые тексты" href="{BASE}feed.xml">
<script>(function(){{try{{var t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t;var f=localStorage.getItem('fs');if(f)document.documentElement.style.setProperty('--fs',f+'px');}}catch(e){{}}}})();</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=PT+Sans:wght@400;700&family=PT+Serif:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/style.css">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
</head>
<body>
<header class="top">
  <a class="brand" href="{root or './'}">{AUTHOR}</a>
  <nav>
    <a href="/creative/">← Творчество</a>
    <a href="{root or './'}">Сборники</a>
    <a href="{root}ekranizaciya.html">Экранизация</a>
    <button class="ctl" id="fs-down" type="button" aria-label="Уменьшить шрифт">A−</button>
    <button class="ctl" id="fs-up" type="button" aria-label="Увеличить шрифт">A+</button>
    <button class="ctl" id="theme" type="button" aria-label="Переключить тему">Тёмная</button>
  </nav>
</header>
<main{mcls}>
{crumbs}
{content}
</main>
<footer>
  <p>© {AUTHOR}, 2026. Читать можно свободно. <a href="{root}ekranizaciya.html">Экранизация и права</a> · <a href="{BASE}feed.xml">RSS</a> · <a href="/">malari.me</a></p>
</footer>
<script src="{root}assets/site.js"></script>
<script data-goatcounter="https://malari.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
"""

PERSON = {"@type": "Person", "name": AUTHOR, "alternateName": "Павел Мальков", "url": "https://malari.me/"}


def write_sitemap():
    rows = []
    for u, d in URLS:
        rows.append(f"<url><loc>{html.escape(u)}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>")
    open(f"{OUT}/sitemap.xml", "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n")


def write_feed(items, limit=30):
    """RSS: последние тексты, появившиеся на сайте (дата из published.json)."""
    items = sorted(items, key=lambda x: (x["date"], x["order"]), reverse=True)[:limit]
    def rfc(d):
        dt = datetime.datetime.strptime(d, "%Y-%m-%d").replace(hour=12, tzinfo=datetime.timezone.utc)
        return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
    rows = [f"<item><title>{html.escape(x['title'])}</title><link>{x['url']}</link>"
            f"<guid isPermaLink=\"true\">{x['url']}</guid><pubDate>{rfc(x['date'])}</pubDate>"
            f"<description>{html.escape(x['desc'])}</description></item>" for x in items]
    open(f"{OUT}/feed.xml", "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" '
        'xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
        f"<title>{html.escape(SITE)}</title><link>{BASE}</link>"
        "<description>Новые повести и рассказы на сайте</description><language>ru</language>"
        f'<atom:link href="{BASE}feed.xml" rel="self" type="application/rss+xml"/>'
        + "".join(rows) + "</channel></rss>\n")


def toc(works, prefix, cls=""):
    """Оглавление сборника. Если в сборнике есть разделы (section в шапке файла),
    рассказы идут вложенным списком под своим разделом и без номеров."""
    def li(w):
        if w["url"]:  # внешняя ссылка (хронотопы): открывается в новой вкладке
            return (f'<a href="{html.escape(w["url"])}" target="_blank" rel="noopener">'
                    f'{html.escape(w["title"])}</a><span class="min">↗</span>')
        return (f'<a href="{prefix}{w["slug"]}.html">{html.escape(w["title"])}</a>'
                f'<span class="min">{w["min"]} мин</span>')
    c = f' class="{cls}"' if cls else ""
    if any(w["part"] for w in works):
        # сборник из частей (part в шапке первого файла части): подзаголовок и сквозная нумерация
        out, items, start = [], [], 1
        def flush():
            nonlocal items, start
            if items:
                out.append(f'<ol{c} start="{start}">' + "\n".join(items) + "</ol>")
                start += len(items)
            items = []
        for w in works:
            if w["nonum"]:  # пролог, эпилог: строка без номера, нумерация не сдвигается
                flush()
                out.append(f'<ul class="{(cls + " nonum").strip()}"><li>{li(w)}</li></ul>')
                continue
            if w["part"]:
                flush()
                out.append(f'<h3 class="part">{html.escape(w["part"])}</h3>')
            items.append(f"<li>{li(w)}</li>")
        flush()
        return "\n".join(out)
    if not any(w["section"] for w in works):
        return f'<ol{c}>' + "\n".join(f"<li>{li(w)}</li>" for w in works) + "</ol>"
    out, sub, open_li = [], [], False
    def close():
        nonlocal sub, open_li
        if open_li:
            out.append((f'<ul class="sub">{"".join(sub)}</ul>' if sub else "") + "</li>")
        sub, open_li = [], False
    for w in works:
        if w["section"]:
            close()
            out.append(f'<li class="sec">{li(w)}')
            open_li = True
        elif open_li:
            sub.append(f"<li>{li(w)}</li>")
        else:
            out.append(f"<li>{li(w)}</li>")
    close()
    cc = (cls + " nested").strip()
    return f'<ul class="{cc}">' + "\n".join(out) + "</ul>"


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    shutil.copytree("assets", f"{OUT}/assets")
    open(f"{OUT}/.nojekyll", "w").close()
    if os.path.exists("CNAME"):
        shutil.copy("CNAME", f"{OUT}/CNAME")

    cols = []
    for d in sorted(os.listdir(SRC)):
        p = os.path.join(SRC, d)
        if not os.path.isdir(p):
            continue
        cmeta, cbody = read(os.path.join(p, "_collection.md"))
        slug = re.sub(r"^\d+-", "", d)
        works = []
        for f in sorted(os.listdir(p)):
            if f.startswith("_") or not f.endswith(".md"):
                continue
            meta, body = read(os.path.join(p, f))
            wslug = re.sub(r"^\d+-", "", f[:-3])
            pic = next((f"images/{wslug}{e}" for e in (".jpg", ".png", ".webp")
                        if os.path.exists(os.path.join(p, "images", wslug + e))), "")
            works.append({"slug": wslug, "title": meta.get("title", f),
                          "body": body, "min": minutes(body), "pic": pic,
                          "caption": meta.get("caption", ""),
                          "section": bool(meta.get("section", "")),
                          "part": meta.get("part", ""), "nonum": bool(meta.get("nonum", "")), "url": meta.get("url", ""),
                          "alias": meta.get("alias", ""), "written": meta.get("written", ""), "revised": meta.get("revised", "")})
        theme = os.path.exists(os.path.join(p, "theme.mp3"))  # главная тема цикла (Suno)
        cover = os.path.exists(os.path.join(p, "cover.jpg"))  # обложка плитки (make_covers.py)
        img = os.path.join(p, "images")
        if os.path.isdir(img):
            shutil.copytree(img, f"{OUT}/{slug}/images")
        if cover:
            os.makedirs(f"{OUT}/{slug}", exist_ok=True)
            shutil.copy(os.path.join(p, "cover.jpg"), f"{OUT}/{slug}/cover.jpg")
        cols.append({"slug": slug, "title": cmeta.get("title", d), "about": cbody, "works": works,
                     "theme": theme, "cover": cover, "desc": cmeta.get("description", ""),
                     # место на главной (см. SHELVES) и подпись плитки
                     "shelf": cmeta.get("shelf", ""), "place": float(cmeta.get("place", "0") or 0),
                     "kind": cmeta.get("kind", ""), "unit": cmeta.get("unit", ""),
                     "years": cmeta.get("years", ""), "status": cmeta.get("status", ""),
                     "count_prefix": cmeta.get("count_prefix", "")})

    # главная тема цикла: копия трека и плеер на страницах сборника
    for c in cols:
        if c["theme"]:
            d = next(x for x in os.listdir(SRC) if re.sub(r"^\d+-", "", x) == c["slug"])
            os.makedirs(f"{OUT}/{c['slug']}", exist_ok=True)
            shutil.copy(os.path.join(SRC, d, "theme.mp3"), f"{OUT}/{c['slug']}/theme.mp3")

    def theme(c, note):
        if not c["theme"]:
            return ""
        return (f'<div class="theme"><span class="tl">♪ Главная тема цикла</span>'
                f'<audio controls preload="none" src="theme.mp3"></audio>'
                f'<span class="tn">{note}</span></div>')

    # главная: плитки с обложками, клик ведёт в сборник
    def plural(n, forms=("произведение", "произведения", "произведений")):
        k = 0 if n % 10 == 1 and n % 100 != 11 else 1 if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 2
        return f"{n} {forms[k]}"

    def blurb(text):
        """Первая фраза аннотации сборника, без разметки."""
        t = re.sub(r"[*_>#]", "", text).split("\n\n")[0].strip()
        m = re.match(r"(.+?[.!?…])(\s|$)", t)
        return (m.group(1) if m else t)[:200]

    published = json.load(open(PUBLISHED, encoding="utf-8")) if os.path.exists(PUBLISHED) else {}
    today = datetime.date.today().isoformat()

    def count(c):
        """Сколько в сборнике единиц (рассказов, глав…): без предисловий, послесловий,
        параграфов учебника и внешних ссылок; count_prefix — считать только файлы с таким началом."""
        ws = [w for w in c["works"] if not w["url"] and w["title"] not in EXTRA
              and not w["title"].startswith("§")]
        if c["count_prefix"]:
            ws = [w for w in ws if w["slug"].startswith(c["count_prefix"])]
        return len(ws)

    def label(c):
        n = count(c)
        what = plural(n, UNITS[c["unit"]]) if c["unit"] in UNITS else plural(n)
        return " · ".join(x for x in (c["kind"], what, c["status"]) if x)

    # «Новое на сайте»: три сборника, где тексты появлялись последними (даты из published.json)
    fresh = []
    for c in cols:
        reads = [w for w in c["works"] if not w["url"]]
        if not reads:
            continue
        dated = [(published.get(f'{c["slug"]}/{w["slug"]}', today), i, w) for i, w in enumerate(reads)]
        last = max(d for d, _, _ in dated)
        day = [w for d, _, w in dated if d == last]
        fresh.append((last, c, day))
    fresh = sorted(fresh, key=lambda x: x[0], reverse=True)[:3]
    fresh_slugs = {c["slug"] for _, c, _ in fresh}

    def cover_html(c, name):
        return (f'<img src="{c["slug"]}/cover.jpg" alt="" loading="lazy">' if c["cover"] else
                f'<span class="tcover" style="--h:{sum(map(ord, c["slug"])) * 47 % 360}">'
                f'<span>{html.escape(name[0])}</span></span>')

    PLAY = ('<svg class="i-play" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">'
            '<path d="M4.5 2.5v11l9-5.5z" fill="currentColor"/></svg>'
            '<svg class="i-pause" width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">'
            '<rect x="3" y="2" width="3.5" height="12" rx="1" fill="currentColor"/>'
            '<rect x="9.5" y="2" width="3.5" height="12" rx="1" fill="currentColor"/></svg>')

    def tile(c, chips=True):
        name, _, sub = c["title"].partition(". ")
        badges = ""
        if chips:
            badges = ((f'<span class="ty">{html.escape(c["years"])}</span>' if c["years"] else "")
                      + ('<span class="tnew">новое</span>' if c["slug"] in fresh_slugs else ""))
            badges = f'<span class="tch">{badges}</span>' if badges else ""
        play = (f'<button class="tplay" type="button" data-src="{c["slug"]}/theme.mp3" aria-pressed="false" '
                f'aria-label="Главная тема «{html.escape(name)}»" title="Главная тема цикла">{PLAY}</button>'
                if c["theme"] else "")
        return (f'<div class="tw"><a class="tile" href="{c["slug"]}/"><span class="cv">{cover_html(c, name)}</span>'
                f'{badges}<span class="tb"><span class="tt">{html.escape(name)}</span>'
                + (f'<span class="ts">{html.escape(sub)}</span>' if sub else "")
                + (f'<span class="ta">{html.escape(blurb(c["about"]))}</span>' if c["about"] else "")
                + f'<span class="tn">{html.escape(label(c))}</span></span></a>{play}</div>')

    def day_ru(d):
        y, m, dd = map(int, d.split("-"))
        return f"{dd} {MONTHS_GEN[m - 1]}"

    fcards = []
    for last, c, day in fresh:
        name = c["title"].partition(". ")[0]
        main_ = [x for x in day if x["title"] not in EXTRA] or day
        w = main_[-1]  # последний текст дня, послесловие не в счёт
        what = f"«{w['title']}»" if w["title"] != name else "Новый текст"
        if len(day) > 1:
            what += " и ещё " + plural(len(day) - 1, UNITS.get(c["unit"], ("текст", "текста", "текстов")))
        fcards.append(f'<a class="fc" href="{c["slug"]}/{w["slug"]}.html">'
                      f'<span class="fi">{cover_html(c, name)}</span>'
                      f'<span class="fb"><span class="fd">{day_ru(last)}</span>'
                      f'<span class="ft">{html.escape(name)}</span>'
                      f'<span class="fw">{html.escape(what)}</span></span></a>')

    shelves, chips = [], []
    for sid, sname, sdesc in SHELVES:
        cs = sorted((c for c in cols if c["shelf"] == sid), key=lambda c: c["place"])
        if not cs:
            continue
        chips.append(f'<a class="chip" href="#sh-{sid}">{html.escape(sname)}</a>')
        shelves.append(f'<section class="sh" id="sh-{sid}"><div class="shh"><h2>{html.escape(sname)}</h2>'
                       f'<span class="shn">{plural(len(cs), ("книга", "книги", "книг"))}</span></div>'
                       f'<p class="shd">{html.escape(sdesc)}</p>'
                       '<div class="shelf row">' + "\n".join(tile(c) for c in cs) + '</div></section>')
    known = {s[0] for s in SHELVES}
    for c in cols:  # сборники без полки: широкая карточка «Вне циклов» внизу
        if c["shelf"] in known:
            continue
        name = c["title"].partition(". ")[0]
        shelves.append(f'<a class="wcard" href="{c["slug"]}/"><span class="wi">{cover_html(c, name)}</span>'
                       f'<span class="wb"><span class="kick">Вне циклов</span><span class="wt">{html.escape(name)}</span>'
                       + (f'<span class="wd">{html.escape(blurb(c["about"]))}</span>' if c["about"] else "")
                       + '</span><span class="wn">' + html.escape(label(c))
                       + (' · новое' if c["slug"] in fresh_slugs else "") + ' →</span></a>')

    parts = ['<section class="hero"><h1>Проза</h1>'
             '<p>Сборники повестей и рассказов. Читать можно бесплатно и без регистрации, '
             'с телефона или с большого экрана, при свете и в темноте.</p></section>',
             '<section class="fresh" aria-labelledby="fresh-h"><h2 class="kick" id="fresh-h">Новое на сайте</h2>'
             '<div class="fr">' + "\n".join(fcards) + '</div></section>',
             '<div class="bar"><nav class="chips" id="chips" aria-label="Полки">' + "".join(chips) + '</nav>'
             '<p class="wnote" id="wnote" hidden>Все сборники в том порядке, в каком писались</p>'
             '<div class="seg" role="group" aria-label="Как показывать сборники">'
             '<button type="button" data-view="shelves" aria-pressed="true">По полкам</button>'
             '<button type="button" data-view="written" aria-pressed="false">По времени написания</button></div></div>',
             '<div id="v-shelves">' + "\n".join(shelves) + '</div>',
             '<div id="v-written" hidden><div class="shelf">' + "\n".join(tile(c, False) for c in cols) + '</div></div>']
    open(f"{OUT}/index.html", "w", encoding="utf-8").write(page(
        SITE, "\n".join(parts), "", wide=True, url="index.html",
        desc="Повести и рассказы Павла Юрича: детективы о старом Тифлисе, Риме и Китае, "
             "истории об инспекторе Морсе, хоррор, проза о Грузии. Читать бесплатно, без регистрации.",
        ld={"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "inLanguage": "ru",
            "author": PERSON}))

    # сборники и рассказы
    feed = []
    for c in cols:
        os.makedirs(f"{OUT}/{c['slug']}", exist_ok=True)
        about = render(c["about"]) if c["about"] else ""
        body = f'<h1>{html.escape(c["title"])}</h1>{theme(c, "Включите перед чтением — как заставку сериала")}{about}{toc(c["works"], "", "toc")}'
        crumbs = '<p class="crumbs"><a href="../">Все сборники</a></p>'
        cdesc = c["desc"] or ((snippet(c["about"], 200) or plain(blurb(c["about"]))) if c["about"] else "")
        cdesc = cdesc or f"Сборник прозы Павла Юрича «{c['title']}». Читать бесплатно."
        open(f"{OUT}/{c['slug']}/index.html", "w", encoding="utf-8").write(
            page(f'{c["title"]} — {AUTHOR}', body, "../", crumbs, url=f"{c['slug']}/index.html",
                 desc=cdesc, image=f"{c['slug']}/cover.jpg" if c["cover"] else "",
                 ld={"@context": "https://schema.org", "@type": "Book", "name": c["title"],
                     "inLanguage": "ru", "author": PERSON, "isAccessibleForFree": True}))
        # старые адреса (сборник раньше был отдельным): страницы-переадресации
        alias = ""
        for w in c["works"]:
            if "/" in w["alias"]:  # «alias: сборник/рассказ» — переехал один рассказ, а не весь сборник
                old_dir, old_name = w["alias"].split("/", 1)
                to = f'../{c["slug"]}/{w["slug"]}.html'
                os.makedirs(f"{OUT}/{old_dir}", exist_ok=True)
                open(f"{OUT}/{old_dir}/{old_name}.html", "w", encoding="utf-8").write(
                    f'<!doctype html><html lang="ru"><meta charset="utf-8">'
                    f'<meta http-equiv="refresh" content="0; url={to}">'
                    f'<link rel="canonical" href="{to}"><title>{html.escape(w["title"])}</title>'
                    f'<p><a href="{to}">Страница переехала</a></p></html>')
                continue
            alias = w["alias"] or alias
            if alias:
                os.makedirs(f"{OUT}/{alias}", exist_ok=True)
                for name, to in ((w["slug"], f'../{c["slug"]}/{w["slug"]}.html'),
                                 ("index", f'../{c["slug"]}/')):
                    open(f"{OUT}/{alias}/{name}.html", "w", encoding="utf-8").write(
                        f'<!doctype html><html lang="ru"><meta charset="utf-8">'
                        f'<meta http-equiv="refresh" content="0; url={to}">'
                        f'<link rel="canonical" href="{to}"><title>{html.escape(c["title"])}</title>'
                        f'<p><a href="{to}">Страница переехала</a></p></html>')
        reads = [w for w in c["works"] if not w["url"]]
        for i, w in enumerate(reads):
            prev = reads[i - 1] if i else None
            nxt = reads[i + 1] if i + 1 < len(reads) else None
            nav = '<nav class="pn">'
            nav += (f'<a class="prev" href="{prev["slug"]}.html"><small>Назад</small>{html.escape(prev["title"])}</a>'
                    if prev else '<span></span>')
            nav += (f'<a class="next" href="{nxt["slug"]}.html"><small>Дальше</small>{html.escape(nxt["title"])}</a>'
                    if nxt else f'<a class="next" href="./"><small>Конец сборника</small>К оглавлению</a>')
            nav += "</nav>"
            crumbs = (f'<p class="crumbs"><a href="../">Все сборники</a> · '
                      f'<a href="./">{html.escape(c["title"])}</a></p>')
            body = (f'<article><h1>{html.escape(w["title"])}</h1>'
                    f'<p class="meta">{AUTHOR} · около {w["min"]} мин чтения</p>'
                    + theme(c, "Заставка")
                    + (f'<figure><img src="{w["pic"]}" alt="{html.escape(w["caption"] or "Иллюстрация к рассказу «" + w["title"] + "»")}" loading="lazy">'
                       + (f'<figcaption>{html.escape(w["caption"])}</figcaption>' if w["caption"] else "") + "</figure>"
                       if w["pic"] else "")
                    + f'{render(w["body"])}{signature(w["written"], w["revised"])}</article>{nav}')
            short = c["title"].partition(". ")[0]
            wtitle = (f'{w["title"]} — {AUTHOR}' if w["title"] == short
                      else f'{w["title"]} — {short} — {AUTHOR}')
            key = f'{c["slug"]}/{w["slug"]}'
            published.setdefault(key, today)
            desc = snippet(w["body"]) or f'{w["title"]}: из сборника «{c["title"]}»'
            feed.append({"title": f'{w["title"]} — {short}', "url": BASE + key + ".html",
                         "date": published[key], "desc": desc, "order": len(feed)})
            open(f"{OUT}/{c['slug']}/{w['slug']}.html", "w", encoding="utf-8").write(
                page(wtitle, body, "../", crumbs, url=key + ".html", desc=desc, kind="article",
                     image=(f'{c["slug"]}/{w["pic"]}' if w["pic"] else
                            f'{c["slug"]}/cover.jpg' if c["cover"] else ""),
                     date=published[key],
                     ld={"@context": "https://schema.org", "@type": "CreativeWork", "name": w["title"],
                         "inLanguage": "ru", "author": PERSON, "isAccessibleForFree": True,
                         "isPartOf": {"@type": "Book", "name": c["title"], "url": f'{BASE}{c["slug"]}/'}}))

    # отдельные страницы
    for f in sorted(os.listdir("pages")):
        meta, body = read(os.path.join("pages", f))
        open(f"{OUT}/{f[:-3]}.html", "w", encoding="utf-8").write(
            page(f'{meta.get("title", "")} — {AUTHOR}',
                 f'<article class="plain"><h1>{html.escape(meta.get("title", ""))}</h1>{body}</article>', "",
                 url=f"{f[:-3]}.html", desc=meta.get("description", "") or plain(re.sub(r"<[^>]+>", " ", body))[:180]))

    # даты появления на сайте: новые тексты получают сегодняшнюю
    json.dump(dict(sorted(published.items())), open(PUBLISHED, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    write_sitemap()
    write_feed(feed)

    n = sum(len(c["works"]) for c in cols)
    print(f"Готово: сборников {len(cols)}, произведений {n} → {OUT}/")


if __name__ == "__main__":
    main()
