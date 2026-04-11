"""Encrypted credential manager for Nexus connectors.

Uses Fernet symmetric encryption with a key derived from BRAIN_BEARER_TOKEN
via PBKDF2. Credentials stored as encrypted JSON at data/credentials.enc.
"""

import base64
import json
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

load_dotenv(r"C:\jarvis\.env")

logger = logging.getLogger("jarvis.connectors.auth")

DATA_DIR = Path(r"C:\jarvis\data")
SALT_FILE = DATA_DIR / ".cred_salt"
CRED_FILE = DATA_DIR / "credentials.enc"


def _get_fernet() -> Fernet:
    """Derive a Fernet key from BRAIN_BEARER_TOKEN + salt."""
    token = os.getenv("BRAIN_BEARER_TOKEN", "")
    if not token:
        raise RuntimeError("BRAIN_BEARER_TOKEN not set — cannot encrypt credentials")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Generate or load salt
    if SALT_FILE.exists():
        salt = SALT_FILE.read_bytes()
    else:
        salt = os.urandom(16)
        SALT_FILE.write_bytes(salt)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(token.encode()))
    return Fernet(key)


def _load_all() -> dict:
    """Load and decrypt all credentials."""
    if not CRED_FILE.exists():
        return {}
    try:
        f = _get_fernet()
        encrypted = CRED_FILE.read_bytes()
        decrypted = f.decrypt(encrypted)
        return json.loads(decrypted)
    except Exception as e:
        logger.error("Failed to decrypt credentials: %s", e)
        return {}


def _save_all(data: dict):
    """Encrypt and save all credentials."""
    f = _get_fernet()
    plaintext = json.dumps(data).encode()
    CRED_FILE.write_bytes(f.encrypt(plaintext))


def store_credential(connector: str, key: str, value: str):
    """Store a credential for a connector (encrypted)."""
    data = _load_all()
    if connector not in data:
        data[connector] = {}
    data[connector][key] = value
    _save_all(data)
    logger.info("Credential stored: %s.%s", connector, key)


def get_credential(connector: str, key: str) -> str | None:
    """Retrieve a credential for a connector."""
    data = _load_all()
    return data.get(connector, {}).get(key)


def has_credentials(connector: str, required_keys: list[str] | None = None) -> bool:
    """Check if a connector has stored credentials."""
    data = _load_all()
    if connector not in data:
        return False
    if required_keys:
        return all(k in data[connector] for k in required_keys)
    return bool(data[connector])


def delete_credentials(connector: str):
    """Remove all credentials for a connector."""
    data = _load_all()
    if connector in data:
        del data[connector]
        _save_all(data)
        logger.info("Credentials deleted: %s", connector)
