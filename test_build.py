import unittest
from unittest.mock import patch

from build import render_card


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


if __name__ == "__main__":
    unittest.main()
