"""
AiTao — src/core/license.py

License management for the AiTao dual-license model.

Editions:
  - Core    (AGPL v3)       : file indexing + search, no RAG chat injection
  - Premium (Commercial)    : RAG chat, Virtual LLMs, advanced OCR, translation

During the BETA TEST phase, is_premium() always returns True so that all
invited testers have access to every feature without needing a license key.

To switch to enforced license checking, set:
  AITAO_BETA=false  in environment, or
  [license] beta_mode = false  in config/config.toml

License key format: AITAO-<base64url(payload_json)>.<base64url(rsa_sha256_signature)>
Validation: RSA-SHA256 offline verification using the embedded public key.

Usage:
    from src.core.license import LicenseManager

    LicenseManager().require_premium("rag_chat")   # raises if not licensed
    if LicenseManager().is_premium():
        ...
    LicenseManager().activate("AITAO-xxx.yyy")     # install a key
    LicenseManager().get_info()                     # {'tier':'premium','exp':'...','label':'...'}
"""

from __future__ import annotations

import base64
import datetime
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding

# RSA public key — verifies license signatures (private key never leaves the admin machine)
_PUBLIC_KEY_PEM = """\
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAviLlFdMu7i5YD5WmPkZh
3pNo+dNIATdlzJlB/iDPAQSnqtlfrVhtmAUE6tq0C8fet0Jck73fdwvK+FB6saiT
wn6ZimVrLLkV2mblOTl8AXvjbLfJ2OtTMQRymDkaambGR+39DERpAfhgnpNQGi3X
hX8255jPZhDr59pnmWrvZ5nJwXdiryq3MzVyVnxJT+0P6bDrXQAcexp64imjYz5q
QyLdA8bAusMYxdb9M5Tirp7zg3S4QHxckvkj+/T8mLdwXL9q1CMVsRegzKQbhEfU
cnZ7GX9fycImNd3Xn5uCWpKXYoHStMy43KkJgw38G8umb4DqEBj1vhpC7jAq0jDD
7QIDAQAB
-----END PUBLIC KEY-----
"""


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class PremiumFeatureError(RuntimeError):
    """Raised when a Premium feature is accessed without a valid license."""

    def __init__(self, feature: str) -> None:
        self.feature = feature
        super().__init__(
            f"'{feature}' is a Premium feature.\n"
            "Install a license key to unlock it:\n"
            "  ./aitao.sh license activate <YOUR-KEY>\n"
            "Purchase: https://shamantao.com"
        )


# ---------------------------------------------------------------------------
# License Manager
# ---------------------------------------------------------------------------

class LicenseManager:
    """
    Lightweight license checker.

    BETA MODE (default): is_premium() always returns True.
    Set env var AITAO_BETA=false or config [license] beta_mode = false
    to enforce key-based validation (v3.0.0 commercial release).
    """

    # Features gated behind Premium
    PREMIUM_FEATURES: tuple[str, ...] = (
        "rag_chat",         # RAG context injection into LLM prompts
        "virtual_models",   # -context / -basic model name routing
        "ocr_advanced",     # PaddleOCR + Qwen-VL
        "translation",      # mBART / NLLB document translation
        "categorization",   # Automatic document categorization
        "corrections",      # User feedback / learning loop
        "personal_assistant", # Agenda / reminders (roadmap)
    )

    def __init__(self) -> None:
        self._beta_mode = self._resolve_beta_mode()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_premium(self) -> bool:
        """Return True if Premium features are unlocked."""
        if self._beta_mode:
            return True
        return self._check_license_key()

    def require_premium(self, feature: str) -> None:
        """Raise PremiumFeatureError if the feature is not accessible."""
        if not self.is_premium():
            raise PremiumFeatureError(feature)

    def edition(self) -> str:
        """Return a human-readable edition string for display purposes."""
        if self._beta_mode:
            return "Premium (beta)"
        return "Premium" if self._check_license_key() else "Core"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resolve_beta_mode(self) -> bool:
        """
        Beta mode is ON unless explicitly disabled.
        Priority: env var > config file > default (True).
        """
        env = os.environ.get("AITAO_BETA", "").strip().lower()
        if env in ("false", "0", "no"):
            return False
        if env in ("true", "1", "yes"):
            return True

        # Check config.toml [license] beta_mode
        try:
            from src.core.config import ConfigManager
            cfg = ConfigManager()
            beta_cfg = cfg.get("license.beta_mode", None)
            if beta_cfg is not None:
                return bool(beta_cfg)
        except Exception:
            pass

        # Default: beta ON during pre-commercial phase
        return True

    def activate(self, key_str: str) -> bool:
        """Write a license key to disk. Returns True if the key is valid before saving."""
        if not self._verify_key_string(key_str):
            return False
        key_path = Path.home() / ".config" / "aitao" / "license.key"
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(key_str.strip())
        return True

    def deactivate(self) -> None:
        """Remove the license key file."""
        key_path = Path.home() / ".config" / "aitao" / "license.key"
        if key_path.exists():
            key_path.unlink()

    def get_info(self) -> dict:
        """Return parsed license payload, or empty dict if no valid key."""
        key_path = Path.home() / ".config" / "aitao" / "license.key"
        if not key_path.exists():
            return {}
        raw = key_path.read_text().strip()
        return self._parse_payload(raw) or {}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_license_key(self) -> bool:
        """Validate the on-disk license key using RSA-SHA256 signature."""
        key_path = Path.home() / ".config" / "aitao" / "license.key"
        if not key_path.exists():
            return False
        try:
            raw = key_path.read_text().strip()
            return self._verify_key_string(raw)
        except Exception:
            return False

    def _verify_key_string(self, key_str: str) -> bool:
        """Verify RSA signature and expiry of a raw key string."""
        if not key_str.startswith("AITAO-"):
            return False
        parts = key_str[6:].rsplit(".", 1)
        if len(parts) != 2:
            return False
        payload_b64, sig_b64 = parts
        try:
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + "==")
            signature = base64.urlsafe_b64decode(sig_b64 + "==")
            pub_key = serialization.load_pem_public_key(_PUBLIC_KEY_PEM.encode())
            pub_key.verify(signature, payload_bytes, asym_padding.PKCS1v15(), hashes.SHA256())
        except (InvalidSignature, Exception):
            return False
        data = self._parse_payload(key_str)
        if not data:
            return False
        exp = datetime.date.fromisoformat(data["exp"])
        return exp >= datetime.date.today() and data.get("tier") == "premium"

    @staticmethod
    def _parse_payload(key_str: str) -> dict | None:
        """Decode and return the JSON payload from a key string, or None on error."""
        try:
            inner = key_str[6:].rsplit(".", 1)[0]
            payload_bytes = base64.urlsafe_b64decode(inner + "==")
            return json.loads(payload_bytes)
        except Exception:
            return None
