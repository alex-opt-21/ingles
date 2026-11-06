import hashlib
import hmac
import json
import re
import secrets
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
USERS_FILE = STORAGE_DIR / "users.json"

ITERATIONS = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _load() -> dict:
    try:
        with USERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("users"), dict):
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return {"users": {}}


def _save(data: dict) -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = USERS_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        # El reemplazo evita dejar users.json a medio escribir.
    tmp.replace(USERS_FILE)


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS
    ).hex()


def _public(email: str, user: dict) -> dict:
    return {
        "email": email,
        "name": user["name"],
        "xp": user.get("xp", 0),
        "completed": list(user.get("completed", [])),
        # Solo se devuelve al usuario autenticado para que la app pueda
        # ofrecerle continuar su propia práctica pendiente.
        "active_session": user.get("active_session"),
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
        "active_session": None,
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
    if user is None:
        return False, "Correo o contraseña incorrectos."

    expected = user["hash"]
    given = _hash(password, bytes.fromhex(user["salt"]))
    if not hmac.compare_digest(expected, given):
        return False, "Correo o contraseña incorrectos."
    return True, _public(email, user)


def get_user(email: str) -> Optional[dict]:
    """Obtiene los datos públicos de un usuario ya registrado."""
    email = (email or "").strip().lower()
    user = _load()["users"].get(email)
    return _public(email, user) if user else None


def save_progress(email: str, progress: dict) -> None:
    """Actualiza XP/completados sin borrar otros campos del usuario."""
    email = (email or "").strip().lower()
    data = _load()
    user = data["users"].get(email)
    if user is None:
        return

    if "xp" in progress:
        user["xp"] = progress["xp"]
    if "completed" in progress:
        user["completed"] = list(progress["completed"])
    if "active_session" in progress:
        user["active_session"] = progress["active_session"]

    try:
        _save(data)
    except OSError as err:
        print(f"No se pudo guardar el progreso: {err}")


def save_active_session(email: str, session_state: dict) -> None:
    """Guarda o actualiza la práctica pendiente de un estudiante."""
    if not isinstance(session_state, dict):
        raise TypeError("session_state debe ser un diccionario.")
    # Valida que todo pueda representarse en JSON antes de modificar users.json.
    json.dumps(session_state, ensure_ascii=False)
    save_progress(email, {"active_session": session_state})


def get_active_session(email: str) -> Optional[dict]:
    """Devuelve la sesión pendiente, o None si no existe."""
    user = get_user(email)
    return user.get("active_session") if user else None


def clear_active_session(email: str) -> None:
    """Elimina la práctica pendiente sin tocar XP ni ejercicios completados."""
    save_progress(email, {"active_session": None})


def get_ranking(limit=None):
    """Devuelve el ranking de estudiantes ordenado por XP."""
    usuarios = _load().get("users", {})
    estudiantes = []

    for email, user in usuarios.items():
        if user.get("role", "user") != "user":
            continue
        if not user.get("active", True):
            continue

        estudiantes.append({
            "name": user.get("name", "Estudiante"),
            "email": email,
            "xp": user.get("xp", 0),
            "completed": len(user.get("completed", [])),
        })

    estudiantes.sort(key=lambda u: (-u["xp"], u["name"].lower()))
    return estudiantes[:limit] if limit is not None else estudiantes
