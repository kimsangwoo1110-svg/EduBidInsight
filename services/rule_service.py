"""Rule matching and opportunity scoring for school projects."""

import json

from services.database import (
    add_rule,
    delete_rule,
    find_rules,
    update_rule,
    update_rule_enabled,
)


RULE_FIELDS = (
    "id",
    "category",
    "condition",
    "recommendation",
    "score",
    "description",
    "enabled",
)
PROJECT_FIELDS = {
    "project_name",
    "category",
    "status",
    "budget",
    "start_year",
    "end_year",
    "source",
}
CONTRACT_FIELDS = {
    "school_code",
    "school_name",
    "contract_date",
    "product",
    "category",
    "vendor",
    "quantity",
    "amount",
    "source_file",
}
RECORD_FIELDS = PROJECT_FIELDS | CONTRACT_FIELDS
OPERATORS = {"equals", "not_equals", "contains", "in", "gt", "gte", "lt", "lte"}


class RuleService:
    """Manage rules and turn matching rules into ranked sales insights."""

    @classmethod
    def create(
        cls,
        category,
        condition,
        recommendation,
        score,
        description="",
        enabled=True,
    ):
        values = cls._validated_rule_values(
            category, condition, recommendation, score, description, enabled
        )
        return add_rule(
            values["category"],
            values["condition"],
            values["recommendation"],
            values["score"],
            values["description"],
            values["enabled"],
        )

    @staticmethod
    def list(enabled_only=False):
        return [dict(zip(RULE_FIELDS, row)) for row in find_rules(enabled_only)]

    @staticmethod
    def set_enabled(rule_id, enabled):
        return update_rule_enabled(rule_id, enabled)

    @classmethod
    def update(
        cls,
        rule_id,
        category,
        condition,
        recommendation,
        score,
        description="",
        enabled=True,
    ):
        values = cls._validated_rule_values(
            category, condition, recommendation, score, description, enabled
        )
        return update_rule(
            rule_id,
            values["category"],
            values["condition"],
            values["recommendation"],
            values["score"],
            values["description"],
            values["enabled"],
        )

    @staticmethod
    def delete(rule_id):
        return delete_rule(rule_id)

    @classmethod
    def duplicate(cls, rule_id):
        rule = cls.get(rule_id)
        if rule is None:
            raise ValueError("rule not found")
        return cls.create(
            rule["category"],
            rule["condition"],
            f"{rule['recommendation']} (복사본)",
            rule["score"],
            rule["description"],
            rule["enabled"],
        )

    @classmethod
    def get(cls, rule_id):
        return next((rule for rule in cls.list() if rule["id"] == rule_id), None)

    @classmethod
    def validate_condition(cls, condition):
        """Validate condition JSON and return its normalized object form."""
        parsed_condition = cls._parse_condition(condition)
        cls._validate_condition(parsed_condition)
        return parsed_condition

    @classmethod
    def format_condition(cls, condition):
        parsed_condition = cls.validate_condition(condition)
        return json.dumps(parsed_condition, ensure_ascii=False, indent=2)

    @classmethod
    def matches(cls, project, condition):
        """Return whether one project satisfies a validated JSON condition."""
        parsed_condition = cls._parse_condition(condition)
        cls._validate_condition(parsed_condition)
        return cls._evaluate_node(project, parsed_condition)

    @classmethod
    def evaluate_project(cls, project, rules=None):
        """Aggregate all enabled matching rules into one project opportunity."""
        candidate_rules = cls.list(enabled_only=True) if rules is None else rules
        matched_rules = []
        for rule in candidate_rules:
            if not bool(rule.get("enabled", True)):
                continue
            try:
                is_match = cls.matches(project, rule["condition"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                # One malformed stored rule must not prevent other insights.
                continue
            if is_match:
                matched_rules.append(rule)

        if not matched_rules:
            return None

        score = sum(max(0, int(rule.get("score") or 0)) for rule in matched_rules)
        recommendations = list(
            dict.fromkeys(rule["recommendation"] for rule in matched_rules)
        )
        reasons = list(
            dict.fromkeys(
                rule.get("description") or f"{rule['category']} 규칙 일치"
                for rule in matched_rules
            )
        )
        target_name = project.get("project_name") or project.get("product", "")
        target_type = "contract" if "product" in project else "project"
        return {
            "project_id": project.get("id"),
            "project_name": target_name,
            "target_type": target_type,
            "recommendation": " / ".join(recommendations),
            "score": score,
            "reason": " ".join(reasons),
            "priority": cls.priority_for_score(score),
            "matched_rule_ids": [rule.get("id") for rule in matched_rules],
        }

    @classmethod
    def evaluate_projects(cls, projects):
        """Return matched project opportunities, highest score first."""
        rules = cls.list(enabled_only=True)
        insights = [cls.evaluate_project(project, rules) for project in projects]
        matched = [insight for insight in insights if insight is not None]
        return sorted(
            matched,
            key=lambda insight: (-insight["score"], insight["project_name"].casefold()),
        )

    @classmethod
    def evaluate_contracts(cls, contracts):
        """Evaluate imported contracts with the same enabled rule set."""
        rules = cls.list(enabled_only=True)
        insights = [cls.evaluate_project(contract, rules) for contract in contracts]
        matched = [insight for insight in insights if insight is not None]
        return sorted(
            matched,
            key=lambda insight: (-insight["score"], insight["project_name"].casefold()),
        )

    @classmethod
    def test_rule(cls, rule, records):
        """Evaluate one selected rule against a school's projects and contracts."""
        matched_records = [
            record for record in records if cls.matches(record, rule["condition"])
        ]
        if not matched_records:
            reason = (
                "선택한 학교에 등록된 프로젝트 또는 계약이 없습니다."
                if not records
                else "선택한 학교 데이터와 조건이 일치하지 않습니다."
            )
            return {"match": False, "score": 0, "reason": reason}

        record_names = ", ".join(
            str(
                record.get("project_name")
                or record.get("product")
                or "이름 없는 데이터"
            )
            for record in matched_records
        )
        description = rule.get("description") or f"{rule['category']} 규칙 일치"
        return {
            "match": True,
            "score": max(0, int(rule.get("score") or 0)),
            "reason": f"{description} 일치 데이터: {record_names}",
        }

    @staticmethod
    def priority_for_score(score):
        if score >= 70:
            return "높음"
        if score >= 40:
            return "보통"
        return "낮음"

    @staticmethod
    def _parse_condition(condition):
        if isinstance(condition, str):
            return json.loads(condition)
        return condition

    @classmethod
    def _validated_rule_values(
        cls, category, condition, recommendation, score, description, enabled
    ):
        selected_category = str(category or "").strip()
        selected_recommendation = str(recommendation or "").strip()
        if not selected_category:
            raise ValueError("category is required")
        if not selected_recommendation:
            raise ValueError("recommendation is required")
        try:
            numeric_score = int(score)
        except (TypeError, ValueError) as error:
            raise ValueError("score must be an integer") from error
        if numeric_score < 0:
            raise ValueError("score must be zero or greater")

        parsed_condition = cls.validate_condition(condition)
        return {
            "category": selected_category,
            "condition": json.dumps(parsed_condition, ensure_ascii=False),
            "recommendation": selected_recommendation,
            "score": numeric_score,
            "description": str(description or "").strip(),
            "enabled": bool(enabled),
        }

    @classmethod
    def _validate_condition(cls, condition):
        if not isinstance(condition, dict):
            raise ValueError("condition must be a JSON object")

        group_keys = [key for key in ("all", "any") if key in condition]
        if group_keys:
            if len(group_keys) != 1 or len(condition) != 1:
                raise ValueError("condition groups must contain only 'all' or 'any'")
            children = condition[group_keys[0]]
            if not isinstance(children, list) or not children:
                raise ValueError("condition group must contain at least one condition")
            for child in children:
                cls._validate_condition(child)
            return

        required = {"field", "operator", "value"}
        if set(condition) != required:
            raise ValueError("condition requires field, operator, and value")
        if condition["field"] not in RECORD_FIELDS:
            raise ValueError(f"unsupported rule field: {condition['field']}")
        if condition["operator"] not in OPERATORS:
            raise ValueError(f"unsupported operator: {condition['operator']}")
        if condition["operator"] == "in" and not isinstance(condition["value"], list):
            raise ValueError("the 'in' operator requires a list value")

    @classmethod
    def _evaluate_node(cls, project, condition):
        if "all" in condition:
            return all(cls._evaluate_node(project, child) for child in condition["all"])
        if "any" in condition:
            return any(cls._evaluate_node(project, child) for child in condition["any"])

        actual = project.get(condition["field"])
        expected = condition["value"]
        operator = condition["operator"]
        if operator == "equals":
            return cls._normalized(actual) == cls._normalized(expected)
        if operator == "not_equals":
            return cls._normalized(actual) != cls._normalized(expected)
        if operator == "contains":
            return cls._normalized(expected) in cls._normalized(actual)
        if operator == "in":
            return cls._normalized(actual) in {
                cls._normalized(value) for value in expected
            }

        try:
            left = float(actual)
            right = float(expected)
        except (TypeError, ValueError):
            return False
        return {
            "gt": left > right,
            "gte": left >= right,
            "lt": left < right,
            "lte": left <= right,
        }[operator]

    @staticmethod
    def _normalized(value):
        return str(value or "").strip().casefold()
