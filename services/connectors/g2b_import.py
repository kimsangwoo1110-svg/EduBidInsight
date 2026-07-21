"""G2B (나라장터) procurement import for the Smart Import Framework."""

import hashlib
import os
import threading

from services import database
from services.base_import import BaseImport
from services.connectors.schoolmarket_import import SchoolMarketImport
from services.contract_service import ContractService
from services.school_service import SchoolService


G2B_COLUMNS = (
    "contract_number",
    "notice_number",
    "school_name",
    "procuring_organization",
    "supplier",
    "product_name",
    "contract_amount",
    "contract_date",
    "category",
)
G2B_REQUIRED_FIELDS = (
    "supplier",
    "product_name",
    "contract_amount",
    "contract_date",
)
G2B_FIELD_LABELS = {
    "contract_number": "계약번호",
    "notice_number": "공고번호",
    "school_name": "학교명",
    "procuring_organization": "수요기관",
    "supplier": "공급업체",
    "product_name": "품명",
    "contract_amount": "계약금액",
    "contract_date": "계약일",
    "category": "분류",
}
G2B_COLUMN_ALIASES = {
    "contract_number": (
        "계약번호", "계약 번호", "계약건번호", "contract number", "contractnumber", "contractno",
    ),
    "notice_number": (
        "공고번호", "입찰공고번호", "공고 번호", "notice number", "noticenumber", "bidno",
    ),
    "school_name": (
        "학교명", "학교", "기관명", "school name", "schoolname",
    ),
    "procuring_organization": (
        "수요기관", "수요기관명", "발주기관", "발주기관명", "procuring organization", "buyer", "agency",
    ),
    "supplier": (
        "공급업체", "계약업체", "낙찰업체", "업체명", "supplier", "vendor", "contractor",
    ),
    "product_name": (
        "품명", "품목명", "물품명", "제품명", "사업명", "product name", "productname", "itemname",
    ),
    "contract_amount": (
        "계약금액", "낙찰금액", "금액", "총액", "contract amount", "contractamount", "amount",
    ),
    "contract_date": (
        "계약일", "계약일자", "낙찰일", "contract date", "contractdate", "awarddate",
    ),
    "category": ("분류", "카테고리", "품목분류", "category", "classification"),
}

# Ordered, data-only rules make future expansion possible without changing the classifier.
G2B_CATEGORY_RULES = (
    ("Network", ("network", "router", "switch", "firewall", "네트워크", "라우터", "스위치", "방화벽", "통신장비")),
    ("Software", ("software", "license", "platform", "소프트웨어", "라이선스", "플랫폼")),
    ("ICT", ("ict", "notebook", "laptop", "tablet", "desktop", "computer", "정보통신", "전산", "노트북", "태블릿", "컴퓨터", "전자칠판")),
    ("Display", ("display", "monitor", "projector", "디스플레이", "모니터", "프로젝터", "영상장비")),
    ("Furniture", ("desk", "chair", "cabinet", "furniture", "책상", "의자", "캐비닛", "가구")),
)


def classify_g2b_product(product_name, source_category=""):
    """Classify a G2B item with ordered, extensible keyword rules."""
    normalized = " ".join(
        f"{source_category or ''} {product_name or ''}".casefold().split()
    )
    for category, terms in G2B_CATEGORY_RULES:
        if any(term in normalized for term in terms):
            return category
    return "Other"


class G2BImport(SchoolMarketImport):
    """Import G2B contracts using the shared transactional import lifecycle."""

    source = "G2B"

    def __init__(
        self,
        filename,
        sheet_name=None,
        mapping=None,
        history_service=None,
        cancel_event=None,
    ):
        BaseImport.__init__(self, self.source, filename, history_service)
        self.extension = os.path.splitext(self.filename)[1].lower()
        if self.extension not in {".xlsx", ".csv"}:
            raise ValueError("only .xlsx and .csv G2B files are supported")
        if not os.path.isfile(self.filename):
            raise ValueError("G2B file does not exist")
        sheets = self.sheet_names(self.filename)
        self.sheet_name = sheet_name or sheets[0]
        headers = self.headers(self.filename, self.sheet_name)
        self.mapping = mapping or self.auto_map(headers)
        self.validate_mapping(self.mapping, headers)
        self.cancel_event = cancel_event or threading.Event()
        self._loaded = None

    def _transform(self, source_row):
        values = {
            field: source_row.get(header, "") if header else ""
            for field, header in self.mapping.items()
        }
        organization = str(values.get("procuring_organization") or "").strip()
        school_name = str(values.get("school_name") or "").strip() or organization
        purchase = {
            "contract_number": str(values.get("contract_number") or "").strip(),
            "notice_number": str(values.get("notice_number") or "").strip(),
            "procuring_organization": organization,
            "school_name": school_name,
            "contract_date": ContractService.normalize_date(values.get("contract_date")),
            "product": str(values.get("product_name") or "").strip(),
            "vendor": str(values.get("supplier") or "").strip(),
            "quantity": 0,
            "amount": ContractService.normalize_amount(values.get("contract_amount")),
        }
        purchase["category"] = classify_g2b_product(
            purchase["product"], values.get("category")
        )
        missing = [
            field for field in ("school_name", "contract_date", "product", "vendor", "amount")
            if purchase.get(field) in (None, "")
        ]
        if missing:
            raise ValueError(f"required fields are missing: {', '.join(missing)}")
        return purchase

    def _raw_contract(self, source_row):
        values = {
            field: source_row.get(header, "") if header else ""
            for field, header in self.mapping.items()
        }
        product = str(values.get("product_name") or "").strip()
        return {
            "school_name": str(values.get("school_name") or "").strip()
            or str(values.get("procuring_organization") or "").strip(),
            "contract_date": values.get("contract_date", ""),
            "product": product,
            "vendor": values.get("supplier", ""),
            "quantity": 0,
            "amount": values.get("contract_amount", ""),
            "category": classify_g2b_product(product, values.get("category")),
        }

    def _save_purchase(self, row, result, connection):
        purchase = row["purchase"]
        result["school_rows"] += 1
        match = SchoolService.match_name(purchase["school_name"], connection=connection)
        if match:
            result["school_matches"] += 1
            school_code = match["school_code"]
            school_name = match["school_name"]
        else:
            school_name = purchase["school_name"]
            school_code = self._unmatched_school_code(school_name)
            result["warnings"].append(
                f"Row {row['row_number']}: school not matched: {school_name}"
            )
        contract = ContractService.validate(
            {
                "school_code": school_code,
                "school_name": school_name,
                "contract_date": purchase["contract_date"],
                "product": purchase["product"],
                "category": purchase["category"],
                "vendor": purchase["vendor"],
                "quantity": 0,
                "amount": purchase["amount"],
                "source_file": os.path.basename(self.filename),
            }
        )
        record_key = self._record_key(purchase, contract)
        duplicate = database.g2b_key_exists(record_key, connection=connection)
        if not purchase["contract_number"] and not purchase["notice_number"] and not duplicate:
            duplicate = database.contract_duplicate_exists(contract, connection=connection)
        if duplicate:
            result["duplicates"] += 1
            return
        contract_id = database.add_contract(contract, connection=connection, commit=False)
        database.add_g2b_key(
            record_key,
            purchase["contract_number"],
            purchase["notice_number"],
            contract_id,
            connection,
        )
        result["imported"] += 1
        result["category_summary"][purchase["category"]] += 1

    @staticmethod
    def _record_key(purchase, contract):
        contract_number = G2BImport._identity(purchase["contract_number"])
        if contract_number:
            return f"contract:{contract_number}"
        notice_number = G2BImport._identity(purchase["notice_number"])
        if notice_number:
            return f"notice:{notice_number}"
        composite = "|".join(
            str(contract.get(field, "")).strip().casefold()
            for field in ("school_code", "contract_date", "product", "vendor", "amount")
        )
        return "composite:" + hashlib.sha256(composite.encode("utf-8")).hexdigest()

    @classmethod
    def auto_map(cls, headers):
        normalized = {cls._normalize(header): header for header in headers}
        return {
            field: next(
                (
                    normalized[cls._normalize(alias)]
                    for alias in G2B_COLUMN_ALIASES[field]
                    if cls._normalize(alias) in normalized
                ),
                "",
            )
            for field in G2B_COLUMNS
        }

    @staticmethod
    def validate_mapping(mapping, headers):
        missing = [field for field in G2B_REQUIRED_FIELDS if not mapping.get(field)]
        if not mapping.get("school_name") and not mapping.get("procuring_organization"):
            missing.append("school_name/procuring_organization")
        if missing:
            raise ValueError(f"required column mappings are missing: {', '.join(missing)}")
        invalid = [value for value in mapping.values() if value and value not in set(headers)]
        if invalid:
            raise ValueError(f"mapped columns do not exist: {', '.join(invalid)}")
        selected = [value for value in mapping.values() if value]
        if len(selected) != len(set(selected)):
            raise ValueError("one source column cannot be mapped more than once")
        return True

    @staticmethod
    def _identity(value):
        return "".join(str(value or "").split()).casefold()


class G2BService:
    """Read-only G2B contract identity service."""

    @staticmethod
    def contract_ids_for_school(school_code):
        return database.find_g2b_contract_ids(school_code)


G2BImportConnector = G2BImport
