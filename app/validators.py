import re


def is_valid_email(email: str) -> bool:
    """
    Validates an email and ensures it is a @colby.edu address.
    """
    if not email:
        return False

    pattern = r"^[a-zA-Z0-9._%+-]+@colby\.edu$"
    return bool(re.match(pattern, email))


def is_strong_password(password: str) -> bool:
    """
    Requires a secure password:
    - minimum 12 characters
    - at least one uppercase letter
    - at least one lowercase letter
    - at least one number
    - at least one special character
    """
    password = password.strip()

    if len(password) < 12:
        return False

    upper = re.search(r"[A-Z]", password)
    lower = re.search(r"[a-z]", password)
    number = re.search(r"[0-9]", password)
    special = re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password)

    return all([upper, lower, number, special])
