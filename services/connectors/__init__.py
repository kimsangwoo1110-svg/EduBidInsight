"""External data connectors available to EduBid Insight."""

from services.connectors.base import BaseConnector
from services.connectors.contract_import import ContractImportConnector
from services.connectors.schoolmarket_import import SchoolMarketImport
from services.connectors.g2b_import import G2BImport
from services.connectors.education_office_import import EducationOfficeImport
from services.connectors.neis_school import NeisSchoolConnector


__all__ = [
    "BaseConnector",
    "ContractImportConnector",
    "SchoolMarketImport",
    "G2BImport",
    "EducationOfficeImport",
    "NeisSchoolConnector",
]
