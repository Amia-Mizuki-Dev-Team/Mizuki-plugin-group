import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from support import add_repo_paths

add_repo_paths()

from storage import load_history, load_notices, record_history, save_json


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
            json.dumps({"legacy:group-1": "hash", "legacy:group-2": 123}),
            encoding="utf-8",
        )
        self.assertEqual(load_history(history), {"legacy:group-1": "hash"})

    def test_record_history_merges_latest_targets(self) -> None:
        history = self.root / "history.json"
        record_history(history, "group:1", "hash-1")
        record_history(history, "private:2", "hash-2")
        self.assertEqual(
            load_history(history),
            {"group:1": "hash-1", "private:2": "hash-2"},
        )

    def test_atomic_write_cleans_temp_file_after_replace_failure(self) -> None:
        file = self.root / "notices.json"
        with patch("storage.Path.replace", side_effect=OSError), self.assertRaises(
            OSError
        ):
            save_json(file, ["notice"])
        self.assertFalse(list(self.root.glob("*.tmp")))

    def test_atomic_write_does_not_leave_partial_json(self) -> None:
        file = self.root / "nested" / "notices.json"
        save_json(file, ["old"])
        with patch("storage.os.fsync", side_effect=OSError):
            with self.assertRaises(OSError):
                save_json(file, ["new"])
        self.assertEqual(load_notices(file), ["old"])


if __name__ == "__main__":
    unittest.main()
