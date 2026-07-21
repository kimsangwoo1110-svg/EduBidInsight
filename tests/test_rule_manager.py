import unittest

from gui.rule_manager import (
    RULE_TABLE_COLUMNS,
    rule_table_values,
    rule_test_display_values,
    sort_rule_records,
)


class RuleManagerUiLogicTest(unittest.TestCase):
    def setUp(self):
        self.rules = [
            {
                "id": 1,
                "enabled": 1,
                "category": "예산",
                "recommendation": "대형 제안",
                "score": 25,
                "description": "예산 조건",
            },
            {
                "id": 2,
                "enabled": 0,
                "category": "AI",
                "recommendation": "AI 제안",
                "score": 40,
                "description": "AI 조건",
            },
        ]

    def test_required_columns_and_table_values(self):
        self.assertEqual(
            [column[0] for column in RULE_TABLE_COLUMNS],
            ["enabled", "category", "recommendation", "score", "description"],
        )
        self.assertEqual(
            rule_table_values(self.rules[1]),
            ("중지", "AI", "AI 제안", 40, "AI 조건"),
        )

    def test_table_sort_supports_text_number_and_enabled(self):
        self.assertEqual(
            [rule["id"] for rule in sort_rule_records(self.rules, "category")],
            [2, 1],
        )
        self.assertEqual(
            [rule["id"] for rule in sort_rule_records(self.rules, "score", True)],
            [2, 1],
        )
        self.assertEqual(
            [rule["id"] for rule in sort_rule_records(self.rules, "enabled")],
            [2, 1],
        )

    def test_rule_test_result_is_mapped_to_ui_labels(self):
        self.assertEqual(
            rule_test_display_values(
                {"match": True, "score": 40, "reason": "AI 사업 발견"}
            ),
            ("일치", "40", "AI 사업 발견"),
        )


if __name__ == "__main__":
    unittest.main()
