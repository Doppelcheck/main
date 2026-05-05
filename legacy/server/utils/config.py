import json
import os
import pathlib


# Default configuration values
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 5000,
    "model": "tulu3",
    "debug": False,
    "custom_urls": [],  # Array to store custom search URLs
    "google_custom_search_api_key": "AIzaSyA0uco4J3foYY5H7Fm1pQirmI1kzPj1ZB4",
    "google_custom_search_engine_id": "67d78a2b549ad4939"
}

# Global configuration dictionary
_config: dict[str, any] = dict()

_config_file = pathlib.Path("content_analysis_config.json")
_ollama_host_env = "OLLAMA_HOST"

def init_config() -> None:
    """
    Initialize the configuration system.
    """

    global _config, _config_file, _ollama_host_env

    # Check if OLLAMA_HOST environment variable is set
    _ollama_host = os.getenv(_ollama_host_env)
    if _ollama_host:
        _config["ollama_host"] = _ollama_host
    else:
        print(f"Environment variable { _ollama_host_env } not set. Using default value.")
        _config["ollama_host"] = "http://localhost:11434"  # Default value

    # Load configuration from file if it exists
    if _config_file.exists():
        try:
            file_config = json.loads(_config_file.read_text())
            _config.update(DEFAULT_CONFIG)  # Start with defaults
            _config.update(file_config)  # Override with file values
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config file: {e}")
            _config.update(DEFAULT_CONFIG)  # Use defaults on error
    else:
        # No config file exists, use defaults
        _config.update(DEFAULT_CONFIG)
        # Save the default config
        save_config()


def get_config() -> dict[str, any]:
    """
    Get the entire configuration dictionary (copy).

    Returns:
        A copy of the configuration dictionary
    """
    return _config.copy()


def get(key: str, default: any = None) -> any:
    """
    Get a specific configuration value.

    Args:
        key: The configuration key to retrieve
        default: Value to return if key doesn't exist

    Returns:
        The configuration value or default if not found
    """
    return _config.get(key, default)


def set(key: str, value: any) -> None:
    """
    Set a configuration value and save to file.

    Args:
        key: The configuration key to set
        value: The value to set
    """
    _config[key] = value
    save_config()


def update(config_dict: dict[str, any]) -> None:
    """
    Update multiple configuration values at once and save.

    Args:
        config_dict: Dictionary of configuration keys and values to update
    """
    _config.update(config_dict)
    save_config()


def save_config() -> None:
    """Save the current configuration to file."""
    try:
        with open(_config_file, 'w') as f:
            config_copy = _config.copy()
            del config_copy["ollama_host"]
            json.dump(config_copy, f, indent=4)
    except IOError as e:
        print(f"Error saving config file: {e}")


# Initialize with defaults when module is imported
if not _config:
    init_config()