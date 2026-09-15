# boakeadamsson.com

The website of Bo Åke Adamsson, Swedish painter, sculptor and graphic artist.
A static site, served by GitHub Pages from the repository root.

## How it fits together

`artworks.json` is the single source of truth for the catalogue. Two scripts read
it and generate everything else, so no generated file should ever be edited by hand:

| Command | What it does |
|---|---|
| `python3 tools/optimise_images.py` | Turns print masters in `images/` into web-sized AVIF/WebP/JPEG derivatives in `images/opt/`, and records dimensions and blur previews in `tools/image-manifest.json`. |
| `python3 tools/build.py` | Writes every HTML page, `sitemap.xml` and `robots.txt` from `artworks.json` and the image manifest. |

Hand-written sources are `artworks.json`, `assets/css/site.css`, `assets/js/site.js`,
and the page copy in `tools/partials/`.

Generated, and safe to delete and rebuild: `index.html`, `404.html`, `sitemap.xml`,
`robots.txt`, and the `about/ oil/ graphics/ sculpture/ work/ privacy/ terms/` directories.

## Everyday tasks

**Change a price, dimension or year.** Edit `artworks.json`. Each work is one block,
and only the values to the right of the colons need touching:

```json
{
  "id": 4,
  "slug": "stora-gatan",
  "title": "Stora Gatan",
  "type": "oil",
  "typeName": "Oil Painting",
  "description": "",
  "price": 56000,
  "dimensions": "120 x 140 cm",
  "year": 2022,
  "image": "images/stora-gatan.jpg"
}
```

`price` is a plain number with no currency symbol, spaces or thousands separators.
`dimensions` is free text, and a work with none shows "On request" on its page.
Leave `slug` alone once a work is published: it is that work's web address, and
changing it breaks any link anyone has saved. Then:

```sh
python3 -c "import json; json.load(open('artworks.json'))"   # catches a stray comma
python3 tools/build.py
git add -A && git commit -m "Update artwork details" && git push
```

**Add a new artwork.** Put the master image in `images/`, copy an existing block in
`artworks.json` and edit it, giving it an `id` no other work uses and a `slug` of
lowercase letters, numbers and hyphens only. Then:

```sh
python3 tools/optimise_images.py     # needs Pillow: pip install Pillow
python3 tools/build.py
```

**Edit the about page, privacy policy or terms.** Those live in `tools/partials/`.
Edit the partial, then run `python3 tools/build.py`.

**Preview locally.**

```sh
python3 -m http.server 8000     # then open http://localhost:8000
```

## About the images

The original print masters, roughly 300 MB and 2,000 to 5,000px on a side, are **not** kept
in the working tree. They remain in git history and can be recovered at any time:

```sh
git log --all --oneline -- images/existence.jpg
git checkout <commit> -- images/existence.jpg
```

Treat that as a backstop, not a backup: keep your own copies of the masters.

`tools/optimise_images.py` carries existing manifest entries over when a master is
absent, so it only ever has work to do for images that are genuinely new.

## Structure

Each page is generated as real HTML with its content already in the markup, so the
site works with JavaScript disabled and search engines index each artwork
individually. `assets/js/site.js` then layers instant client-side navigation over
the same URLs. Old `#work/13`-style links still resolve to their new addresses.

## Before going live

Seller identity and retention live in the `SELLER` and `RETENTION` constants at the
top of `tools/build.py`, and feed both legal pages. Edit them there, not in the
generated HTML.

One placeholder is still outstanding in `tools/partials/terms.html`: the **VAT
registration number**, or confirmation that the business is not VAT registered.
It renders as a visibly marked chip so it cannot go live unnoticed. To find any
remaining placeholder:

```sh
grep -rn 'class="todo"' tools/partials/
```

Both legal pages are drafted against the GDPR and Swedish consumer law but have not
been reviewed by a lawyer.
