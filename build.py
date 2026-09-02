#!/usr/bin/env python3
"""Build the home page and one detail page per artwork from the site catalog."""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageOps

from media_tools import IMAGE_EXTENSIONS, ROOT, VIDEO_EXTENSIONS, image_derivative_paths, relative_to_root, video_derivative_path


AVAILABILITY_LABELS = {
    "available": "Available",
    "inquire": "Availability on request",
    "made-to-order": "Made to order",
    "reserved": "Reserved",
    "sold": "Sold",
}


def escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_json(filename: str) -> dict:
    return json.loads((ROOT / filename).read_text(encoding="utf-8"))


def asset_url(filename: str) -> str:
    version = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()[:12]
    return f"{filename}?v={version}"


def validate(site: dict, catalog: dict) -> None:
    required_site = {
        "title", "artist", "tagline", "contact_email", "artist_statement",
        "page_title", "meta_description", "hero_eyebrow", "formspree_id",
    }
    missing_site = required_site - site.keys()
    if missing_site:
        raise ValueError(f"site.json is missing: {', '.join(sorted(missing_site))}")
    if not re.fullmatch(r"[a-zA-Z0-9]+", site["formspree_id"]):
        raise ValueError("formspree_id must contain only letters and numbers")

    category_ids = [category["id"] for category in catalog["categories"]]
    if len(category_ids) != len(set(category_ids)):
        raise ValueError("Category IDs must be unique")

    item_ids: set[str] = set()
    for item in catalog["items"]:
        required_item = {"id", "title", "category", "description", "price", "availability", "media"}
        missing = required_item - item.keys()
        if missing:
            raise ValueError(f"{item.get('id', 'Item')} is missing: {', '.join(sorted(missing))}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["id"]):
            raise ValueError(f"Invalid artwork ID: {item['id']}")
        if item["id"] in item_ids:
            raise ValueError(f"Duplicate item ID: {item['id']}")
        item_ids.add(item["id"])
        if item["category"] not in category_ids:
            raise ValueError(f"Unknown category for {item['id']}: {item['category']}")
        if not item["media"]:
            raise ValueError(f"{item['id']} must have at least one image or video")
        for media in item["media"]:
            source = ROOT / media["source"]
            if not source.is_file():
                raise FileNotFoundError(f"Missing media for {item['id']}: {media['source']}")
            if source.suffix.lower() not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
                raise ValueError(f"Unsupported media type: {media['source']}")
            if media.get("poster"):
                poster = ROOT / media["poster"]
                if not poster.is_file():
                    raise FileNotFoundError(f"Missing poster for {item['id']}: {media['poster']}")
                if poster.suffix.lower() not in IMAGE_EXTENSIONS:
                    raise ValueError(f"Unsupported poster type: {media['poster']}")


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        oriented = ImageOps.exif_transpose(image)
        return oriented.size


def optimized_images(source: Path, item_id: str) -> list[tuple[int, str]]:
    candidates: dict[int, str] = {}
    for _, path in image_derivative_paths(source, item_id):
        if path.exists():
            width, _ = image_dimensions(path)
            candidates[width] = relative_to_root(path)
    return sorted(candidates.items())


def first_poster(item: dict) -> str | None:
    for media in item["media"]:
        source = ROOT / media["source"]
        if source.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        optimized = optimized_images(source, item["id"])
        if optimized:
            return optimized[0][1]
        return media["source"]
    return None


def render_media(item: dict, media: dict, index: int, *, eager: bool) -> str:
    source = ROOT / media["source"]
    extension = source.suffix.lower()
    active = " active" if index == 0 else ""
    hidden = "false" if index == 0 else "true"
    alt = escaped(media.get("alt") or item["title"])

    if extension in IMAGE_EXTENSIONS:
        width, height = image_dimensions(source)
        variants = optimized_images(source, item["id"])
        if variants:
            srcset = ", ".join(f"{escaped(path)} {variant_width}w" for variant_width, path in variants)
            display_source = variants[-1][1]
            source_tag = f'<source type="image/webp" srcset="{srcset}" sizes="(max-width: 720px) 94vw, 44vw">'
        else:
            display_source = media["source"]
            source_tag = ""
        loading = "eager" if eager else "lazy"
        element = (
            f'<picture>{source_tag}<img src="{escaped(display_source)}" alt="{alt}" '
            f'width="{width}" height="{height}" loading="{loading}" decoding="async" '
            f'data-full-src="{escaped(media["source"])}"></picture>'
        )
    else:
        converted = video_derivative_path(source, item["id"])
        display_source = relative_to_root(converted) if converted.exists() else media["source"]
        poster = media.get("poster") or first_poster(item)
        poster_attribute = f' poster="{escaped(poster)}"' if poster else ""
        element = (
            f'<video muted loop playsinline preload="metadata" aria-label="{alt}"{poster_attribute}>'
            f'<source src="{escaped(display_source)}" type="video/mp4">'
            "Your browser does not support embedded video.</video>"
        )

    media_type = "Video" if extension in VIDEO_EXTENSIONS else "Image"
    return f'<div class="carousel-item{active}" aria-hidden="{hidden}">{element}<span class="media-type">{media_type}</span></div>'


def detail_filename(item: dict) -> str:
    return f"mobile-{item['id']}.html"


def render_card(item: dict, category: dict, *, eager: bool, preview: bool = False) -> str:
    # Lead with motion when available, keeping the remaining views in order.
    gallery_media = list(item["media"])
    for index, media in enumerate(gallery_media):
        if Path(media["source"]).suffix.lower() in VIDEO_EXTENSIONS:
            gallery_media.insert(0, gallery_media.pop(index))
            break
    if preview:
        gallery_media = gallery_media[:1]
    media_html = "".join(render_media(item, media, index, eager=eager and index == 0) for index, media in enumerate(gallery_media))
    controls = ""
    if preview:
        controls = f'<a class="button button-primary detail-link" href="{escaped(detail_filename(item))}" aria-label="See Detail for {escaped(item["title"])}">See Detail</a>'
    elif len(gallery_media) > 1:
        controls = f'''
            <div class="carousel-controls">
              <button class="carousel-button previous" type="button" aria-label="Previous view of {escaped(item['title'])}">‹</button>
              <span class="carousel-count" aria-live="polite">1 / {len(item['media'])}</span>
              <button class="carousel-button next" type="button" aria-label="Next view of {escaped(item['title'])}">›</button>
            </div>'''

    facts: list[str] = []
    if item.get("dimensions"):
        facts.append(f'<li><span>Dimensions</span>{escaped(item["dimensions"])}</li>')
    if item.get("materials"):
        facts.append(f'<li><span>Materials</span>{escaped(item["materials"])}</li>')
    if item.get("year"):
        facts.append(f'<li><span>Year</span>{escaped(item["year"])}</li>')
    facts_html = f'<ul class="artwork-facts">{"".join(facts)}</ul>' if facts else ""

    price = "Contact for price" if item.get("price") is None else f'${item["price"]:,.2f}'.replace(".00", "")
    availability = AVAILABILITY_LABELS.get(item["availability"], item["availability"].replace("-", " ").title())
    featured = '<span class="featured-label">Featured</span>' if item.get("featured") else ""
    heading = "h3" if preview else "h1"
    gallery_tabindex = ' tabindex="0"' if not preview and len(gallery_media) > 1 else ""
    media_label = "Preview" if preview else "Media gallery"
    inquiry_url = "#contact" if preview else f"index.html?artwork={quote(item['title'], safe='')}#contact"

    return f'''
      <article class="artwork-card" id="{escaped(item['id'])}">
        <div class="artwork-media carousel"{gallery_tabindex} aria-label="{media_label} for {escaped(item['title'])}">
          <div class="carousel-inner">{media_html}</div>{controls}
        </div>
        <div class="artwork-copy">
          <div class="artwork-labels"><span>{escaped(category['name'])}</span>{featured}</div>
          <{heading}>{escaped(item['title'])}</{heading}>
          <p class="artwork-description">{escaped(item['description'])}</p>
{facts_html}
          <div class="artwork-purchase">
            <div><strong>{escaped(price)}</strong><span class="availability availability-{escaped(item['availability'])}">{escaped(availability)}</span></div>
            <a class="inquire-button" href="{escaped(inquiry_url)}" data-inquire-title="{escaped(item['title'])}">Inquire</a>
          </div>
        </div>
      </article>'''


def render_detail_page(site: dict, item: dict, category: dict) -> str:
    lightbox_enabled = bool(item.get("image_lightbox"))
    body_attribute = ' data-image-lightbox="true"' if lightbox_enabled else ""
    lightbox = '''
  <dialog class="image-lightbox" data-lightbox-dialog aria-label="Expanded artwork image">
    <div class="image-lightbox-toolbar">
      <button class="image-lightbox-size" type="button" data-lightbox-size>View actual size</button>
      <button class="image-lightbox-close" type="button" data-lightbox-close aria-label="Close expanded image">×</button>
    </div>
    <div class="image-lightbox-stage" data-lightbox-stage data-mode="fit">
      <img class="image-lightbox-image" data-lightbox-image src="" alt="">
    </div>
  </dialog>''' if lightbox_enabled else ""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="description" content="{escaped(item['description'])}">
  <meta name="theme-color" content="#252626">
  <title>{escaped(item['title'])} — {escaped(site['artist'])}</title>
  <link rel="stylesheet" href="{asset_url('style.css')}">
  <script src="{asset_url('script.js')}" defer></script>
</head>
<body{body_attribute}>
  <main class="detail-page">
    <a class="button back-button" href="index.html#{escaped(item['id'])}">← Back</a>
{render_card(item, category, eager=True)}
  </main>
{lightbox}
</body>
</html>
'''


def render_mailinglist_page(site: dict, version: str) -> str:
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="description" content="Join the {escaped(site['title'])} mailing list for news and updates from {escaped(site['artist'])}.">
  <meta name="theme-color" content="#252626">
  <title>Join Mailing List — {escaped(site['title'])}</title>
  <link rel="stylesheet" href="{asset_url('style.css')}">
  <script src="{asset_url('script.js')}" defer></script>
  <script>
    window.formspree = window.formspree || function () {{ (formspree.q = formspree.q || []).push(arguments); }};
    formspree('initForm', {{ formElement: '#mailing-list-form', formId: {json.dumps(site['formspree_id'])} }});
  </script>
  <script src="https://unpkg.com/@formspree/ajax@1" defer></script>
</head>
<body class="mailing-list-page">
  <a class="skip-link" href="#mailing-list-form">Skip to mailing list form</a>
  <header class="site-header">
    <a class="brand" href="index.html" aria-label="{escaped(site['title'])} home"><strong>{escaped(site['artist'])}</strong><span>{escaped(site['title'])}</span></a>
    <nav class="primary-nav" aria-label="Primary navigation"><a href="index.html">Home</a><a href="index.html#work">Work</a><a href="index.html#contact">Contact</a></nav>
  </header>

  <main>
    <section class="hero mailing-list-hero" aria-labelledby="page-title">
      <div class="hero-orbit" aria-hidden="true"><span></span><span></span><span></span></div>
      <p class="eyebrow">Stay connected</p>
      <h1 id="page-title">{escaped(site['title'])}</h1>
      <h2>Join Mailing List</h2>

      <div data-fs-success></div>
      <div data-fs-error></div>

      <form id="mailing-list-form" class="contact-form mailing-list-form" action="https://formspree.io/f/{escaped(site['formspree_id'])}" method="post" enctype="text/plain">
        <label>Name<input type="text" name="name" autocomplete="name" required data-fs-field><span data-fs-error="name"></span></label>
        <label>Email<input type="email" name="email" autocomplete="email" required data-fs-field><span data-fs-error="email"></span></label>
        <input type="hidden" name="form_type" value="Mailing list signup">
        <button class="button button-primary" type="submit" data-fs-submit-btn>Join Mailing List</button>
        <p class="form-note">No personal information is stored by this website.</p>
        <p class="form-status" aria-live="polite"></p>
      </form>
    </section>
  </main>

  <footer class="site-footer"><p>© <span id="current-year"></span> {escaped(site['artist'])}</p><p class="site-version">Version <span data-site-version>{escaped(version)}</span></p><a href="index.html">Back to home ↑</a></footer>
</body>
</html>
'''


def render_featured_card(item: dict, category: dict) -> str:
    media = next(
        (entry for entry in item["media"] if (ROOT / entry["source"]).suffix.lower() in IMAGE_EXTENSIONS),
        None,
    )
    if media is None:
        return ""
    source = ROOT / media["source"]
    width, height = image_dimensions(source)
    variants = optimized_images(source, item["id"])
    display_source = variants[0][1] if variants else media["source"]
    return f'''
        <a class="featured-card" href="{escaped(detail_filename(item))}">
          <img src="{escaped(display_source)}" alt="{escaped(media.get('alt') or item['title'])}" width="{width}" height="{height}" loading="lazy" decoding="async">
          <span><small>{escaped(category['name'])}</small><strong>{escaped(item['title'])}</strong></span>
        </a>'''


def render_page(site: dict, catalog: dict, version: str) -> str:
    used_categories = [category for category in catalog["categories"] if any(item["category"] == category["id"] for item in catalog["items"])]
    categories_by_id = {category["id"]: category for category in catalog["categories"]}
    nav_links = "".join(f'<a href="#{escaped(category["id"])}">{escaped(category["name"])}</a>' for category in used_categories)

    sections: list[str] = []
    first_card = True
    for category in used_categories:
        cards: list[str] = []
        for item in [entry for entry in catalog["items"] if entry["category"] == category["id"]]:
            cards.append(render_card(item, category, eager=first_card, preview=True))
            first_card = False
        sections.append(f'''
    <section class="collection-section" id="{escaped(category['id'])}" aria-labelledby="{escaped(category['id'])}-title">
      <div class="section-heading">
        <p class="eyebrow">Collection</p>
        <h2 id="{escaped(category['id'])}-title">{escaped(category['name'])}</h2>
        <p>{escaped(category['description'])}</p>
      </div>
      <div class="artwork-grid">{"".join(cards)}</div>
    </section>''')

    statement = "".join(f"<p>{escaped(paragraph)}</p>" for paragraph in site["artist_statement"])
    artwork_options = "".join(f'<option value="{escaped(item["title"])}">{escaped(item["title"])}</option>' for item in catalog["items"])
    featured_cards = "".join(
        render_featured_card(item, categories_by_id[item["category"]])
        for item in catalog["items"] if item.get("featured")
    )
    contact_email = escaped(site["contact_email"])

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="description" content="{escaped(site['meta_description'])}">
  <meta name="theme-color" content="#252626">
  <title>{escaped(site['page_title'])}</title>
  <link rel="stylesheet" href="{asset_url('style.css')}">
  <script src="{asset_url('script.js')}" defer></script>
  <script>
    window.formspree = window.formspree || function () {{ (formspree.q = formspree.q || []).push(arguments); }};
    formspree('initForm', {{ formElement: '#contact-form', formId: {json.dumps(site['formspree_id'])} }});
  </script>
  <script src="https://unpkg.com/@formspree/ajax@1" defer></script>
</head>
<body>
  <a class="skip-link" href="#work">Skip to artwork</a>
  <header class="site-header">
    <a class="brand" href="#top" aria-label="{escaped(site['title'])} home"><strong>{escaped(site['artist'])}</strong><span>{escaped(site['title'])}</span></a>
    <nav class="primary-nav" aria-label="Primary navigation"><a href="#work">Work</a><a href="#about">About</a><a href="#contact">Contact</a><a href="mailinglist.html">Mailing List</a></nav>
  </header>

  <main id="top">
    <section class="hero" aria-labelledby="page-title">
      <div class="hero-orbit" aria-hidden="true"><span></span><span></span><span></span></div>
      <p class="eyebrow">{escaped(site['hero_eyebrow'])}</p>
      <h1 id="page-title">{escaped(site['title'])}</h1>
      <p class="hero-intro">{escaped(site['tagline'])}</p>
      <div class="hero-actions"><a class="button button-primary" href="#work">Explore the work</a><a class="text-link" href="#contact">Discuss a commission</a></div>
      <details class="artist-statement" id="about">
        <summary>Artist Statement: <span class="artist-statement-caret" aria-hidden="true">▼</span></summary>
        <div class="artist-statement-content">{statement}</div>
      </details>
    </section>

    <section class="featured-section" id="work" aria-labelledby="featured-title">
      <div class="section-heading"><div><p class="eyebrow">Selected work</p><h2 id="featured-title">Mobiles in motion</h2></div><p>A selection of suspended works ranging from spare studies in balance to complex, multi-level constructions.</p></div>
      <div class="featured-grid">{featured_cards}</div>
    </section>

    <div class="collection-nav"><nav aria-label="Artwork collections">{nav_links}</nav></div>
    <div class="collections">{"".join(sections)}</div>

    <section class="contact-section" id="contact" aria-labelledby="contact-title">
      <div class="contact-intro">
        <p class="eyebrow">Contact</p>
        <h2 id="contact-title">Ask about a work or commission</h2>
        <p>Share the piece you are interested in, your location, and any questions about scale, installation, or a custom mobile.</p>
        <a class="contact-email" href="mailto:{contact_email}">{contact_email}</a>
      </div>

      <div data-fs-success></div>
      <div data-fs-error></div>

      <form id="contact-form" class="contact-form" action="https://formspree.io/f/{escaped(site['formspree_id'])}" method="post" enctype="text/plain">
        <div class="field-row">
            <label>Name<input type="text" name="name" autocomplete="name" required data-fs-field ><span data-fs-error="name"></span></label>
            <label>Email<input type="email" name="email" autocomplete="email" required data-fs-field ><span data-fs-error="email"></span></label>
        </div>
        <label>Artwork<select name="artwork" id="contact-artwork" data-fs-field ><option value="General inquiry">General inquiry</option>{artwork_options}<option value="Commission">Commission or custom work</option></select><span data-fs-error="artwork"></span></label>
        <label>Message
            <textarea name="message" rows="6" required placeholder="Tell me what you would like to know…" data-fs-field ></textarea>
            <span data-fs-error="message"></span>
        </label>
        <button class="button button-primary" type="submit" data-fs-submit-btn>Send email</button>
        <p class="form-note">No personal information is stored by this website.</p>
        <p class="form-status" aria-live="polite"></p>
      </form>

    </section>
  </main>

  <footer class="site-footer"><p>© <span id="current-year"></span> {escaped(site['artist'])}</p><p class="site-version">Version <span data-site-version>{escaped(version)}</span></p><a href="#top">Back to top ↑</a></footer>
</body>
</html>
'''


def main() -> int:
    site = load_json("site.json")
    catalog = load_json("items.json")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    validate(site, catalog)
    output = ROOT / "index.html"
    output.write_text(render_page(site, catalog, version), encoding="utf-8")
    mailing_list_output = ROOT / "mailinglist.html"
    mailing_list_output.write_text(render_mailinglist_page(site, version), encoding="utf-8")
    categories = {category["id"]: category for category in catalog["categories"]}
    for item in catalog["items"]:
        detail = ROOT / detail_filename(item)
        detail.write_text(render_detail_page(site, item, categories[item["category"]]), encoding="utf-8")
    print(f"Built {output.name}, {mailing_list_output.name}, and {len(catalog['items'])} artwork detail pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
