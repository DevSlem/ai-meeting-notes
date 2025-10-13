"""Configuration and secure storage for API keys."""

import os
from pathlib import Path
from typing import Optional


class SecureConfig:
    """Handle secure storage of API keys and configuration."""

    def __init__(self, config_dir: str = ".config"):
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "api_key.txt")
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        os.makedirs(self.config_dir, exist_ok=True)

        # Set restrictive permissions on config directory (Unix-like systems)
        if os.name != 'nt':  # Not Windows
            try:
                os.chmod(self.config_dir, 0o700)  # rwx------
            except Exception:
                pass

    def save_api_key(self, api_key: str) -> bool:
        """
        Save API key to secure config file.

        Args:
            api_key: The API key to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Write API key to file
            with open(self.config_file, 'w') as f:
                f.write(api_key)

            # Set restrictive permissions on the file (Unix-like systems)
            if os.name != 'nt':  # Not Windows
                try:
                    os.chmod(self.config_file, 0o600)  # rw-------
                except Exception:
                    pass

            return True

        except Exception as e:
            print(f"Error saving API key: {e}")
            return False

    def load_api_key(self) -> Optional[str]:
        """
        Load API key from secure config file.

        Returns:
            Optional[str]: The API key if found, None otherwise
        """
        try:
            if not os.path.exists(self.config_file):
                return None

            with open(self.config_file, 'r') as f:
                api_key = f.read().strip()

            return api_key if api_key else None

        except Exception as e:
            print(f"Error loading API key: {e}")
            return None

    def delete_api_key(self) -> bool:
        """
        Delete the stored API key.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            return True

        except Exception as e:
            print(f"Error deleting API key: {e}")
            return False

    def has_api_key(self) -> bool:
        """
        Check if an API key is stored.

        Returns:
            bool: True if API key exists, False otherwise
        """
        return os.path.exists(self.config_file) and os.path.getsize(self.config_file) > 0
