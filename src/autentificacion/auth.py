import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).parent
STORAGE_DIR = Path(os.getenv("FLET_APP_STORAGE_DATA") or BASE_DIR / "storage")
USERS_FILE = STORAGE_DIR / "users.json"

ITERATIONS = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _load() -> dict:
    try:
        with open(USERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}}


def _save(data: dict) -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(USERS_FILE)  


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS).hex()


def _public(email: str, user: dict) -> dict:
    return {
        "email": email,
        "name": user["name"],
        "xp": user.get("xp", 0),
        "completed": list(user.get("completed", [])),
    }


def register(name: str, email: str, password: str, confirm: str):
    """Devuelve (True, usuario) o (False, mensaje_de_error)."""
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not name:
        return False, "Escribe tu nombre."
    if not EMAIL_RE.match(email):
        return False, "Correo no válido."
    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."
    if password != confirm:
        return False, "Las contraseñas no coinciden."

    data = _load()
    if email in data["users"]:
        return False, "Ese correo ya está registrado."

    salt = secrets.token_bytes(16)
    data["users"][email] = {
        "name": name,
        "salt": salt.hex(),
        "hash": _hash(password, salt),
        "xp": 0,
        "completed": [],
    }
    try:
        _save(data)
    except OSError:
        return False, "No se pudo guardar la cuenta."
    return True, _public(email, data["users"][email])


def login(email: str, password: str):
    """Devuelve (True, usuario) o (False, mensaje_de_error)."""
    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return False, "Completa correo y contraseña."

    user = _load()["users"].get(email)
    # Mismo mensaje si el correo no existe o la clave es incorrecta
    if user is None:
        return False, "Correo o contraseña incorrectos."

    expected = user["hash"]
    given = _hash(password, bytes.fromhex(user["salt"]))
    if not hmac.compare_digest(expected, given):
        return False, "Correo o contraseña incorrectos."
    return True, _public(email, user)


def save_progress(email: str, progress: dict) -> None:
    data = _load()
    user = data["users"].get(email)
    if user is None:
        return
    user["xp"] = progress["xp"]
    user["completed"] = progress["completed"]
    try:
        _save(data)
    except OSError as err:
        print(f"No se pudo guardar el progreso: {err}")