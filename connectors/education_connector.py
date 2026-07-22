"""Mock boundary for future Education Office data integration."""

from connectors.base_connector import ConnectorMetadata, MockConnector


class EducationConnector(MockConnector):
    metadata = ConnectorMetadata(
        key="education_office", name="Education Office", profile_key="education_office",
        description="Future regional Education Office project connector",
    )
