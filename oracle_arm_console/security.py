import json
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash


class PasswordStore:
    def __init__(self, path=None, initial_password="admin"):
        self.path = Path(path) if path else None
        self.password_hash = generate_password_hash(initial_password)
        if self.path and self.path.is_file():
            values = json.loads(self.path.read_text(encoding="utf-8"))
            stored_hash = values.get("password_hash", "")
            if stored_hash:
                self.password_hash = stored_hash

    def verify(self, password):
        return check_password_hash(self.password_hash, password)

    def update(self, password):
        self.password_hash = generate_password_hash(password)
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"password_hash": self.password_hash}, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)
