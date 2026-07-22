"""Public connector registry used by application presentation layers."""

from connectors.base_connector import BaseConnector, ConnectorMetadata, MockConnector
from connectors.education_connector import EducationConnector
from connectors.excel_connector import ExcelConnector
from connectors.g2b_connector import G2BConnector
from connectors.s2b_connector import S2BConnector
from connectors.school_info_connector import SchoolInfoConnector


CONNECTOR_TYPES = (
    SchoolInfoConnector,
    EducationConnector,
    S2BConnector,
    G2BConnector,
    ExcelConnector,
)


def connector_catalog():
    """Return fresh connector instances in stable Data Source Manager order."""
    return tuple(connector_type() for connector_type in CONNECTOR_TYPES)


def connector_for_profile(profile_key):
    for connector in connector_catalog():
        if connector.metadata.profile_key == profile_key:
            return connector
    raise KeyError(f"unknown connector profile: {profile_key}")


__all__ = (
    "BaseConnector", "ConnectorMetadata", "MockConnector", "ExcelConnector",
    "SchoolInfoConnector", "S2BConnector", "G2BConnector", "EducationConnector",
    "connector_catalog", "connector_for_profile",
)
