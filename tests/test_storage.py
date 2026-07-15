import json
import tempfile
import unittest
from pathlib import Path

from storage import load_history, load_notices, save_json


class TestNoticeStorage(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_json_creates_parent_and_round_trips(self) -> None:
        file = self.root / "nested" / "notices.json"
        save_json(file, ["第一条", "第二条"])
        self.assertEqual(load_notices(file), ["第一条", "第二条"])
        self.assertFalse(list(file.parent.glob("*.tmp")))

    def test_malformed_or_wrong_shape_uses_safe_shape(self) -> None:
        notices = self.root / "notices.json"
        notices.write_text("not json", encoding="utf-8")
        self.assertEqual(load_notices(notices), [])

        notices.write_text(json.dumps({"unexpected": True}), encoding="utf-8")
        self.assertEqual(load_notices(notices), [])

        history = self.root / "history.json"
        history.write_text(json.dumps(["unexpected"]), encoding="utf-8")
        self.assertEqual(load_history(history), {})

    def test_history_filters_non_string_values(self) -> None:
        history = self.root / "history.json"
        history.write_text(
            json.dumps({"group_1": "hash", "group_2": 123}),
            encoding="utf-8",
        )
        self.assertEqual(load_history(history), {"group_1": "hash"})


if __name__ == "__main__":
    unittest.main()
