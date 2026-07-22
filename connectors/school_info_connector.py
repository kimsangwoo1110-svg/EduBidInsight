"""Mock boundary for the future School Info OpenAPI integration."""

from connectors.base_connector import ConnectorMetadata, MockConnector


class SchoolInfoConnector(MockConnector):
    metadata = ConnectorMetadata(
        key="school_info", name="School Info OpenAPI", profile_key="school",
        description="Future school master-data OpenAPI connector",
    )
