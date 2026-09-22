"""Compatibility entrypoint for the ingestion service.

This module now runs the unified ingestion service that supports:
- MQTT ingestion mode
- Dataset replay mode
"""

from services.ingestion.service import main


if __name__ == "__main__":
	main()
