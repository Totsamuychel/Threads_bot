"""Generate a bcrypt hash for the admin password.

Usage:
    python hash_password.py mypassword
    python hash_password.py          # will prompt

Paste the output as ADMIN_PASSWORD_HASH in your .env file.
"""

import sys

try:
    from passlib.context import CryptContext
except ImportError:
    print("Error: passlib not installed. Run: pip install passlib[bcrypt]")
    sys.exit(1)

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

if len(sys.argv) > 1:
    password = sys.argv[1]
else:
    import getpass
    password = getpass.getpass("Password: ")

print(ctx.hash(password))
