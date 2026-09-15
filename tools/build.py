#!/usr/bin/env python3
"""Generate the static site from artworks.json and the image manifest.

Every route is written out as a real HTML file with its content already in the
markup, so the site works with JavaScript disabled and search engines can index
each artwork individually. assets/js/site.js then layers instant client-side
navigation on top, using the same URLs.

Usage:  python3 tools/build.py
"""
import html
import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PARTIALS = ROOT / "tools" / "partials"

# Must match the CNAME file: GitHub Pages serves the apex and redirects www to
# it, so canonicals, og:url and the sitemap all have to name the apex. Pointing
# them at a host that only redirects muddles the signal Google is given.
SITE = "https://boakeadamsson.com"
EMAIL = "ba.adamsson@gmail.com"
PRIVACY_EMAIL = EMAIL
IMG = "/images/opt/"

# Seller identity, in one place. Swedish e-commerce law (2002:562) requires a
# trader to state these, and they appear on both legal pages.
SELLER = {
    "name": "Bo Åke Adamsson",
    "form": "enskild näringsverksamhet (Swedish sole trader)",
    # An enskild firma's organisationsnummer is the proprietor's personnummer.
    # The last four digits are the part that enables identity fraud, so they are
    # withheld on the public site and given in full on request and on invoices.
    "orgnr": "410622-XXXX",
    "street": "Tärna Prästgård 112",
    "postal": "733 93 Sala",
    "seat": "Sala, Västmanlands län",
}

SELLER_ADDRESS = (
    f'{SELLER["name"]}<br>\n  {SELLER["form"]}<br>\n  {SELLER["street"]}<br>\n  '
    f'{SELLER["postal"]}, Sweden<br>\n  Registered office: {SELLER["seat"]}<br>\n  '
    f'Organisationsnummer: {SELLER["orgnr"]}'
)

# How long an inquiry that never becomes a sale is kept.
RETENTION = "24 months"

# Shown wherever the masked organisationsnummer appears, so the omission is
# explained rather than looking like an oversight.
# TODO: once the VAT registration number is to hand, state it here in full —
# a VAT-registered trader is expected to publish it (e-handelslagen 2002:562 § 8).
IDENTITY_NOTE = (
    "The studio trades as an <strong>enskild näringsverksamhet</strong>, a Swedish "
    "sole trader. For that business form the organisationsnummer is the proprietor's "
    "own personal identity number, so the last four digits are withheld here to guard "
    "against identity fraud. The full number, and the studio's Swedish VAT "
    "registration number, are stated on every quote and invoice and are given in "
    "full on request."
)

FILTERS = {
    "all": ("/", "Selected Works", None),
    "oil": ("/oil/", "Oil Paintings", "oil"),
    "graphics": ("/graphics/", "Graphics", "graphics"),
    "sculpture": ("/sculpture/", "Bronze Sculptures", "sculpture"),
}

SIZES_GALLERY = "(max-width:700px) 92vw, (max-width:1100px) 46vw, 30vw"
SIZES_WORK = "(max-width:900px) 92vw, 55vw"
SIZES_HERO = "(max-width:900px) 100vw, 57vw"
SIZES_SPLIT = "(max-width:900px) 92vw, 40vw"

e = html.escape


def price_display(price, type_):
    if type_ == "sculpture" or price > 10000:
        return "Price on Request"
    return "€{:,}".format(price)


def picture(rec, alt, sizes, eager=False, cls=""):
    """The <picture> block, matching what site.js generates at runtime."""
    stem, widths = rec["stem"], rec["widths"]
    fallback = widths[-1]

    def ss(ext):
        return ", ".join(f"{IMG}{stem}-{w}.{ext} {w}w" for w in widths)

    load = ('fetchpriority="high" decoding="async"' if eager
            else 'loading="lazy" decoding="async"')
    return (
        f'<picture{cls}>'
        f'<source type="image/avif" srcset="{ss("avif")}" sizes="{sizes}">'
        f'<source type="image/webp" srcset="{ss("webp")}" sizes="{sizes}">'
        f'<img src="{IMG}{stem}-{fallback}.jpg" srcset="{ss("jpg")}" sizes="{sizes}"'
        f' width="{rec["width"]}" height="{rec["height"]}" alt="{e(alt)}" {load}>'
        f"</picture>"
    )


def ph_style(rec):
    """Inline the blurred preview so it paints before any network request."""
    return f' style="background-image:url({rec["lqip"]})"'


# --------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------

NAV = [
    ("/", "gallery", "Gallery"),
    ("/oil/", "oil", "Oil Paintings"),
    ("/graphics/", "graphics", "Graphics"),
    ("/sculpture/", "sculpture", "Sculptures"),
    ("/about/", "about", "About"),
]


def header(active):
    ACTIVE = ' class="active" aria-current="page"'
    items = "".join(
        '<li><a href="%s" data-route="%s"%s>%s</a></li>'
        % (href, route, ACTIVE if route == active else "", label)
        for href, route, label in NAV
    )
    return f"""<a class="skip-link" href="#main">Skip to content</a>
<header class="site">
    <div class="header-inner">
        <a href="/" class="sig-link" aria-label="Bo Åke Adamsson — home">
            <img src="/images/signature.png" alt="Bo Åke Adamsson" width="420" height="120">
        </a>
        <nav class="main" aria-label="Main navigation"><ul>{items}</ul></nav>
    </div>
</header>"""


SOCIAL = [
    ("https://instagram.com/boakeadamsson", "Instagram",
     '<rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>'
     '<path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>'
     '<line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>'),
    ("https://facebook.com/boakeadamsson", "Facebook",
     '<path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"></path>'),
    ("https://www.youtube.com/@BoAkeAdamsson.", "YouTube",
     '<path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z"></path>'
     '<polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02"></polygon>'),
    ("https://tiktok.com/@boakeadamsson", "TikTok",
     '<path d="M9 12a4 4 0 1 0 4 4V4a5 5 0 0 0 5 5"></path>'),
]


def footer():
    links = "".join(
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" title="{name}" aria-label="{name}">'
        f'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" aria-hidden="true">{svg}</svg></a>'
        for url, name, svg in SOCIAL
    )
    return f"""<footer>
    <img src="/images/signature.png" alt="Bo Åke Adamsson" class="fsig" width="420" height="120" loading="lazy">
    <div class="social-links">{links}</div>
    <nav class="foot-links" aria-label="Legal">
        <a href="/about/">About</a>
        <a href="mailto:{EMAIL}">Contact</a>
        <a href="/privacy/">Privacy</a>
        <a href="/terms/">Terms of Sale</a>
    </nav>
    <p>&copy; {date.today().year} Bo Åke Adamsson. All rights reserved.</p>
    <p>Contact: <a class="mail" href="mailto:{EMAIL}">{EMAIL}</a></p>
</footer>"""


def layout(*, title, description, path, body, jsonld=None, og_image=None,
           preload=None, active=None, page_state=None, artworks_data=None,
           robots=None):
    ld = ""
    for block in (jsonld or []):
        ld += ('<script type="application/ld+json">'
               + json.dumps(block, ensure_ascii=False) + "</script>\n    ")

    og = og_image or f"{IMG}skal-1600.jpg"
    pre = ""
    if preload:
        stem, widths, sizes = preload
        av = ", ".join(f"{IMG}{stem}-{w}.avif {w}w" for w in widths)
        pre = (f'<link rel="preload" as="image" type="image/avif" '
               f'href="{IMG}{stem}-{widths[-1]}.avif" imagesrcset="{av}" '
               f'imagesizes="{sizes}" fetchpriority="high">\n    ')

    state = ""
    if page_state:
        state = f"<script>window.PAGE={json.dumps(page_state)};</script>\n"
    data = ""
    if artworks_data is not None:
        data = ("<script>window.ARTWORKS="
                + json.dumps(artworks_data, ensure_ascii=False, separators=(",", ":"))
                + ";</script>\n")

    script = ""
    if artworks_data is not None:
        script = f'{state}{data}<script src="/assets/js/site.js" defer></script>\n'

    return f"""<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(title)}</title>
    <meta name="description" content="{e(description)}">
    <meta name="author" content="Bo Åke Adamsson">
    {'<meta name="robots" content="' + robots + '">' if robots else '<meta name="robots" content="index, follow, max-image-preview:large">'}
    <link rel="canonical" href="{SITE}{path}">

    <meta property="og:type" content="{'article' if path.startswith('/work/') else 'website'}">
    <meta property="og:site_name" content="Bo Åke Adamsson">
    <meta property="og:title" content="{e(title)}">
    <meta property="og:description" content="{e(description)}">
    <meta property="og:url" content="{SITE}{path}">
    <meta property="og:image" content="{SITE}{og}">
    <meta property="og:locale" content="en_GB">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{e(title)}">
    <meta name="twitter:description" content="{e(description)}">
    <meta name="twitter:image" content="{SITE}{og}">

    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23E6E8E2'/%3E%3Ccircle cx='16' cy='16' r='9' fill='%238C3A24'/%3E%3C/svg%3E">
    <meta name="theme-color" content="#E6E8E2" media="(prefers-color-scheme: light)">
    <meta name="theme-color" content="#14171A" media="(prefers-color-scheme: dark)">

    <link rel="preload" as="font" type="font/woff2" href="/assets/fonts/instrument-serif-400-latin.woff2" crossorigin>
    <link rel="preload" as="font" type="font/woff2" href="/assets/fonts/archivo-400-latin.woff2" crossorigin>
    {pre}<link rel="stylesheet" href="/assets/css/fonts.css">
    <link rel="stylesheet" href="/assets/css/site.css">

    {ld}</head>
<body>
{header(active)}
<div id="main">
{body}
</div>
{footer()}
{script}</body>
</html>
"""


# --------------------------------------------------------------------------
# page bodies
# --------------------------------------------------------------------------

def gallery_card(art, rec):
    p = price_display(art["price"], art["type"])
    price_html = ('<span class="price request">On Request</span>'
                  if p == "Price on Request" else f'<span class="price">{p}</span>')
    dims = " · ".join(x for x in (art["dimensions"], str(art["year"]))
                           if x and x != "—")
    alt = f'{art["title"]} — {art["typeName"]} by Bo Åke Adamsson'
    return f"""<a class="piece reveal" href="/work/{art['slug']}/" data-slug="{art['slug']}" aria-label="View {e(art['title'])} in detail">
    <figure class="ph"{ph_style(rec)}>{picture(rec, alt, SIZES_GALLERY)}<span class="tag">{e(art['typeName'])}</span></figure>
    <figcaption>
        <div class="row1"><h3>{e(art['title'])}</h3>{price_html}</div>
        <div class="dims">{e(dims)}</div>
    </figcaption>
</a>"""


def filter_bar(active, counts):
    out = []
    for key, (href, label, _) in FILTERS.items():
        on = key == active
        out.append(
            '<a href="%s" data-filter="%s" class="%s" role="button"%s>%s'
            '<span class="count">%d</span></a>'
            % (href, key, "active" if on else "",
               ' aria-current="page"' if on else "",
               "All Works" if key == "all" else label, counts[key])
        )
    return ('<div class="filter-bar" role="group" aria-label="Filter artworks">'
            + "".join(out) + "</div>")


def home_body(artworks, manifest, active, hero):
    counts = {"all": len(artworks)}
    for k in ("oil", "graphics", "sculpture"):
        counts[k] = sum(1 for a in artworks if a["type"] == k)

    shown = artworks if active == "all" else [a for a in artworks if a["type"] == active]
    cards = "\n".join(gallery_card(a, manifest[a["image"].split("/")[-1]]) for a in shown)
    if not cards:
        cards = '<p class="empty">No works in this category at the moment.</p>'

    hero_rec = manifest[hero["image"].split("/")[-1]]
    hero_alt = f'{hero["title"]} — oil painting by Bo Åke Adamsson'
    about_rec = manifest["about-photo.jpg"]
    title = FILTERS[active][1]

    hero_html = f"""<section class="hero">
    <div class="hero-text">
        <div class="hero-eyebrow">Swedish Painter · Sculptor · Graphic Artist</div>
        <h1>Six decades of <em>Nordic light</em>, painted without apology.</h1>
        <p>Trained in Barcelona and Stockholm, collected by royal houses across Europe. Original oils, bronzes and lithographs, available directly from the artist's studio.</p>
        <div class="cta-row">
            <a href="#collection" class="btn solid">View the Collection</a>
            <a href="/about/" class="btn">About the Artist</a>
        </div>
    </div>
    <div class="hero-figure ph"{ph_style(hero_rec)}>
        <a href="/work/{hero['slug']}/" aria-label="View {e(hero['title'])} in detail">{picture(hero_rec, hero_alt, SIZES_HERO, eager=True)}</a>
        <div class="cap"><span class="rd"></span> {e(hero['title'])} — Oil on canvas, {e(hero['dimensions'])}, {hero['year']}</div>
    </div>
</section>

<section class="section" style="padding-bottom:2.5rem;">
    <p class="intro-line">A body of work built on <em>bravado and tenderness</em> in equal measure — this collection holds the pieces currently available to acquire, each photographed in the studio where it was made.</p>
</section>
"""

    return f"""<main id="view-home" class="view active">
{hero_html}
<section class="section" id="collection" style="padding-top:2rem;">
    <div class="section-head">
        <div>
            <div class="eyebrow">The Collection</div>
            <h2 id="collection-title">{title}</h2>
        </div>
        <p>Every piece comes directly from the artist's studio, catalogued with its medium, year and — where they have been recorded — its measurements. Click any work to see it in full and inquire.</p>
    </div>
    {filter_bar(active, counts)}
    <div id="gallery" class="gallery">
{cards}
    </div>
</section>

<section class="section">
    <div class="split reveal">
        <figure class="ph"{ph_style(about_rec)}>{picture(about_rec, "Bo Åke Adamsson in the studio", SIZES_SPLIT)}</figure>
        <div>
            <div class="eyebrow">The Artist</div>
            <h2>A storyteller who happens to paint.</h2>
            <p class="pull-quote">"He doesn't pass by unnoticed... an imposing man who looks shamelessly healthy, whose whole person emanates a liberating air of happy-go-luckiness."</p>
            <p class="body-text">Trained at the Real Academia de Bellas Artes in Barcelona and later in bronze casting at Stockholm's Royal Academy, Bo Åke's work sits in the Swedish National Art Museum and in the private collections of Gustaf VI Adolf, Carl XVI Gustaf, and the Sultan of Brunei.</p>
            <a href="/about/" class="btn" style="margin-top:0.6rem;">Read the Full Story</a>
        </div>
    </div>
</section>

<section class="cta-band">
    <h2>Own a piece of this world.</h2>
    <p>Every inquiry reaches the artist's studio directly. Ask about availability, shipping, or arranging a viewing.</p>
    <a href="mailto:{EMAIL}" class="btn">Contact the Studio</a>
</section>
</main>

<main id="view-about" class="view"></main>
<main id="view-work" class="view">
    <div class="work-top">
        <a href="/" class="back-link" id="work-back">← Back to Collection</a>
        <nav class="worknav" aria-label="Browse artworks">
            <a href="/" id="work-prev">← Previous</a>
            <a href="/" id="work-next">Next →</a>
        </nav>
    </div>
    <div class="work-layout" id="work-body"></div>
</main>"""


def inquiry_form(art):
    return f"""<form class="inquiry-form" data-inquiry="{e(art['title'])}">
    <h3>Inquire about this work</h3>
    <p class="sub">Your message goes straight to Bo Åke's studio — no galleries, no middlemen.</p>
    <div class="form-group"><label for="inq-name">Your Name</label>
        <input type="text" id="inq-name" name="name" required placeholder="Enter your full name" autocomplete="name"></div>
    <div class="form-group"><label for="inq-email">Email Address</label>
        <input type="email" id="inq-email" name="email" required placeholder="your.email@example.com" autocomplete="email"></div>
    <div class="form-group"><label for="inq-msg">Message <span style="text-transform:none;font-weight:400;letter-spacing:0;opacity:0.7;">(optional)</span></label>
        <textarea id="inq-msg" name="message" placeholder="Questions about the work, shipping, or arranging a viewing..."></textarea></div>
    <button type="submit" class="btn solid" style="width:100%;">Send Inquiry</button>
    <div class="form-status" role="status"></div>
    <p class="consent">Your name, email and message are sent to the studio through Formspree and used only to answer you. See the <a href="/privacy/">Privacy Policy</a>.</p>
    <p class="direct-line">Prefer email? Write directly to <a href="mailto:{EMAIL}?subject=Inquiry: {e(art['title'])}">{EMAIL}</a></p>
</form>"""


def work_body(art, rec, prev, nxt):
    p = price_display(art["price"], art["type"])
    on_request = p == "Price on Request"
    rows = [("Medium", art["typeName"])]
    rows.append(("Dimensions", art["dimensions"]
                 if art["dimensions"] and art["dimensions"] != "—"
                 else "On request"))
    rows.append(("Year", str(art["year"])))
    specs = "".join(
        f'<div class="spec-row"><span class="k">{k}</span><span class="v">{e(v)}</span></div>'
        for k, v in rows
    )
    specs += (f'<div class="spec-row"><span class="k">Price</span>'
              f'<span class="v price-lg">{p}</span></div>')

    alt = f'{art["title"]} — {art["typeName"]} by Bo Åke Adamsson'
    desc = f'<p class="work-desc">{e(art["description"])}</p>' if art["description"] else ""
    avail = ("This work is available. Send an inquiry below and the studio will respond "
             "personally with the price and delivery details." if on_request else
             "This work is available for purchase. Send an inquiry below and the studio "
             "will respond personally to arrange the details.")

    return f"""<main id="view-work" class="view active">
    <div class="work-top">
        <a href="/" class="back-link" id="work-back">← Back to Collection</a>
        <nav class="worknav" aria-label="Browse artworks">
            <a href="/work/{prev['slug']}/" id="work-prev" rel="prev">← Previous</a>
            <a href="/work/{nxt['slug']}/" id="work-next" rel="next">Next →</a>
        </nav>
    </div>
    <div class="work-layout" id="work-body">
        <div class="work-figure ph"{ph_style(rec)}>{picture(rec, alt, SIZES_WORK, eager=True)}</div>
        <div class="work-info">
            <div class="eyebrow">{e(art['typeName'])}</div>
            <h1>{e(art['title'])}</h1>
            <div class="spec-table">{specs}</div>
            {desc}
            <div class="avail-note"><span class="rd"></span><span>{avail}</span></div>
            {inquiry_form(art)}
        </div>
    </div>
</main>

<main id="view-home" class="view">
    <section class="section" id="collection" style="padding-top:4rem;">
        <div class="section-head">
            <div><div class="eyebrow">The Collection</div><h2 id="collection-title">Selected Works</h2></div>
            <p>Every piece comes directly from the artist's studio, catalogued with its medium, year and measurements.</p>
        </div>
        <div class="filter-bar" role="group" aria-label="Filter artworks"></div>
        <div id="gallery" class="gallery"></div>
    </section>
</main>
<main id="view-about" class="view"></main>"""


def about_body(manifest):
    src = (PARTIALS / "about.html").read_text()
    rec = manifest["about-photo.jpg"]
    src = src.replace(
        '<figure><img src="images/about-photo.jpg" alt="Bo Åke Adamsson" loading="lazy"></figure>',
        f'<figure class="ph"{ph_style(rec)}>'
        + picture(rec, "Bo Åke Adamsson", SIZES_SPLIT, eager=True) + "</figure>",
    )
    src = src.replace('onsubmit="subscribeNewsletter(event)"', "")
    src = src.replace(
        '<div class="form-status" id="newsletter-status" role="status"></div>',
        '<div class="form-status" role="status"></div>\n'
        '                <p class="consent">Your email is stored only to send these updates, '
        'is handled through Formspree, and you can unsubscribe at any time. '
        'See the <a href="/privacy/">Privacy Policy</a>.</p>',
    )
    return f"""<main id="view-about" class="view active">
{src}
<section class="cta-band">
    <h2>See the work in person.</h2>
    <p>Write to the studio to ask about current availability, exhibitions, or arranging a private viewing.</p>
    <a href="mailto:{EMAIL}" class="btn">Contact the Studio</a>
</section>
</main>

<main id="view-home" class="view">
    <section class="section" id="collection" style="padding-top:4rem;">
        <div class="section-head">
            <div><div class="eyebrow">The Collection</div><h2 id="collection-title">Selected Works</h2></div>
            <p>Every piece comes directly from the artist's studio, catalogued with its medium, year and measurements.</p>
        </div>
        <div class="filter-bar" role="group" aria-label="Filter artworks"></div>
        <div id="gallery" class="gallery"></div>
    </section>
</main>
<main id="view-work" class="view">
    <div class="work-top">
        <a href="/" class="back-link" id="work-back">← Back to Collection</a>
        <nav class="worknav" aria-label="Browse artworks">
            <a href="/" id="work-prev">← Previous</a><a href="/" id="work-next">Next →</a>
        </nav>
    </div>
    <div class="work-layout" id="work-body"></div>
</main>"""


def legal_body(name):
    src = (PARTIALS / f"{name}.html").read_text()
    src = (src.replace("{{DATE}}", date.today().strftime("%d %B %Y"))
              .replace("{{PRIVACY_EMAIL}}", PRIVACY_EMAIL)
              .replace("{{SELLER_ADDRESS}}", SELLER_ADDRESS)
              .replace("{{ORGNR}}", SELLER["orgnr"])
              .replace("{{SELLER_NAME}}", SELLER["name"])
              .replace("{{RETENTION}}", RETENTION)
              .replace("{{IDENTITY_NOTE}}", IDENTITY_NOTE)
              .replace("{{EMAIL}}", EMAIL))
    return f'<main class="legal">\n{src}\n</main>'


# --------------------------------------------------------------------------
# structured data
# --------------------------------------------------------------------------

PERSON = {
    "@context": "https://schema.org",
    "@type": "Person",
    "@id": f"{SITE}/#artist",
    "name": "Bo Åke Adamsson",
    "jobTitle": "Painter, Sculptor and Graphic Artist",
    "nationality": "Swedish",
    "email": EMAIL,
    "url": f"{SITE}/",
    "sameAs": [
        "https://instagram.com/boakeadamsson",
        "https://facebook.com/boakeadamsson",
        "https://www.youtube.com/@BoAkeAdamsson.",
        "https://tiktok.com/@boakeadamsson",
    ],
}


def work_jsonld(art, rec):
    on_request = art["type"] == "sculpture" or art["price"] > 10000
    offer = {
        "@type": "Offer",
        "url": f"{SITE}/work/{art['slug']}/",
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
        "seller": {"@id": f"{SITE}/#artist"},
    }
    if on_request:
        offer["priceSpecification"] = {"@type": "PriceSpecification",
                                       "priceCurrency": "EUR"}
    else:
        offer["price"] = str(art["price"])
        offer["priceCurrency"] = "EUR"

    node = {
        "@context": "https://schema.org",
        "@type": "VisualArtwork",
        "name": art["title"],
        "url": f"{SITE}/work/{art['slug']}/",
        "image": f"{SITE}{IMG}{rec['stem']}-1600.jpg",
        "artform": art["typeName"],
        "artist": PERSON,
        "creator": {"@id": f"{SITE}/#artist"},
        "dateCreated": str(art["year"]),
        "offers": offer,
    }
    if art["description"]:
        node["description"] = art["description"]
    if art["dimensions"] and art["dimensions"] != "—":
        node["size"] = art["dimensions"]
        parts = art["dimensions"].replace("cm", "").strip().split("×")
        if len(parts) >= 2:
            try:
                node["height"] = {"@type": "QuantitativeValue",
                                  "value": float(parts[0].strip()), "unitCode": "CMT"}
                node["width"] = {"@type": "QuantitativeValue",
                                 "value": float(parts[1].strip()), "unitCode": "CMT"}
            except ValueError:
                pass
    return node


def breadcrumbs(trail):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name,
             "item": f"{SITE}{url}"}
            for i, (name, url) in enumerate(trail)
        ],
    }


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def write(path, content):
    dest = ROOT / path.lstrip("/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content)


def main():
    artworks = json.loads((ROOT / "artworks.json").read_text())
    manifest = json.loads((ROOT / "tools" / "image-manifest.json").read_text())
    rec_of = lambda a: manifest[a["image"].split("/")[-1]]

    # Compact catalogue for the client: only what site.js renders with.
    client = [{
        "id": a["id"], "slug": a["slug"], "title": a["title"], "type": a["type"],
        "typeName": a["typeName"], "description": a["description"],
        "price": a["price"], "dimensions": a["dimensions"], "year": a["year"],
        "stem": rec_of(a)["stem"], "w": rec_of(a)["width"], "h": rec_of(a)["height"],
        "widths": rec_of(a)["widths"],
    } for a in artworks]

    hero = next(a for a in artworks if a["slug"] == "skal")
    pages = 0

    # Gallery pages (all + one per medium)
    for key, (path, label, _) in FILTERS.items():
        is_home = key == "all"
        title = ("Bo Åke Adamsson — Swedish Painter & Sculptor | Originals, Bronzes, Lithographs"
                 if is_home else f"{label} by Bo Åke Adamsson | Available from the Studio")
        desc = ("Bo Åke Adamsson — Swedish painter, sculptor and graphic artist. Explore original "
                "oil paintings, bronze sculptures, and lithographs available for purchase directly "
                "from the artist's studio." if is_home else
                f"{label} by Swedish artist Bo Åke Adamsson, available directly from the studio. "
                f"Each work catalogued with its medium, year and measurements.")
        ld = [PERSON] if is_home else [breadcrumbs([("Gallery", "/"), (label, path)])]
        if is_home:
            ld.append({
                "@context": "https://schema.org", "@type": "WebSite",
                "name": "Bo Åke Adamsson", "url": f"{SITE}/",
                "inLanguage": "en",
                "publisher": {"@id": f"{SITE}/#artist"},
            })
        hero_rec = rec_of(hero)
        write(path + "index.html", layout(
            title=title, description=desc, path=path,
            body=home_body(artworks, manifest, key, hero),
            jsonld=ld, active="gallery" if is_home else key,
            og_image=f"{IMG}{hero_rec['stem']}-1600.jpg",
            preload=(hero_rec["stem"], hero_rec["widths"], SIZES_HERO),
            page_state={"filter": key}, artworks_data=client))
        pages += 1

    # One page per artwork
    for i, art in enumerate(artworks):
        rec = rec_of(art)
        prev = artworks[(i - 1) % len(artworks)]
        nxt = artworks[(i + 1) % len(artworks)]
        p = price_display(art["price"], art["type"])
        desc = art["description"] or (
            f'{art["title"]} — {art["typeName"].lower()} by Swedish artist Bo Åke Adamsson'
            + (f', {art["dimensions"]}' if art["dimensions"] and art["dimensions"] != "—" else "")
            + f', {art["year"]}. {p if p != "Price on Request" else "Price on request"}. '
              'Available directly from the artist\'s studio.')
        write(f"/work/{art['slug']}/index.html", layout(
            title=f'{art["title"]} — {art["typeName"]} by Bo Åke Adamsson',
            description=desc[:300], path=f"/work/{art['slug']}/",
            body=work_body(art, rec, prev, nxt),
            jsonld=[work_jsonld(art, rec),
                    breadcrumbs([("Gallery", "/"), (art["title"], f"/work/{art['slug']}/")])],
            og_image=f"{IMG}{rec['stem']}-1600.jpg",
            preload=(rec["stem"], rec["widths"], SIZES_WORK),
            active=None, artworks_data=client))
        pages += 1

    # About
    write("/about/index.html", layout(
        title="About Bo Åke Adamsson — Swedish Painter & Sculptor",
        description="Bo Åke Adamsson studied at the Real Academia de Bellas Artes in Barcelona "
                    "and bronze casting at Stockholm's Royal Academy. His work is held by the "
                    "Swedish National Art Museum and royal collections across Europe.",
        path="/about/", body=about_body(manifest),
        jsonld=[PERSON, breadcrumbs([("Gallery", "/"), ("About", "/about/")])],
        active="about", artworks_data=client))
    pages += 1

    # Legal
    for name, title, desc in (
        ("privacy", "Privacy Policy — Bo Åke Adamsson",
         "How this website handles personal data: what the inquiry and newsletter forms "
         "collect, who processes it, how long it is kept, and your rights under the GDPR."),
        ("terms", "Terms of Sale — Bo Åke Adamsson",
         "Terms for buying original artwork directly from Bo Åke Adamsson's studio: "
         "ordering, prices, payment, delivery, the 14-day right of withdrawal, and authenticity."),
    ):
        write(f"/{name}/index.html", layout(
            title=title, description=desc, path=f"/{name}/",
            body=legal_body(name),
            jsonld=[breadcrumbs([("Gallery", "/"), (title.split(" — ")[0], f"/{name}/")])],
            active=None))
        pages += 1

    # 404
    write("/404.html", layout(
        title="Page not found — Bo Åke Adamsson",
        description="That page does not exist. Browse the collection instead.",
        path="/404.html", robots="noindex, follow",
        body=f"""<main class="legal" style="text-align:center;">
    <h1>Not found</h1>
    <p class="updated" style="border:0;">The page you were looking for isn't here — it may have been a work that has since sold.</p>
    <p><a class="btn solid" href="/" style="margin-top:1rem;">View the Collection</a></p>
</main>"""))
    pages += 1

    # robots + sitemap
    write("/robots.txt", f"""User-agent: *
Allow: /
Disallow: /admin.html
Disallow: /images/opt/

Sitemap: {SITE}/sitemap.xml
""")

    today = date.today().isoformat()
    urls = [("/", "1.0", "weekly")]
    urls += [(FILTERS[k][0], "0.8", "weekly") for k in ("oil", "graphics", "sculpture")]
    urls += [("/about/", "0.7", "monthly")]
    urls += [(f"/work/{a['slug']}/", "0.9", "monthly") for a in artworks]
    urls += [("/privacy/", "0.2", "yearly"), ("/terms/", "0.3", "yearly")]
    body = "\n".join(
        f"  <url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>{f}</changefreq><priority>{p}</priority></url>"
        for u, p, f in urls
    )
    write("/sitemap.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{body}
</urlset>
""")

    print(f"Built {pages} pages + robots.txt + sitemap.xml ({len(urls)} URLs)")


if __name__ == "__main__":
    main()
