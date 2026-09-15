#!/usr/bin/env python3
"""Generate responsive, web-sized derivatives from the print masters in images/.

The masters are 2000-5000px wide and up to 18 MB each; no browser ever displays
them at that size. For each image referenced by the site this writes AVIF, WebP
and JPEG copies at 400/800/1600px into images/opt/, plus a tiny blurred LQIP
that the page inlines as a data URI while the real file loads.

Usage:  python3 tools/optimise_images.py [--force]
Requires Pillow with AVIF and WebP support.
"""
import base64
import io
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageFilter, features

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "images"
OUT = SRC / "opt"

WIDTHS = (400, 800, 1600)
QUALITY = {"avif": 62, "webp": 82, "jpeg": 82}
LQIP_WIDTH = 20

# Images used by the site outside the artwork catalogue.
EXTRA = ["about-photo.jpg"]


def check_support():
    missing = [n for n in ("webp", "avif") if not features.check(n)]
    if missing:
        sys.exit(f"Pillow is missing codec support for: {', '.join(missing)}")


def load(path):
    im = Image.open(path)
    im.load()
    if im.mode in ("RGBA", "LA", "P"):
        # The masters carry an alpha channel the artwork never uses; flatten it
        # onto white so JPEG works and AVIF/WebP stay small.
        bg = Image.new("RGB", im.size, (255, 255, 255))
        rgba = im.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[-1])
        im = bg
    return im.convert("RGB")


def lqip(im):
    """A 20px-wide blurred preview, small enough to inline as a data URI."""
    w = LQIP_WIDTH
    h = max(1, round(im.height * w / im.width))
    tiny = im.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
    buf = io.BytesIO()
    tiny.save(buf, "JPEG", quality=40, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def derivatives(im, stem, force):
    """Write every width/format pair. Returns list of widths actually available."""
    made = []
    for w in WIDTHS:
        if w > im.width:
            # Never upscale: a master narrower than the target keeps its own size.
            if made:
                continue
            target = im.copy()
        else:
            h = round(im.height * w / im.width)
            target = im.resize((w, h), Image.LANCZOS)
        for fmt, ext in (("AVIF", "avif"), ("WEBP", "webp"), ("JPEG", "jpg")):
            dest = OUT / f"{stem}-{w}.{ext}"
            if dest.exists() and not force:
                continue
            kw = {"quality": QUALITY[ext if ext != "jpg" else "jpeg"]}
            if fmt == "WEBP":
                kw["method"] = 6
            if fmt == "JPEG":
                kw.update(optimize=True, progressive=True)
            target.save(dest, fmt, **kw)
        made.append(w)
    return made


def main():
    force = "--force" in sys.argv
    check_support()
    OUT.mkdir(parents=True, exist_ok=True)

    artworks = json.loads((ROOT / "artworks.json").read_text())
    names = [a["image"].split("/")[-1] for a in artworks] + EXTRA

    # The print masters are deliberately not kept in the working tree (they are
    # 300+ MB and live in git history). Entries whose derivatives already exist
    # are carried over unchanged, so this only ever has work to do for images
    # that are genuinely new.
    manifest_path = ROOT / "tools" / "image-manifest.json"
    previous = {}
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())

    manifest = {}
    before = after = 0
    missing = []
    for name in names:
        path = SRC / name
        if not path.exists():
            if name in previous:
                manifest[name] = previous[name]
            else:
                missing.append(name)
            continue
        stem = path.stem
        im = load(path)
        widths = derivatives(im, stem, force)
        manifest[name] = {
            "stem": stem,
            "width": im.width,
            "height": im.height,
            "widths": widths,
            "lqip": lqip(im),
        }
        orig = path.stat().st_size
        opt = (OUT / f"{stem}-{max(widths)}.avif").stat().st_size
        before += orig
        after += opt
        print(f"  {name:44s} {orig/1e6:6.1f}MB -> {opt/1024:6.0f}KB")

    for name in missing:
        print(f"  ! no master and no existing derivatives: {name}", file=sys.stderr)

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    carried = len(manifest) - sum(1 for n in names if (SRC / n).exists())
    print(f"\n{len(manifest)} images in manifest ({carried} carried over).")
    if before:
        print(f"Newly processed: {before/1e6:.0f}MB -> {after/1e6:.1f}MB")
    if missing:
        sys.exit(f"{len(missing)} image(s) have neither a master nor derivatives.")


if __name__ == "__main__":
    main()
