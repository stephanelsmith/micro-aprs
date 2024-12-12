# backend/config_manager.py

import json
import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "frequency_hz": 50.01e6,
    "gain": 14,
    "if_gain": 47,
    "callsign_source": "VE2FPD",
    "callsign_dest": "VE2FPD-2",
    "flags_before": 10,
    "flags_after": 4,
    "send_ip": "127.0.0.1",
    "send_port": 14581,
    "carrier_only": False,
    "device_index": 0
}

class ConfigurationManager:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from a JSON file or return default configuration.
        """
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                config = json.load(f)
            logger.info("Configuration loaded from %s.", self.config_file)
            return config
        else:
            logger.warning("Config file not found. Using default configuration.")
            return DEFAULT_CONFIG.copy()

    def save_config(self) -> None:
        """
        Save current configuration to a JSON file.
        """
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)
        logger.info("Configuration saved to %s.", self.config_file)

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
