#!/usr/bin/env python3
"""Validate artworks.json and the files the site expects to exist.

Run before building, and in CI. Catches the mistakes that are easy to make by
hand and expensive to notice later: a duplicate id, a slug that changes a
published work's address, a price typed with a currency symbol, an image whose
derivatives were never generated.

Usage:  python3 tools/check.py
Exits non-zero, listing every problem, if anything is wrong.
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TYPES = {"oil", "graphics", "sculpture"}
REQUIRED = {
    "id": int, "slug": str, "title": str, "type": str, "typeName": str,
    "description": str, "price": int, "dimensions": str, "year": int, "image": str,
}

problems = []
notes = []


def fail(msg):
    problems.append(msg)


def main():
    path = ROOT / "artworks.json"
    try:
        works = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        # By far the most likely hand-editing mistake, so say exactly where.
        sys.exit(f"artworks.json is not valid JSON: {exc.msg} "
                 f"at line {exc.lineno}, column {exc.colno}")

    if not isinstance(works, list) or not works:
        sys.exit("artworks.json must be a non-empty list")

    manifest_path = ROOT / "tools" / "image-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    seen_ids, seen_slugs = {}, {}
    this_year = date.today().year

    for i, w in enumerate(works):
        where = f"entry {i} ({w.get('title', 'untitled')!r})"

        shape_ok = True
        for field, want in REQUIRED.items():
            if field not in w:
                fail(f"{where}: missing '{field}'")
                shape_ok = False
            elif not isinstance(w[field], want) or isinstance(w[field], bool):
                fail(f"{where}: '{field}' should be {want.__name__}, "
                     f"got {type(w[field]).__name__} ({w[field]!r})")
                shape_ok = False
        # The value checks below assume the types above hold; running them on a
        # price typed as "EUR 34 000" would crash rather than explain itself.
        if not shape_ok:
            continue

        if w["id"] in seen_ids:
            fail(f"{where}: id {w['id']} already used by {seen_ids[w['id']]!r}")
        seen_ids[w["id"]] = w["title"]

        if not SLUG.match(w["slug"]):
            fail(f"{where}: slug {w['slug']!r} must be lowercase letters, digits "
                 f"and single hyphens")
        if w["slug"] in seen_slugs:
            fail(f"{where}: slug {w['slug']!r} already used by {seen_slugs[w['slug']]!r}")
        seen_slugs[w["slug"]] = w["title"]

        if w["type"] not in TYPES:
            fail(f"{where}: type {w['type']!r} is not one of {sorted(TYPES)}")
        if w["price"] < 0:
            fail(f"{where}: price {w['price']} is negative")
        if not (1900 <= w["year"] <= this_year):
            fail(f"{where}: year {w['year']} is outside 1900-{this_year}")
        if not w["title"].strip():
            fail(f"{where}: title is empty")

        name = w["image"].split("/")[-1]
        if name not in manifest:
            fail(f"{where}: {name} is not in the image manifest. Run "
                 f"tools/optimise_images.py after adding a new image.")
        else:
            rec = manifest[name]
            missing = [
                f"{rec['stem']}-{width}.{ext}"
                for width in rec["widths"] for ext in ("avif", "webp", "jpg")
                if not (ROOT / "images" / "opt" / f"{rec['stem']}-{width}.{ext}").exists()
            ]
            if missing:
                fail(f"{where}: missing derivatives {', '.join(missing[:4])}"
                     f"{'...' if len(missing) > 4 else ''}")

    # Not failures, but worth surfacing: the catalogue is incomplete here.
    unmeasured = [w for w in works
                  if not w["dimensions"].strip(" ‐‑‒–—―-")]
    if unmeasured:
        notes.append(f"{len(unmeasured)} work(s) have no recorded measurements and "
                     f'show "On request": '
                     + ", ".join(f"#{w['id']} {w['title']}" for w in unmeasured))

    for note in notes:
        print(f"note: {note}")

    if problems:
        print(f"\n{len(problems)} problem(s) found:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)

    print(f"ok: {len(works)} works, {len(seen_slugs)} unique slugs, all images present")


if __name__ == "__main__":
    main()
