import json
import secrets
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


class PasswordStore:
    def __init__(self, path=None, initial_password=None):
        self.path = Path(path) if path else None
        self.password_hash = ""
        self.session_secret = secrets.token_hex(32)
        needs_save = bool(self.path)
        if self.path and self.path.is_file():
            values = json.loads(self.path.read_text(encoding="utf-8"))
            self.password_hash = values.get("password_hash", "")
            stored_secret = values.get("session_secret", "")
            if stored_secret:
                self.session_secret = stored_secret
                needs_save = False

        # Explicit callers may seed a new store for tests or controlled migrations.
        # The web app does not pass a default password.
        if not self.password_hash and initial_password is not None:
            self.password_hash = generate_password_hash(initial_password)

        if needs_save:
            self._save()

    @property
    def is_initialized(self):
        return bool(self.password_hash)

    def verify(self, password):
        return self.is_initialized and check_password_hash(self.password_hash, password)

    def initialize(self, password):
        if self.is_initialized:
            raise RuntimeError("Admin password is already initialized")
        self.update(password)

    def update(self, password):
        self.password_hash = generate_password_hash(password)
        self._save()

    def _save(self):
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "password_hash": self.password_hash,
                    "session_secret": self.session_secret,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)
