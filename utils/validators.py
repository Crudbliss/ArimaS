"""
validators.py
-------------
Password strength validation utilities.
"""

import re


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validates password strength.

    Rules:
      - At least 8 characters
      - At least 1 uppercase letter
      - At least 1 lowercase letter
      - At least 1 digit
      - At least 1 special character (!@#$%^&*()_+-=[]{}|;':",.<>?/`~)

    Returns:
        (True, "") if valid
        (False, "reason") if invalid
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."

    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;':\",./<>?`~]", password):
        return False, "Password must contain at least one special character."

    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    """
    Validates username format.

    Rules:
      - 3 to 30 characters
      - Only letters, numbers, and underscores
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    if len(username) > 30:
        return False, "Username must not exceed 30 characters."

    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username may only contain letters, numbers, and underscores."

    return True, ""
