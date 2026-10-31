#!/usr/bin/env python3
"""Готовит обложки сборников для плиток на главной: content/<сборник>/cover.jpg.

Источник — иллюстрация из строки `cover: images/файл.jpg` в шапке _collection.md,
а если её нет — иллюстрация первого рассказа сборника. Картинка обрезается в квадрат
и ужимается, чтобы главная грузилась быстро. Готовая cover.jpg не перезаписывается
(чтобы пересоздать, удалите её или запустите с ключом --force).
Нужен Pillow:  pip install pillow
"""
import os, re, sys
from PIL import Image

SRC, W, H = "content", 600, 600
force = "--force" in sys.argv

for d in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, d)
    out = os.path.join(p, "cover.jpg")
    if not os.path.isdir(p) or (os.path.exists(out) and not force):
        continue
    meta = open(os.path.join(p, "_collection.md"), encoding="utf-8").read()
    m = re.search(r"^cover:\s*(\S+)", meta, re.M)
    src = os.path.join(p, m.group(1)) if m else None
    if not src:
        for f in sorted(os.listdir(p)):
            if f.endswith(".md") and not f.startswith("_"):
                s = re.sub(r"^\d+-", "", f[:-3])
                src = next((os.path.join(p, "images", s + e) for e in (".jpg", ".png", ".webp")
                            if os.path.exists(os.path.join(p, "images", s + e))), None)
                if src:
                    break
    if not src or not os.path.exists(src):
        print(f"{d}: иллюстраций нет — на главной будет текстовая обложка")
        continue
    im = Image.open(src).convert("RGB")
    k = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 3  # чуть выше центра: лица обычно в верхней части
    im.crop((x, y, x + W, y + H)).save(out, quality=78, optimize=True, progressive=True)
    print(f"{d}: {os.path.relpath(src, p)} → cover.jpg ({os.path.getsize(out) // 1024} КБ)")
