import os
import tempfile
import unittest
from contextlib import closing

from services import database
from services.rule_service import RuleService


class RuleServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "rules.db")
        database.create_database()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def clear_rules(self):
        with closing(database.get_connection()) as connection, connection:
            connection.execute("DELETE FROM rules")

    def test_database_creates_rules_table_and_default_rules(self):
        with closing(database.get_connection()) as connection:
            columns = [
                row[1] for row in connection.execute("PRAGMA table_info(rules)")
            ]
            rule_count = connection.execute("SELECT COUNT(*) FROM rules").fetchone()[0]

        self.assertEqual(
            columns,
            [
                "id",
                "category",
                "condition",
                "recommendation",
                "score",
                "description",
                "enabled",
            ],
        )
        self.assertEqual(rule_count, 4)

        self.clear_rules()
        database.create_database()
        self.assertEqual(RuleService.list(), [])

    def test_matching_rules_are_scored_and_disabled_rules_are_ignored(self):
        self.clear_rules()
        ai_rule_id = RuleService.create(
            "AI",
            {"field": "category", "operator": "contains", "value": "ai"},
            "AI 솔루션 제안",
            40,
            "AI 분류 일치",
        )
        status_rule_id = RuleService.create(
            "단계",
            {"field": "status", "operator": "in", "value": ["예정", "진행중"]},
            "담당자 접촉",
            20,
            "제안 가능 단계",
        )
        budget_rule_id = RuleService.create(
            "예산",
            {"field": "budget", "operator": "gte", "value": 100_000_000},
            "대형 사업 제안",
            15,
            "1억원 이상",
        )
        disabled_rule_id = RuleService.create(
            "비활성",
            {"field": "status", "operator": "equals", "value": "예정"},
            "표시되면 안 됨",
            100,
            enabled=False,
        )

        insight = RuleService.evaluate_project(
            {
                "id": 1,
                "project_name": "AI 교실 구축",
                "category": "AI 교육",
                "status": "예정",
                "budget": 150_000_000,
            }
        )

        self.assertEqual(insight["score"], 75)
        self.assertEqual(insight["priority"], "높음")
        self.assertEqual(
            insight["matched_rule_ids"],
            [ai_rule_id, status_rule_id, budget_rule_id],
        )
        self.assertNotIn(disabled_rule_id, insight["matched_rule_ids"])
        self.assertIn("AI 솔루션 제안", insight["recommendation"])
        self.assertIn("1억원 이상", insight["reason"])

    def test_nested_conditions_and_priority_boundaries(self):
        condition = {
            "all": [
                {
                    "any": [
                        {"field": "category", "operator": "equals", "value": "공간혁신"},
                        {"field": "project_name", "operator": "contains", "value": "공간"},
                    ]
                },
                {"field": "budget", "operator": "lt", "value": 100_000_000},
            ]
        }
        project = {
            "project_name": "미래형 공간 구축",
            "category": "환경개선",
            "budget": 80_000_000,
        }

        self.assertTrue(RuleService.matches(project, condition))
        self.assertEqual(RuleService.priority_for_score(39), "낮음")
        self.assertEqual(RuleService.priority_for_score(40), "보통")
        self.assertEqual(RuleService.priority_for_score(70), "높음")

    def test_unmatched_projects_are_not_returned(self):
        self.clear_rules()
        RuleService.create(
            "AI",
            {"field": "category", "operator": "equals", "value": "AI 교육"},
            "AI 제안",
            40,
        )
        projects = [
            {"project_name": "체육관 보수", "category": "시설", "status": "완료"}
        ]

        self.assertEqual(RuleService.evaluate_projects(projects), [])

    def test_rule_crud_duplicate_and_enable_toggle(self):
        self.clear_rules()
        rule_id = RuleService.create(
            "시설",
            {"field": "category", "operator": "equals", "value": "시설"},
            "시설 제안",
            30,
            "최초 설명",
        )

        self.assertTrue(
            RuleService.update(
                rule_id,
                "시설 개선",
                {"field": "budget", "operator": "gte", "value": 50_000_000},
                "시설 개선 제안",
                45,
                "수정 설명",
                False,
            )
        )
        updated = RuleService.get(rule_id)
        self.assertEqual(updated["category"], "시설 개선")
        self.assertEqual(updated["score"], 45)
        self.assertEqual(updated["enabled"], 0)

        duplicate_id = RuleService.duplicate(rule_id)
        duplicate = RuleService.get(duplicate_id)
        self.assertEqual(duplicate["recommendation"], "시설 개선 제안 (복사본)")
        self.assertEqual(duplicate["condition"], updated["condition"])

        self.assertTrue(RuleService.set_enabled(duplicate_id, True))
        self.assertEqual(RuleService.get(duplicate_id)["enabled"], 1)
        self.assertTrue(RuleService.delete(rule_id))
        self.assertIsNone(RuleService.get(rule_id))

    def test_json_validation_rejects_invalid_conditions(self):
        with self.assertRaises(ValueError):
            RuleService.validate_condition("not-json")
        with self.assertRaises(ValueError):
            RuleService.validate_condition(
                {"field": "unknown", "operator": "equals", "value": "x"}
            )
        with self.assertRaises(ValueError):
            RuleService.validate_condition(
                {"field": "status", "operator": "in", "value": "예정"}
            )

    def test_single_rule_test_reports_match_score_and_reason(self):
        rule = {
            "id": 1,
            "category": "AI",
            "condition": '{"field":"category","operator":"contains","value":"AI"}',
            "recommendation": "AI 제안",
            "score": 40,
            "description": "AI 사업 발견",
            "enabled": 0,
        }
        projects = [
            {"project_name": "AI 교실 구축", "category": "AI 교육"},
            {"project_name": "체육관 보수", "category": "시설"},
        ]

        result = RuleService.test_rule(rule, projects)

        self.assertTrue(result["match"])
        self.assertEqual(result["score"], 40)
        self.assertIn("AI 교실 구축", result["reason"])


if __name__ == "__main__":
    unittest.main()
