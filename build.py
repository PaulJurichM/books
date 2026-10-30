#!/usr/bin/env python3
"""Собирает сайт из папки content/ в папку docs/ (её публикует GitHub Pages).

Новый рассказ: положить .md в папку сборника (номер в имени файла задаёт порядок)
и запустить  python3 build.py
"""
import html, os, re, shutil

SRC, OUT = "content", "docs"
AUTHOR = "Павел Юрич"
SITE = "Павел Юрич. Проза"
PLACE = "Тбилиси"
MONTHS = ("январь февраль март апрель май июнь июль август "
          "сентябрь октябрь ноябрь декабрь").split()


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


def minutes(body):
    return max(1, round(len(body.split()) / 180))


def page(title, content, root, crumbs=""):
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
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
  <a class="brand" href="{root}index.html">{AUTHOR}</a>
  <nav>
    <a href="/creative/">← Творчество</a>
    <a href="{root}index.html">Сборники</a>
    <a href="{root}ekranizaciya.html">Экранизация</a>
    <button class="ctl" id="fs-down" type="button" aria-label="Уменьшить шрифт">A−</button>
    <button class="ctl" id="fs-up" type="button" aria-label="Увеличить шрифт">A+</button>
    <button class="ctl" id="theme" type="button" aria-label="Переключить тему">Тёмная</button>
  </nav>
</header>
<main>
{crumbs}
{content}
</main>
<footer>
  <p>© {AUTHOR}, 2026. Читать можно свободно. <a href="{root}ekranizaciya.html">Экранизация и права</a> · <a href="/">malari.me</a></p>
</footer>
<script src="{root}assets/site.js"></script>
<script data-goatcounter="https://malari.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
"""

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
        img = os.path.join(p, "images")
        if os.path.isdir(img):
            shutil.copytree(img, f"{OUT}/{slug}/images")
        cols.append({"slug": slug, "title": cmeta.get("title", d), "about": cbody, "works": works,
                     "theme": theme})

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

    # главная
    parts = ['<section class="hero"><h1>Проза</h1>'
             '<p>Сборники повестей и рассказов. Читать можно бесплатно и без регистрации, '
             'с телефона или с большого экрана, при свете и в темноте.</p></section>']
    for c in cols:
        parts.append(
            f'<details class="col"><summary><span class="ct">{html.escape(c["title"])}</span>'
            f'<span class="cn">{len(c["works"])}</span></summary>'
            + toc(c["works"], c["slug"] + "/") +
            f'<p class="more"><a href="{c["slug"]}/index.html">Открыть сборник отдельной страницей</a></p></details>')
    open(f"{OUT}/index.html", "w", encoding="utf-8").write(page(SITE, "\n".join(parts), ""))

    # сборники и рассказы
    for c in cols:
        os.makedirs(f"{OUT}/{c['slug']}", exist_ok=True)
        about = render(c["about"]) if c["about"] else ""
        body = f'<h1>{html.escape(c["title"])}</h1>{theme(c, "Включите перед чтением — как заставку сериала")}{about}{toc(c["works"], "", "toc")}'
        crumbs = '<p class="crumbs"><a href="../index.html">Все сборники</a></p>'
        open(f"{OUT}/{c['slug']}/index.html", "w", encoding="utf-8").write(
            page(f'{c["title"]} — {AUTHOR}', body, "../", crumbs))
        # старые адреса (сборник раньше был отдельным): страницы-переадресации
        alias = ""
        for w in c["works"]:
            alias = w["alias"] or alias
            if alias:
                os.makedirs(f"{OUT}/{alias}", exist_ok=True)
                for name, to in ((w["slug"], f'../{c["slug"]}/{w["slug"]}.html'),
                                 ("index", f'../{c["slug"]}/index.html')):
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
                    if nxt else f'<a class="next" href="index.html"><small>Конец сборника</small>К оглавлению</a>')
            nav += "</nav>"
            crumbs = (f'<p class="crumbs"><a href="../index.html">Все сборники</a> · '
                      f'<a href="index.html">{html.escape(c["title"])}</a></p>')
            body = (f'<article><h1>{html.escape(w["title"])}</h1>'
                    f'<p class="meta">{AUTHOR} · около {w["min"]} мин чтения</p>'
                    + theme(c, "Заставка")
                    + (f'<figure><img src="{w["pic"]}" alt="{html.escape(w["caption"] or "Иллюстрация к рассказу «" + w["title"] + "»")}" loading="lazy">'
                       + (f'<figcaption>{html.escape(w["caption"])}</figcaption>' if w["caption"] else "") + "</figure>"
                       if w["pic"] else "")
                    + f'{render(w["body"])}{signature(w["written"], w["revised"])}</article>{nav}')
            open(f"{OUT}/{c['slug']}/{w['slug']}.html", "w", encoding="utf-8").write(
                page(f'{w["title"]} — {AUTHOR}', body, "../", crumbs))

    # отдельные страницы
    for f in sorted(os.listdir("pages")):
        meta, body = read(os.path.join("pages", f))
        open(f"{OUT}/{f[:-3]}.html", "w", encoding="utf-8").write(
            page(f'{meta.get("title", "")} — {AUTHOR}',
                 f'<article class="plain"><h1>{html.escape(meta.get("title", ""))}</h1>{body}</article>', ""))

    n = sum(len(c["works"]) for c in cols)
    print(f"Готово: сборников {len(cols)}, произведений {n} → {OUT}/")


if __name__ == "__main__":
    main()
