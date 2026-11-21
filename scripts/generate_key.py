#!/usr/bin/env python3
"""
Generate an encryption key for Kolang credential management.
"""

from __future__ import annotations

import base64
import secrets


def generate_key() -> str:
    key_bytes = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(key_bytes).decode("utf-8")


def main() -> None:
    key = generate_key()
    print("Generated 256-bit encryption key:")
    print(key)
    print("\nAdd this to your .env file:")
    print(f"CREDENTIAL_ENCRYPTION_KEY={key}")


if __name__ == "__main__":
    main()
