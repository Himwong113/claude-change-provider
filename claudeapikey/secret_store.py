"""OS keyring secret storage abstraction."""

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

SERVICE_NAME = "claudeapikey"


def _username(vendor: str) -> str:
    return f"vendor:{vendor}"


def set_key(vendor: str, key: str) -> None:
    """Save an API key to the OS keyring."""
    keyring.set_password(SERVICE_NAME, _username(vendor), key)


def get_key(vendor: str) -> str | None:
    """Retrieve an API key from the OS keyring."""
    return keyring.get_password(SERVICE_NAME, _username(vendor))


def delete_key(vendor: str) -> None:
    """Delete an API key from the OS keyring."""
    try:
        keyring.delete_password(SERVICE_NAME, _username(vendor))
    except PasswordDeleteError:
        pass


def key_exists(vendor: str) -> bool:
    """Check whether a key exists in the OS keyring."""
    return get_key(vendor) is not None


def mask_key(key: str) -> str:
    """Mask an API key for display.

    Shows first 3 chars, ellipsis, and last 4 chars.
    """
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:3]}...{key[-4:]}"


def check_keyring_available() -> bool:
    """Check whether the OS keyring backend is functional."""
    try:
        backend = keyring.get_keyring()
        return backend is not None and backend.priority >= 0
    except KeyringError:
        return False
