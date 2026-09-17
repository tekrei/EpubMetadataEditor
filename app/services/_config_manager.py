import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.config_dir = config_file.parent
        self.data = self._load()

    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load config: {e}")
        return {}

    def save(self, window_state=None):
        if window_state:
            self.data.update(window_state)

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.data, f)
        except OSError as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
