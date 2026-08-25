#!/usr/bin/env python3
"""Build index.html from site.json and items.json."""

from __future__ import annotations

import html
import json
from pathlib import Path

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


def validate(site: dict, catalog: dict) -> None:
    required_site = {"title", "artist", "tagline", "contact_email", "artist_statement"}
    missing_site = required_site - site.keys()
    if missing_site:
        raise ValueError(f"site.json is missing: {', '.join(sorted(missing_site))}")

    category_ids = [category["id"] for category in catalog["categories"]]
    if len(category_ids) != len(set(category_ids)):
        raise ValueError("Category IDs must be unique")

    item_ids: set[str] = set()
    for item in catalog["items"]:
        required_item = {"id", "title", "category", "description", "price", "availability", "media"}
        missing = required_item - item.keys()
        if missing:
            raise ValueError(f"{item.get('id', 'Item')} is missing: {', '.join(sorted(missing))}")
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
            f'width="{width}" height="{height}" loading="{loading}" decoding="async"></picture>'
        )
    else:
        converted = video_derivative_path(source, item["id"])
        display_source = relative_to_root(converted) if converted.exists() else media["source"]
        poster = first_poster(item)
        poster_attribute = f' poster="{escaped(poster)}"' if poster else ""
        element = (
            f'<video muted loop playsinline preload="metadata" aria-label="{alt}"{poster_attribute}>'
            f'<source src="{escaped(display_source)}" type="video/mp4">'
            "Your browser does not support embedded video.</video>"
        )

    media_type = "Video" if extension in VIDEO_EXTENSIONS else "Image"
    return f'<div class="carousel-item{active}" aria-hidden="{hidden}">{element}<span class="media-type">{media_type}</span></div>'


def render_card(item: dict, category: dict, *, eager: bool) -> str:
    media_html = "".join(render_media(item, media, index, eager=eager and index == 0) for index, media in enumerate(item["media"]))
    controls = ""
    if len(item["media"]) > 1:
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

    return f'''
      <article class="artwork-card" id="{escaped(item['id'])}">
        <div class="artwork-media carousel" tabindex="0" aria-label="Media gallery for {escaped(item['title'])}">
          <div class="carousel-inner">{media_html}</div>{controls}
        </div>
        <div class="artwork-copy">
          <div class="artwork-labels"><span>{escaped(category['name'])}</span>{featured}</div>
          <h3>{escaped(item['title'])}</h3>
          <p class="artwork-description">{escaped(item['description'])}</p>
{facts_html}
          <div class="artwork-purchase">
            <div><strong>{escaped(price)}</strong><span class="availability availability-{escaped(item['availability'])}">{escaped(availability)}</span></div>
            <a class="inquire-button" href="#contact" data-inquire-title="{escaped(item['title'])}">Inquire</a>
          </div>
        </div>
      </article>'''


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
        <a class="featured-card" href="#{escaped(item['id'])}">
          <img src="{escaped(display_source)}" alt="{escaped(media.get('alt') or item['title'])}" width="{width}" height="{height}" loading="lazy" decoding="async">
          <span><small>{escaped(category['name'])}</small><strong>{escaped(item['title'])}</strong></span>
        </a>'''


def render_page(site: dict, catalog: dict) -> str:
    used_categories = [category for category in catalog["categories"] if any(item["category"] == category["id"] for item in catalog["items"])]
    categories_by_id = {category["id"]: category for category in catalog["categories"]}
    nav_links = "".join(f'<a href="#{escaped(category["id"])}">{escaped(category["name"])}</a>' for category in used_categories)

    sections: list[str] = []
    first_card = True
    for category in used_categories:
        cards: list[str] = []
        for item in [entry for entry in catalog["items"] if entry["category"] == category["id"]]:
            cards.append(render_card(item, category, eager=first_card))
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
  <meta name="description" content="Kinetic mobiles and suspended sculpture by artist {escaped(site['artist'])}.">
  <meta name="theme-color" content="#252626">
  <title>{escaped(site['title'])} — {escaped(site['artist'])}</title>
  <link rel="stylesheet" href="style.css">
  <script src="script.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#work">Skip to artwork</a>
  <header class="site-header">
    <a class="brand" href="#top" aria-label="{escaped(site['title'])} home"><strong>{escaped(site['artist'])}</strong><span>{escaped(site['title'])}</span></a>
    <nav class="primary-nav" aria-label="Primary navigation"><a href="#work">Work</a><a href="#about">About</a><a href="#contact">Contact</a></nav>
  </header>

  <main id="top">
    <section class="hero" aria-labelledby="page-title">
      <div class="hero-orbit" aria-hidden="true"><span></span><span></span><span></span></div>
      <p class="eyebrow">Suspended sculpture · kinetic art</p>
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
      <form class="contact-form" action="mailto:{contact_email}" method="post" enctype="text/plain" data-contact-email="{contact_email}">
        <div class="field-row"><label>Name<input type="text" name="name" autocomplete="name" required></label><label>Email<input type="email" name="email" autocomplete="email" required></label></div>
        <label>Artwork<select name="artwork" id="contact-artwork"><option value="General inquiry">General inquiry</option>{artwork_options}<option value="Commission">Commission or custom work</option></select></label>
        <label>Message<textarea name="message" rows="6" required placeholder="Tell me what you would like to know…"></textarea></label>
        <button class="button button-primary" type="submit">Prepare email</button>
        <p class="form-note">Submitting opens a prepared message in your email application. No information is stored by this website.</p>
        <p class="form-status" aria-live="polite"></p>
      </form>
    </section>
  </main>

  <footer class="site-footer"><p>© <span id="current-year"></span> {escaped(site['artist'])}</p><a href="#top">Back to top ↑</a></footer>
</body>
</html>
'''


def main() -> int:
    site = load_json("site.json")
    catalog = load_json("items.json")
    validate(site, catalog)
    output = ROOT / "index.html"
    output.write_text(render_page(site, catalog), encoding="utf-8")
    print(f"Built {output.name} with {len(catalog['items'])} artworks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
