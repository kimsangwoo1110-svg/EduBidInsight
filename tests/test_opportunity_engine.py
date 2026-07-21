import os
import tempfile
import unittest
from datetime import date

from services import database
from services.opportunity_engine import OpportunityEngine, OpportunityResult
from services.project_service import ProjectService
from services.school_profile_service import SchoolProfileService
from services.school_service import SchoolService


class OpportunityEngineTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "opportunities.db")
        database.create_database()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    @staticmethod
    def full_signal_profile():
        return {
            "school": {"school_code": "S-OPP", "school_name": "기회학교"},
            "analytics": {
                "project_analytics": {
                    "budget_trends": [{"year": 2026, "budget": 200_000_000}]
                }
            },
            "opportunity_context": {
                "projects": [
                    {
                        "id": 1, "project_name": "AI Education", "category": "AI Education",
                        "status": "진행중", "budget": 100_000_000,
                        "updated_at": "2026-07-01", "end_year": 2026,
                    },
                    {
                        "id": 2, "project_name": "Space Innovation", "category": "Space Innovation",
                        "status": "완료", "budget": 50_000_000,
                        "updated_at": "2026-06-15", "end_year": 2026,
                    },
                    {
                        "id": 3, "project_name": "Smart Classroom", "category": "Smart Classroom",
                        "status": "예정", "budget": 50_000_000,
                        "updated_at": "2026-07-10", "end_year": 2026,
                    },
                ],
                "contracts": [
                    {
                        "id": 10, "source_type": "SchoolMarket", "category": "ICT",
                        "product": "Tablet", "contract_date": "2026-07-01",
                    },
                    {
                        "id": 11, "source_type": "G2B", "category": "Network",
                        "product": "Switch", "contract_date": "2026-06-01",
                    },
                    {
                        "id": 12, "source_type": "Contract", "category": "Other",
                        "product": "Annual service", "contract_date": "2025-07-21",
                    },
                ],
                "crm_activities": [{"activity_date": "2025-10-01"}],
            },
        }

    def test_score_calculation_cap_confidence_and_evidence(self):
        result = OpportunityEngine.evaluate_profile(
            self.full_signal_profile(), today=date(2026, 7, 21)
        )

        self.assertIsInstance(result, OpportunityResult)
        self.assertEqual(result.school_id, "S-OPP")
        self.assertEqual(result.score, 100)
        self.assertEqual(result.priority, "★★★★★")
        self.assertEqual(result.confidence, "High")
        self.assertEqual(len(result.evidence), 9)
        self.assertIn("✓ AI Education Project", result.evidence)
        self.assertIn("✓ Recent G2B Contract", result.evidence)
        self.assertIn("✓ Contract Renewal Window", result.evidence)
        self.assertIn("✓ Large Annual Project Budget", result.evidence)

    def test_priority_mapping_boundaries(self):
        self.assertEqual(OpportunityEngine.priority(100), "★★★★★")
        self.assertEqual(OpportunityEngine.priority(90), "★★★★★")
        self.assertEqual(OpportunityEngine.priority(89), "★★★★☆")
        self.assertEqual(OpportunityEngine.priority(70), "★★★★☆")
        self.assertEqual(OpportunityEngine.priority(69), "★★★☆☆")
        self.assertEqual(OpportunityEngine.priority(50), "★★★☆☆")
        self.assertEqual(OpportunityEngine.priority(49), "★★☆☆☆")

    def test_recommendation_and_next_action_generation(self):
        ai = ["✓ AI Education Project"]
        display = ["✓ Recent ICT Purchase"]
        crm = ["✓ No CRM activity in 8 months"]
        renewal = ["✓ Contract Renewal Window"]

        self.assertEqual(
            OpportunityEngine.recommendation(ai), "Recommend AI Classroom proposal."
        )
        self.assertEqual(
            OpportunityEngine.recommendation(display), "Recommend Interactive Display."
        )
        self.assertEqual(
            OpportunityEngine.recommendation(crm), "Recommend Follow-up Visit."
        )
        self.assertEqual(OpportunityEngine.next_action(crm), "Visit this week")
        self.assertEqual(OpportunityEngine.next_action(renewal), "Prepare quotation")
        self.assertEqual(OpportunityEngine.next_action(ai), "Call next Monday")

    def test_configurable_weights(self):
        profile = self.full_signal_profile()
        result = OpportunityEngine.evaluate_profile(
            profile,
            weights={
                "ai_education_project": 7,
                "space_innovation": 0,
                "smart_classroom": 0,
                "recent_ict_purchase": 0,
                "recent_g2b_contract": 0,
                "crm_inactive": 0,
                "contract_renewal": 0,
                "large_annual_budget": 0,
                "recent_project_completion": 0,
            },
            today=date(2026, 7, 21),
        )

        self.assertEqual(result.score, 7)

    def test_school360_profile_contains_generated_opportunity(self):
        SchoolService.save(
            "S360-OPP", "추천학교", "서울교육청", "서울", "초등학교", "서울"
        )
        ProjectService.create(
            "S360-OPP", "AI Education 구축", "AI Education", "진행중", 150_000_000, 2026, 2026
        )

        profile = SchoolProfileService.get_profile("S360-OPP")

        self.assertIsInstance(profile["opportunity"], OpportunityResult)
        self.assertGreaterEqual(profile["opportunity"].score, 40)
        self.assertIn("AI Classroom", profile["opportunity"].recommendation)
        self.assertTrue(profile["opportunity"].evidence)

    def test_dashboard_ranks_top_schools_and_highest_scores(self):
        SchoolService.save("A", "Alpha School", "Office", "서울", "초등학교", "주소")
        SchoolService.save("B", "Beta School", "Office", "서울", "초등학교", "주소")
        ProjectService.create(
            "B", "AI Education", "AI Education", "진행중", 120_000_000, 2026, 2026
        )

        dashboard = OpportunityEngine.dashboard(
            limit=20, today=date(2026, 7, 21), persist=False
        )

        self.assertEqual(dashboard["top_opportunities"][0].school_id, "B")
        self.assertEqual(dashboard["highest_scores"][0].school_name, "Beta School")
        self.assertLessEqual(len(dashboard["top_opportunities"]), 20)

    def test_recently_increased_scores_uses_dedicated_history(self):
        old = OpportunityResult(
            "S-UP", "상승학교", 40, "★★☆☆☆", "Monitor school opportunity.",
            "Monitor project", "Low", [], "2026-07-20T10:00:00+09:00",
        )
        new = OpportunityResult(
            "S-UP", "상승학교", 70, "★★★★☆", "Recommend AI Classroom proposal.",
            "Call next Monday", "Medium", ["✓ AI Education Project"],
            "2026-07-21T10:00:00+09:00",
        )
        OpportunityEngine.save(old)
        OpportunityEngine.save(new)

        increased = OpportunityEngine.recently_increased()

        self.assertEqual(increased[0]["school_id"], "S-UP")
        self.assertEqual(increased[0]["score"], 70)
        self.assertEqual(increased[0]["increase"], 30)

    def test_cached_dashboard_uses_latest_persisted_snapshot(self):
        old = OpportunityResult(
            "CACHE", "Cached School", 45, "★★☆☆☆", "Monitor school opportunity.",
            "Monitor project", "Low", [], "2026-07-20T10:00:00+09:00",
        )
        latest = OpportunityResult(
            "CACHE", "Cached School", 85, "★★★★☆", "Recommend AI Classroom proposal.",
            "Visit this week", "Medium", ["✓ AI Education Project"],
            "2026-07-21T10:00:00+09:00",
        )
        OpportunityEngine.save(old)
        OpportunityEngine.save(latest)

        dashboard = OpportunityEngine.dashboard(cached_only=True, persist=False)

        self.assertEqual(len(dashboard["all_opportunities"]), 1)
        self.assertEqual(dashboard["top_opportunities"][0].score, 85)


if __name__ == "__main__":
    unittest.main()
