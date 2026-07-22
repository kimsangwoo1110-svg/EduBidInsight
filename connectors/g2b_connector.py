"""Mock boundary for the future NaraJangteo (G2B) integration."""

from connectors.base_connector import ConnectorMetadata, MockConnector


class G2BConnector(MockConnector):
    metadata = ConnectorMetadata(
        key="g2b", name="NaraJangteo (G2B)", profile_key="g2b",
        description="Future G2B notice, award, and contract connector",
    )
