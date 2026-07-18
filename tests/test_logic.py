import unittest

from support import add_repo_paths

add_repo_paths()

from logic import (
    MAX_NOTICE_LENGTH,
    MAX_NOTICES,
    get_content_hash,
    group_coverage,
    parse_notice_command,
    parse_notice_index,
    target_key,
    valid_notice_content,
)


class TestNoticeLogic(unittest.TestCase):
    def test_parse_notice_index_is_one_based_and_bounded(self) -> None:
        self.assertEqual(parse_notice_index("1", 3), 0)
        self.assertEqual(parse_notice_index(chr(0xFF13), 3), 2)
        self.assertIsNone(parse_notice_index("0", 3))
        self.assertIsNone(parse_notice_index("4", 3))
        self.assertIsNone(parse_notice_index("1_0", 3))
        self.assertIsNone(parse_notice_index("²", 3))
        self.assertIsNone(parse_notice_index("text", 3))

    def test_group_coverage_uses_current_unique_groups_only(self) -> None:
        latest_hash = get_content_hash("latest")
        sent, total = group_coverage(
            [
                {"group_id": 101},
                {"group_id": "102"},
                {"group_id": 101},
                {"unexpected": True},
            ],
            {
                "group:101": latest_hash,
                "group:999": latest_hash,
                "private:1": latest_hash,
            },
            latest_hash,
        )
        self.assertEqual((sent, total), (1, 2))

    def test_notice_limit_matches_runtime_contract(self) -> None:
        self.assertEqual(MAX_NOTICES, 5)

    def test_command_parser_defaults_to_view_and_preserves_content(self) -> None:
        self.assertEqual(
            parse_notice_command("  公告   "),
            parse_notice_command("公告 查看"),
        )
        self.assertEqual(
            parse_notice_command("公告 修改 2  含有  多个空格的内容").argument,
            "2  含有  多个空格的内容",
        )
        self.assertIsNone(parse_notice_command("不是公告"))

    def test_target_keys_are_namespaced(self) -> None:
        self.assertEqual(target_key(group_id=42), "group:42")
        self.assertEqual(target_key(user_id=42), "private:42")
        self.assertNotEqual(target_key(group_id=42), target_key(user_id=42))
        with self.assertRaises(ValueError):
            target_key()

    def test_content_validation_rejects_blank_and_oversized_values(self) -> None:
        self.assertFalse(valid_notice_content(None))
        self.assertFalse(valid_notice_content("   "))
        self.assertTrue(valid_notice_content("ok"))
        self.assertFalse(valid_notice_content("x" * (MAX_NOTICE_LENGTH + 1)))

    def test_coverage_ignores_malformed_group_entries(self) -> None:
        latest_hash = get_content_hash("latest")
        self.assertEqual(
            group_coverage(
                [None, {"group_id": None}, {"group_id": 1}],
                {"group:1": latest_hash},
                latest_hash,
            ),
            (1, 1),
        )


if __name__ == "__main__":
    unittest.main()
