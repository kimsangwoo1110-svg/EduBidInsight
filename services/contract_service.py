"""Contract validation, persistence, duplicate detection, and search."""

from datetime import date, datetime

from services.database import (
    add_contract,
    contract_duplicate_exists,
    find_contracts,
    update_contract,
)


CONTRACT_FIELDS = (
    "id",
    "school_code",
    "school_name",
    "contract_date",
    "product",
    "category",
    "vendor",
    "quantity",
    "amount",
    "source_file",
    "imported_at",
    "updated_at",
)
REQUIRED_FIELDS = (
    "school_code",
    "school_name",
    "contract_date",
    "product",
    "vendor",
    "amount",
)


class ContractService:
    """Service boundary for imported education contracts."""

    @classmethod
    def save(cls, connection=None, commit=True, **values):
        contract = cls.validate(values)
        if cls.duplicate_check(connection=connection, **contract):
            return None
        return add_contract(contract, connection=connection, commit=commit)

    @classmethod
    def update(cls, contract_id, **values):
        contract = cls.validate(values)
        if cls.duplicate_check(exclude_id=contract_id, **contract):
            raise ValueError("duplicate contract")
        return update_contract(contract_id, contract)

    @staticmethod
    def search(keyword="", limit=None):
        return ContractService._rows(find_contracts(keyword=keyword, limit=limit))

    @staticmethod
    def search_by_school(school_code, limit=None):
        return ContractService._rows(
            find_contracts(school_code=school_code, limit=limit)
        )

    @staticmethod
    def search_by_vendor(vendor, limit=None):
        return ContractService._rows(find_contracts(vendor=vendor, limit=limit))

    @staticmethod
    def search_by_product(product, limit=None):
        return ContractService._rows(find_contracts(product=product, limit=limit))

    @staticmethod
    def recent_contracts(limit=50):
        return ContractService._rows(find_contracts(limit=limit))

    @staticmethod
    def duplicate_check(exclude_id=None, connection=None, **values):
        contract = ContractService.validate(values)
        return contract_duplicate_exists(
            contract, exclude_id=exclude_id, connection=connection
        )

    @classmethod
    def validate(cls, values):
        contract = {
            "school_code": cls._text(values.get("school_code")),
            "school_name": cls._text(values.get("school_name")),
            "contract_date": cls.normalize_date(values.get("contract_date")),
            "product": cls._text(values.get("product")),
            "category": cls._text(values.get("category")),
            "vendor": cls._text(values.get("vendor")),
            "quantity": cls.normalize_quantity(values.get("quantity", 0)),
            "amount": cls.normalize_amount(values.get("amount")),
            "source_file": cls._text(values.get("source_file")),
        }
        missing = [field for field in REQUIRED_FIELDS if contract[field] in (None, "")]
        if missing:
            raise ValueError(f"required fields are missing: {', '.join(missing)}")
        return contract

    @staticmethod
    def normalize_date(value):
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        text = str(value or "").strip()
        if not text:
            return ""
        for pattern in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(text, pattern).date().isoformat()
            except ValueError:
                continue
        raise ValueError(f"invalid contract date: {value}")

    @staticmethod
    def normalize_amount(value):
        text = str(value if value is not None else "").strip()
        if not text:
            return None
        try:
            amount = float(
                text.replace(",", "").replace("원", "").replace("₩", "").strip()
            )
        except ValueError as error:
            raise ValueError(f"invalid amount: {value}") from error
        if amount < 0:
            raise ValueError("amount must be zero or greater")
        return amount

    @staticmethod
    def normalize_quantity(value):
        text = str(value if value is not None else "").strip()
        if not text:
            return 0
        try:
            number = float(text.replace(",", ""))
        except ValueError as error:
            raise ValueError(f"invalid quantity: {value}") from error
        if number < 0 or not number.is_integer():
            raise ValueError("quantity must be a non-negative integer")
        return int(number)

    @staticmethod
    def format_amount(amount):
        return f"{int(float(amount or 0)):,}원"

    @staticmethod
    def _rows(rows):
        return [dict(zip(CONTRACT_FIELDS, row)) for row in rows]

    @staticmethod
    def _text(value):
        return str(value or "").strip()
