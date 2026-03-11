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

Usage:
    from src.core.license import LicenseManager

    LicenseManager().require_premium("rag_chat")   # raises if not licensed
    if LicenseManager().is_premium():
        ...
"""

from __future__ import annotations

import os
from pathlib import Path


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

    def _check_license_key(self) -> bool:
        """
        Validate a license key file.
        Not implemented yet — always returns False when beta is off.
        Will use RSA signature verification in v3.0.0 release.
        """
        key_path = Path.home() / ".config" / "aitao" / "license.key"
        if not key_path.exists():
            return False
        # TODO (v3.0.0): verify RSA signature of key contents
        return False
