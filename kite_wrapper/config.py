import configparser
import os

from kite_wrapper.exceptions import DataException

class KiteConfig:
    def __init__(self, api_key=None, api_secret=None, access_token=None, config_path=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.config_path = config_path or os.path.join(os.path.expanduser("~"), ".kite", "config.ini")
        self._load_config()

    def _load_config(self):
        # Order of precedence:
        # 1. Direct parameters (already assigned to self.api_key, self.api_secret, self.access_token)
        # 2. Environment variables
        # 3. Configuration file

        # Try loading from environment variables if not set by direct parameters
        if self.api_key is None:
            self.api_key = os.environ.get("KITE_API_KEY")
        if self.api_secret is None:
            self.api_secret = os.environ.get("KITE_API_SECRET")
        if self.access_token is None:
            self.access_token = os.environ.get("KITE_ACCESS_TOKEN")

        # Try loading from configuration file if not set by direct parameters or environment variables
        # This will only fill in values if they are still None
        if os.path.exists(self.config_path):
            parser = configparser.ConfigParser()
            parser.read(self.config_path)
            if "Kite" in parser:
                kite_section = parser["Kite"]
                if self.api_key is None:
                    self.api_key = kite_section.get("api_key")
                if self.api_secret is None:
                    self.api_secret = kite_section.get("api_secret")
                if self.access_token is None:
                    self.access_token = kite_section.get("access_token")
            # If "Kite" section is not in parser, and keys are still None, the final check will catch it.
            # No error raised here for missing section, as keys might have been sourced from env or params.

        if not self.api_key or not self.api_secret:
            raise DataException("API key or secret is missing. Please set them in config or environment variables.")

    def get_api_key(self):
        return self.api_key

    def get_api_secret(self):
        return self.api_secret

    def get_access_token(self):
        return self.access_token

    def set_access_token(self, access_token):
        self.access_token = access_token
        # Optionally, save to config file if it was loaded from there
        if os.path.exists(self.config_path):
            parser = configparser.ConfigParser()
            # Read existing content first to preserve other sections/values
            parser.read(self.config_path)
            if "Kite" not in parser:
                parser.add_section("Kite")

            parser["Kite"]["access_token"] = access_token
            try:
                with open(self.config_path, 'w') as configfile:
                    parser.write(configfile)
            except IOError:
                # Handle cases where config_path might not be writable, though it existed.
                # For example, if permissions changed or it's a read-only volume.
                # Depending on requirements, this could log a warning or raise an exception.
                pass # For now, silently ignore if saving fails

    def __str__(self):
        return f"KiteConfig(api_key='{self.api_key[:4] if self.api_key else 'None'}...', api_secret='{self.api_secret[:4] if self.api_secret else 'None'}...', access_token='{self.access_token[:4] if self.access_token else None}...', config_path='{self.config_path}')"
