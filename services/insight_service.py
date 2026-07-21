"""Actionable business intelligence generated from school analytics."""

import json
from datetime import date, datetime

from services.analytics_service import AnalyticsService
from services.contract_service import ContractService
from services.database import add_recommendation_history, find_recommendation_history
from services.project_service import ProjectService


HISTORY_FIELDS = (
    "id",
    "school_code",
    "created_at",
    "score",
    "summary",
    "recommended_products",
    "next_action",
    "risk",
)


class InsightService:
    """Translate analytics into explanations and concrete sales actions."""

    @classmethod
    def summarize_school(cls, school_code, persist=True):
        analytics = AnalyticsService.school_summary(school_code)
        recommendations = cls.recommend_products(school_code, analytics)
        explanation = cls.explain_score(school_code, analytics)
        risks = cls.risk_analysis(school_code, analytics)
        actions = cls.next_sales_action(
            school_code, analytics, recommendations, risks
        )
        summary = cls._summary_text(analytics)
        timeline = cls._opportunity_timeline(school_code, analytics, actions)
        priority_matrix = cls._priority_matrix(analytics, recommendations)
        insight = {
            "school_code": str(school_code or "").strip(),
            "created_at": cls._timestamp(),
            "score": analytics["opportunity"]["score"],
            "summary": summary,
            "recommended_products": recommendations,
            "explanation": explanation,
            "risks": risks,
            "next_actions": actions,
            "opportunity_timeline": timeline,
            "priority_matrix": priority_matrix,
            "analytics": analytics,
            "history_id": None,
        }
        if persist:
            insight["history_id"] = add_recommendation_history(
                insight["school_code"],
                insight["created_at"],
                insight["score"],
                summary,
                json.dumps(recommendations, ensure_ascii=False),
                json.dumps(actions, ensure_ascii=False),
                json.dumps(risks, ensure_ascii=False),
            )
        analytics["business_insight"] = {
            key: value for key, value in insight.items() if key != "analytics"
        }
        return insight

    @classmethod
    def recommend_products(cls, school_code, analytics=None):
        analytics = analytics or AnalyticsService.school_summary(school_code)
        projects = ProjectService.list_for_school(school_code)
        recommendations = []
        seen = set()

        def add(product, reason, confidence):
            key = product.casefold()
            if key not in seen:
                seen.add(key)
                recommendations.append(
                    {
                        "product": product,
                        "reason": reason,
                        "confidence": confidence,
                        "priority": "높음" if confidence >= 80 else "보통",
                    }
                )

        project_text = " ".join(
            f"{project.get('project_name', '')} {project.get('category', '')}"
            for project in projects
        ).casefold()
        for keywords, product, reason, confidence in (
            (("ai", "인공지능"), "AI 교육 솔루션", "AI 관련 프로젝트 수요가 확인됨", 90),
            (("디지털", "스마트"), "스마트기기 및 네트워크", "디지털 교육환경 사업이 확인됨", 85),
            (("공간", "환경개선"), "공간혁신 기자재", "공간·시설 개선 프로젝트가 확인됨", 82),
        ):
            if any(keyword in project_text for keyword in keywords):
                add(product, reason, confidence)

        for product_row in analytics["product_statistics"][:3]:
            confidence = 80 if product_row["count"] >= 2 else 70
            add(
                product_row["product"],
                f"기존 구매 {product_row['count']}건, 구매 비중 {product_row['share']:.1f}%",
                confidence,
            )

        if not recommendations:
            add(
                "학교 교육환경 진단 컨설팅",
                "구매·프로젝트 데이터가 부족해 수요 발굴이 우선임",
                55,
            )
        return recommendations[:5]

    @staticmethod
    def explain_score(school_code, analytics=None):
        analytics = analytics or AnalyticsService.school_summary(school_code)
        opportunity = analytics["opportunity"]
        factors = []
        if opportunity["opportunity_count"]:
            factors.append(
                f"활성 규칙과 일치한 영업 기회 {opportunity['opportunity_count']}건"
            )
        if opportunity["high_priority_count"]:
            factors.append(
                f"높은 우선순위 기회 {opportunity['high_priority_count']}건"
            )
        if analytics["project_summary"]["status_counts"]["예정"]:
            factors.append(
                f"예정 프로젝트 {analytics['project_summary']['status_counts']['예정']}건"
            )
        if analytics["contract_summary"]["total_count"]:
            factors.append(
                f"누적 계약 {analytics['contract_summary']['total_count']}건"
            )
        if not factors:
            factors.append("점수를 산출할 프로젝트·계약 규칙 일치 데이터가 없음")
        return {
            "score": opportunity["score"],
            "priority": opportunity["priority"],
            "factors": factors,
            "text": f"Opportunity Score {opportunity['score']}점: " + " · ".join(factors),
        }

    @classmethod
    def next_sales_action(
        cls, school_code, analytics=None, recommendations=None, risks=None
    ):
        analytics = analytics or AnalyticsService.school_summary(school_code)
        recommendations = recommendations or cls.recommend_products(school_code, analytics)
        risks = risks or cls.risk_analysis(school_code, analytics)
        score = analytics["opportunity"]["score"]
        if score >= 70:
            timing = "3일 이내"
            first_action = "학교 담당자에게 우선 연락하고 제안 일정을 확정"
        elif score >= 40:
            timing = "7일 이내"
            first_action = "담당자와 수요 확인 미팅을 제안"
        else:
            timing = "30일 이내"
            first_action = "학교 현황과 예산 편성 정보를 추가 조사"
        actions = [
            {
                "order": 1,
                "timing": timing,
                "action": first_action,
                "reason": f"현재 Opportunity Score {score}점",
            }
        ]
        if recommendations:
            actions.append(
                {
                    "order": 2,
                    "timing": "첫 접촉 전",
                    "action": f"'{recommendations[0]['product']}' 맞춤 제안서 준비",
                    "reason": recommendations[0]["reason"],
                }
            )
        actionable_risk = next((risk for risk in risks if risk["level"] != "낮음"), None)
        if actionable_risk:
            actions.append(
                {
                    "order": 3,
                    "timing": "제안 검토 시",
                    "action": actionable_risk["mitigation"],
                    "reason": actionable_risk["risk"],
                }
            )
        return actions

    @staticmethod
    def risk_analysis(school_code, analytics=None, today=None):
        analytics = analytics or AnalyticsService.school_summary(school_code)
        today = today or date.today()
        risks = []
        if not analytics["kpis"]["projects"] and not analytics["kpis"]["contracts"]:
            risks.append(
                {
                    "level": "높음",
                    "risk": "분석 가능한 학교 데이터 부족",
                    "mitigation": "프로젝트·계약 원천 데이터를 먼저 확보",
                }
            )
        vendors = analytics["vendor_statistics"]
        if vendors and vendors[0]["share"] >= 70:
            risks.append(
                {
                    "level": "높음" if vendors[0]["share"] >= 85 else "보통",
                    "risk": f"특정 업체 구매 집중도 {vendors[0]['share']:.1f}%",
                    "mitigation": "기존 업체 대비 차별화 요소와 전환 비용을 제시",
                }
            )
        next_expected = analytics["purchase_cycle"]["next_expected_date"]
        if next_expected and date.fromisoformat(next_expected) < today:
            risks.append(
                {
                    "level": "보통",
                    "risk": "예상 구매 시점이 경과함",
                    "mitigation": "구매 완료 여부와 차기 예산 일정을 즉시 확인",
                }
            )
        if analytics["opportunity"]["opportunity_count"] == 0:
            risks.append(
                {
                    "level": "보통",
                    "risk": "활성 규칙과 일치하는 영업 기회 없음",
                    "mitigation": "규칙 조건을 검토하고 학교 수요 인터뷰를 진행",
                }
            )
        if not risks:
            risks.append(
                {
                    "level": "낮음",
                    "risk": "현재 데이터에서 중대한 영업 위험이 발견되지 않음",
                    "mitigation": "정기적으로 프로젝트와 계약 데이터를 갱신",
                }
            )
        return risks

    @staticmethod
    def history(school_code, limit=20):
        history = []
        for row in find_recommendation_history(school_code, limit):
            item = dict(zip(HISTORY_FIELDS, row))
            for field in ("recommended_products", "next_action", "risk"):
                try:
                    item[field] = json.loads(item[field])
                except (TypeError, json.JSONDecodeError):
                    item[field] = []
            history.append(item)
        return history

    @staticmethod
    def _summary_text(analytics):
        kpis = analytics["kpis"]
        cycle = analytics["purchase_cycle"]
        cycle_text = (
            f"평균 구매 주기는 {cycle['average_days']:.1f}일입니다."
            if cycle["average_days"] is not None
            else "구매 주기를 판단할 데이터가 부족합니다."
        )
        return (
            f"프로젝트 {kpis['projects']}건, 계약 {kpis['contracts']}건, "
            f"거래 업체 {kpis['vendors']}개가 확인되었습니다. "
            f"Opportunity Score는 {kpis['opportunity_score']}점이며, {cycle_text}"
        )

    @staticmethod
    def _opportunity_timeline(school_code, analytics, actions):
        events = []
        for contract in ContractService.search_by_school(school_code)[:5]:
            events.append(
                {
                    "date": contract["contract_date"],
                    "type": "계약",
                    "title": contract["product"],
                    "detail": f"{contract['vendor']} · {ContractService.format_amount(contract['amount'])}",
                }
            )
        for project in ProjectService.list_for_school(school_code):
            if project.get("start_year"):
                events.append(
                    {
                        "date": f"{project['start_year']}-01-01",
                        "type": "프로젝트",
                        "title": project["project_name"],
                        "detail": project.get("status") or "-",
                    }
                )
        next_expected = analytics["purchase_cycle"]["next_expected_date"]
        if next_expected:
            events.append(
                {
                    "date": next_expected,
                    "type": "예상",
                    "title": "다음 구매 예상 시점",
                    "detail": actions[0]["action"] if actions else "영업 준비",
                }
            )
        return sorted(events, key=lambda event: (event["date"], event["type"]))

    @staticmethod
    def _priority_matrix(analytics, recommendations):
        next_expected = analytics["purchase_cycle"]["next_expected_date"]
        urgent = (
            analytics["opportunity"]["score"] >= 70
            or (next_expected and date.fromisoformat(next_expected) <= date.today())
        )
        rows = []
        for recommendation in recommendations:
            high_impact = recommendation["confidence"] >= 80
            if high_impact and urgent:
                quadrant = "즉시 실행"
            elif high_impact:
                quadrant = "전략 추진"
            elif urgent:
                quadrant = "빠른 대응"
            else:
                quadrant = "관찰"
            rows.append(
                {
                    "item": recommendation["product"],
                    "impact": "높음" if high_impact else "보통",
                    "urgency": "높음" if urgent else "보통",
                    "quadrant": quadrant,
                    "reason": recommendation["reason"],
                }
            )
        return rows

    @staticmethod
    def _timestamp():
        return datetime.now().astimezone().isoformat(timespec="seconds")
