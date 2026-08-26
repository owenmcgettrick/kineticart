# Kinetic Creations website

This is a static portfolio and inquiry website for Owen McGettrick. GitHub serves
the generated `index.html` and artwork detail pages at
[owenmcgettrick.com](https://owenmcgettrick.com/).

## Add an artwork

Run the interactive helper from this folder:

```bash
python3 add_item.py
```

The helper asks for the artwork details and media files, then:

1. adds the artwork to `items.json`;
2. copies its original media into `img/`;
3. creates smaller web images and a web-video version when supported; and
4. rebuilds `index.html` and creates a `mobile-<id>.html` page for every artwork.

Review the result before committing and pushing it.

## Site version

The version shown in the footer starts at `1.0`. A repository pre-commit hook
increments the second number for each subsequent commit and includes the new
version in that commit. The hook is enabled in this checkout with:

```bash
git config core.hooksPath .githooks
```

Run that command once after cloning the repository on another computer.

## Edit an existing artwork

Edit its record in `items.json`, then rebuild:

```bash
python3 build.py
```

The home page shows one preview per artwork and a “See Detail” link to its
`mobile-<id>.html` page. Each detail page contains the full gallery, artwork
information, and a Back button returning to the matching home-page card.
Artwork previews and galleries start with their first video when available and
play it automatically when visible. The remaining gallery views keep their
catalog order; photo-only galleries keep their original order.

The same build command generates pages for new entries in `items.json`; no
manual HTML editing is needed. Commit the generated pages along with the
catalog changes. To run the build tests, use `python3 -m unittest -v`.

Use a number for `price`, or `null` to display “Contact for price.” Optional
fields such as `dimensions`, `materials`, and `year` can also remain `null`.
Supported availability values are `available`, `inquire`, `made-to-order`,
`reserved`, and `sold`.

Categories are defined at the top of `items.json`. Tabletop and wall-mounted
categories are ready to appear automatically when an artwork is assigned to
them.

## Site and contact details

The artist name, page title, description, introduction, statement, contact email,
and Formspree form ID are stored in `site.json`. Edit these settings there, then
run `python3 build.py` so future builds retain the changes.

The contact form submits through the existing Formspree integration. Inquire
links on detail pages return to the home-page form with the artwork selected.

## Refresh optimized media

Original files under the artwork folders in `img/` are retained. Browser-sized
derivatives live in `img/web/` and can be regenerated with:

```bash
python3 optimize_media.py --force
python3 build.py
```

The image workflow requires Pillow. On macOS, the helper uses `avconvert` to
produce 480p web-video derivatives; if it is unavailable, the original video is
used as a fallback.
