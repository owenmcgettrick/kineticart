import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build
from build import detail_filename, render_card, render_detail_page, render_mailinglist_page, render_page


class GalleryOrderTests(unittest.TestCase):
    def check_order(self, sources, expected):
        item = {
            "id": "test-mobile",
            "title": "Test Mobile",
            "description": "A mobile",
            "price": None,
            "availability": "inquire",
            "media": [{"source": source} for source in sources],
        }
        with patch("build.render_media", return_value="") as render:
            render_card(item, {"name": "Mobiles"}, eager=True)

        self.assertEqual(
            [(call.args[1]["source"], call.args[2], call.kwargs["eager"])
             for call in render.call_args_list],
            [(source, index, index == 0) for index, source in enumerate(expected)],
        )
        self.assertEqual([media["source"] for media in item["media"]], sources)

    def test_photo_only_gallery_keeps_order(self):
        self.check_order(["first.jpg", "second.jpg"], ["first.jpg", "second.jpg"])

    def test_first_video_moves_to_front(self):
        self.check_order(
            ["first.jpg", "second.jpg", "motion.MOV"],
            ["motion.MOV", "first.jpg", "second.jpg"],
        )

    def test_additional_video_keeps_its_place_among_remaining_views(self):
        self.check_order(
            ["first.jpg", "motion.mp4", "second.jpg", "wide.mp4"],
            ["motion.mp4", "first.jpg", "second.jpg", "wide.mp4"],
        )

    def test_video_already_first_keeps_order(self):
        self.check_order(["motion.mp4", "first.jpg"], ["motion.mp4", "first.jpg"])


class ArtworkPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.site = build.load_json("site.json")
        cls.catalog = build.load_json("items.json")
        cls.categories = {entry["id"]: entry for entry in cls.catalog["categories"]}

    def test_home_has_one_preview_and_detail_link_per_artwork(self):
        page = render_page(self.site, self.catalog, "1.0")
        self.assertNotIn('class="carousel-controls"', page)
        self.assertEqual(page.count('class="carousel-item active"'), len(self.catalog["items"]))
        for item in self.catalog["items"]:
            with self.subTest(item=item["id"]):
                card = render_card(item, self.categories[item["category"]], eager=False, preview=True)
                self.assertIn(f'href="{detail_filename(item)}"', card)
                self.assertIn('>See Detail</a>', card)
                has_video = any(Path(media["source"]).suffix.lower() in build.VIDEO_EXTENSIONS for media in item["media"])
                self.assertEqual('<video ' in card, has_video)

    def test_detail_pages_preserve_galleries_and_link_back(self):
        for item in self.catalog["items"]:
            with self.subTest(item=item["id"]):
                page = render_detail_page(self.site, item, self.categories[item["category"]])
                self.assertEqual(len(re.findall(r'class="carousel-item(?: active)?"', page)), len(item["media"]))
                self.assertIn(f'href="index.html#{item["id"]}"', page)
                self.assertIn(f'<h1>{build.escaped(item["title"])}</h1>', page)
                self.assertIn(build.escaped(item["description"]), page)
                self.assertIn('href="index.html?artwork=', page)
                self.assertNotIn('>See Detail</a>', page)

    def test_image_lightbox_is_enabled_only_for_opted_in_artwork(self):
        enabled = next(item for item in self.catalog["items"] if item["id"] == "circular-platforms-structural")
        disabled = next(item for item in self.catalog["items"] if item["id"] != enabled["id"])
        enabled_page = render_detail_page(self.site, enabled, self.categories[enabled["category"]])
        disabled_page = render_detail_page(self.site, disabled, self.categories[disabled["category"]])

        self.assertIn('data-image-lightbox="true"', enabled_page)
        self.assertIn('data-lightbox-dialog', enabled_page)
        self.assertIn('data-lightbox-size', enabled_page)
        self.assertNotIn('data-lightbox-dialog', disabled_page)

    def test_homepage_videos_use_explicit_first_frame_posters(self):
        for item in self.catalog["items"]:
            video = next(
                (media for media in item["media"] if Path(media["source"]).suffix.lower() in build.VIDEO_EXTENSIONS),
                None,
            )
            if video is None:
                continue
            with self.subTest(item=item["id"]):
                self.assertIn("poster", video)
                rendered = build.render_media(item, video, 0, eager=False)
                self.assertIn(f'poster="{video["poster"]}"', rendered)

    def test_mailing_list_page_has_only_name_and_email_fields(self):
        page = render_mailinglist_page(self.site, "1.0")
        self.assertIn('<h1 id="page-title">Kinetic Creations</h1>', page)
        self.assertIn('<h2>Join Mailing List</h2>', page)
        self.assertIn('class="hero mailing-list-hero"', page)
        self.assertIn('name="name"', page)
        self.assertIn('name="email"', page)
        self.assertNotIn('<select', page)
        self.assertNotIn('<textarea', page)

    def test_build_creates_page_for_new_catalog_entry(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["items"] = [catalog["items"][0]]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "img").symlink_to(build.ROOT / "img", target_is_directory=True)
            for filename in ("style.css", "script.js"):
                (root / filename).symlink_to(build.ROOT / filename)
            (root / "site.json").write_text(json.dumps(self.site))
            (root / "VERSION").write_text("1.0\n")
            (root / "items.json").write_text(json.dumps(catalog))
            with patch("build.ROOT", root):
                build.main()
                new_item = copy.deepcopy(catalog["items"][0])
                new_item.update(id="new-mobile", title="New Mobile")
                new_item["media"] = new_item["media"][:1]
                catalog["items"].append(new_item)
                (root / "items.json").write_text(json.dumps(catalog))
                build.main()
            self.assertIn('href="mobile-new-mobile.html"', (root / "index.html").read_text())
            self.assertIn('<h1>New Mobile</h1>', (root / "mobile-new-mobile.html").read_text())
            self.assertNotIn('class="carousel-controls"', (root / "mobile-new-mobile.html").read_text())
            self.assertIn('<h2>Join Mailing List</h2>', (root / "mailinglist.html").read_text())

    def test_invalid_id_cannot_write_outside_detail_page_path(self):
        catalog = copy.deepcopy(self.catalog)
        catalog["items"][0]["id"] = "../outside"
        with self.assertRaisesRegex(ValueError, "Invalid artwork ID"):
            build.validate(self.site, catalog)


if __name__ == "__main__":
    unittest.main()
