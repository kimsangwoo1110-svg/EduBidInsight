"""Mock boundary for the future School Market (S2B) integration."""

from connectors.base_connector import ConnectorMetadata, MockConnector


class S2BConnector(MockConnector):
    metadata = ConnectorMetadata(
        key="s2b", name="School Market (S2B)", profile_key="schoolmarket",
        description="Future S2B purchase and contract connector",
    )
