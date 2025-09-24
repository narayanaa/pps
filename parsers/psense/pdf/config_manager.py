import json
from typing import Dict, Any


class ConfigManager:
    def __init__(self, config_file: str):
        self.config = self.load_config(config_file)

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Loads configuration from a JSON file."""
        with open(config_file, "r") as f:
            return json.load(f)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a specific configuration setting, or returns default."""
        return self.config.get(key, default)

