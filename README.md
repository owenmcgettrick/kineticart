# Kinetic Creations website

This is a static portfolio and inquiry website for Owen McGettrick. GitHub serves
the generated `index.html` at [owenmcgettrick.com](https://owenmcgettrick.com/).

## Add an artwork

Run the interactive helper from this folder:

```bash
python3 add_item.py
```

The helper asks for the artwork details and media files, then:

1. adds the artwork to `items.json`;
2. copies its original media into `img/`;
3. creates smaller web images and a web-video version when supported; and
4. rebuilds `index.html`.

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

Artwork galleries start with their first video when one is available and play
it automatically when visible. The remaining views keep their catalog order;
galleries containing only photos are unchanged.

Use a number for `price`, or `null` to display “Contact for price.” Optional
fields such as `dimensions`, `materials`, and `year` can also remain `null`.
Supported availability values are `available`, `inquire`, `made-to-order`,
`reserved`, and `sold`.

Categories are defined at the top of `items.json`. Tabletop and wall-mounted
categories are ready to appear automatically when an artwork is assigned to
them.

## Site and contact details

The artist name, introduction, statement, and contact email are stored in
`site.json`. Confirm that `owen@owenmcgettrick.com` is an active mailbox before
publishing; change `contact_email` there if another address should receive
inquiries, then run `python3 build.py`.

The contact form prepares a message in the visitor's email application. The
static website does not collect or store form submissions.

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
