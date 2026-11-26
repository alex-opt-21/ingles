
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path
from typing import Optional


# ---------- PATHS ----------

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
USERS_FILE = STORAGE_DIR / "users.json"
SESSION_FILE= STORAGE_DIR / "session.json"

# ---------- CONFIGURATION ----------

ITERATIONS = 200_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DEFAULT_ACHIEVEMENTS = {
    "unlocked": [],
    "completed_modules": [],
    "perfect_practices": 0,
}


# ---------- LOAD / SAVE ----------

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

    tmp = STORAGE_DIR / "users.tmp"

    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp, USERS_FILE)

    except OSError as err:
        print(f"[ERROR] No se pudo guardar users.json: {err}")
        raise


# ---------- PERSISTENT LOCAL SESSION ----------

def _save_session(email: str) -> str:
    """Genera y guarda un token local para recordar al usuario."""

    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    token = secrets.token_urlsafe(32)

    session = {
        "email": email,
        "token": token,
    }

    tmp = STORAGE_DIR / "session.tmp"

    with tmp.open("w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp, SESSION_FILE)

    return token


def restore_session() -> Optional[dict]:
    """Recupera la sesión del usuario al abrir la aplicación."""

    try:
        with SESSION_FILE.open("r", encoding="utf-8") as f:
            session = json.load(f)

        email = session.get("email", "").strip().lower()
        token = session.get("token", "")

        if not email or not token:
            return None

        user = _load()["users"].get(email)

        if not user or not user.get("active", True):
            logout()
            return None

        return _public(email, user)

    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None


def logout() -> None:
    """Cierra la sesión y elimina el token local."""

    try:
        SESSION_FILE.unlink(missing_ok=True)
    except OSError as error:
        print(f"[ERROR] No se pudo cerrar la sesión: {error}")

# ---------- PASSWORD SECURITY ----------

def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    ).hex()


# ---------- PUBLIC USER DATA ----------

def _public(email: str, user: dict) -> dict:
    return {
        "email": email,
        "name": user["name"],
        "xp": user.get("xp", 0),
        "completed": list(user.get("completed", [])),
        "active_session": user.get("active_session"),
        "achievements": user.get(
            "achievements",
            DEFAULT_ACHIEVEMENTS.copy(),
        ),
        "progress": user.get("progress", {}),
    }


# ---------- REGISTER ----------

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
        "achievements": DEFAULT_ACHIEVEMENTS.copy(),
        "progress": {},
    }

    try:
        _save(data)

    except OSError:
        return False, "No se pudo guardar la cuenta."
    try:
        token = _save_session(email)
    except OSError:
        return False, "La cuenta se creó, pero no se pudo guardar la sesión."

    resultado = _public(email, data["users"][email])
    resultado["token"] = token

    return True, resultado
    

# ---------- LOGIN ----------

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

    try:
       token = _save_session(email)
    except OSError:
       return False, "No se pudo guardar la sesión local."

    resultado = _public(email, user)
    resultado["token"] = token

    return True, resultado


# ---------- GET USER ----------

def get_user(email: str) -> Optional[dict]:
    """Obtiene los datos públicos de un usuario registrado."""

    email = (email or "").strip().lower()
    user = _load()["users"].get(email)

    return _public(email, user) if user else None


# ---------- SAVE PROGRESS ----------

def save_progress(email: str, progress: dict) -> None:
    """
    Actualiza XP, ejercicios, sesiones, logros y progreso
    sin borrar los demás datos del usuario.
    """

    email = (email or "").strip().lower()

    if not isinstance(progress, dict):
        raise TypeError("progress debe ser un diccionario.")

    data = _load()
    user = data["users"].get(email)

    if user is None:
        print(f"[ERROR] Usuario no encontrado: {email}")
        return

    if "xp" in progress:
        user["xp"] = progress["xp"]

    if "completed" in progress:
        user["completed"] = list(progress["completed"])

    if "active_session" in progress:
        user["active_session"] = progress["active_session"]

    if "achievements" in progress:
        user["achievements"] = progress["achievements"]

    if "progress" in progress:
        user["progress"] = progress["progress"]

    _save(data)
    print("[OK] Progreso guardado correctamente.")


# ---------- MODULE PROGRESS ----------

def save_module_progress(
    email: str,
    module: str,
    lesson: str,
    level: str,
    state: dict,
) -> None:
    """Guarda el progreso de una práctica específica."""

    if not isinstance(state, dict):
        raise TypeError("state debe ser un diccionario.")

    # Verifica que el estado sea serializable.
    json.dumps(state, ensure_ascii=False)

    email = (email or "").strip().lower()
    data = _load()
    user = data["users"].get(email)

    if user is None:
        print(f"[ERROR] Usuario no encontrado: {email}")
        return

    progress = user.setdefault("progress", {})

    progress.setdefault(module, {})
    progress[module].setdefault(lesson, {})

    progress[module][lesson][level] = state

    _save(data)


def get_module_progress(
    email: str,
    module: str,
    lesson: str,
    level: str,
) -> Optional[dict]:
    """Recupera el progreso de una práctica específica."""

    user = get_user(email)

    if not user:
        return None

    return (
        user.get("progress", {})
        .get(module, {})
        .get(lesson, {})
        .get(level)
    )


def clear_module_progress(
    email: str,
    module: str,
    lesson: str,
    level: str,
) -> None:
    """Elimina solamente el progreso de una práctica específica."""

    email = (email or "").strip().lower()
    data = _load()
    user = data["users"].get(email)

    if user is None:
        return

    progress = user.get("progress", {})

    if module in progress:
        if lesson in progress[module]:
            progress[module][lesson].pop(level, None)

            if not progress[module][lesson]:
                progress[module].pop(lesson)

        if not progress[module]:
            progress.pop(module)

    _save(data)


# ---------- LEGACY ACTIVE SESSION ----------

def save_active_session(email: str, session_state: dict) -> None:
    """Compatibilidad con el sistema anterior de sesiones."""

    if not isinstance(session_state, dict):
        raise TypeError("session_state debe ser un diccionario.")

    json.dumps(session_state, ensure_ascii=False)

    save_progress(email, {"active_session": session_state})


def get_active_session(email: str) -> Optional[dict]:
    """Devuelve la sesión pendiente del sistema anterior."""

    user = get_user(email)

    return user.get("active_session") if user else None


def clear_active_session(email: str) -> None:
    """Elimina la sesión pendiente del sistema anterior."""

    save_progress(email, {"active_session": None})


# ---------- ACHIEVEMENTS ----------

def save_achievements(email: str, achievements: dict) -> None:
    """Guarda los logros de un usuario."""

    if not isinstance(achievements, dict):
        raise TypeError("achievements debe ser un diccionario.")

    save_progress(email, {"achievements": achievements})


def get_achievements(email: str) -> dict:
    """Obtiene los logros guardados de un usuario."""

    user = get_user(email)

    if not user:
        return DEFAULT_ACHIEVEMENTS.copy()

    return user.get(
        "achievements",
        DEFAULT_ACHIEVEMENTS.copy(),
    )


# ---------- RANKING ----------

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

    estudiantes.sort(
        key=lambda u: (-u["xp"], u["name"].lower())
    )

    return estudiantes[:limit] if limit is not None else estudiantes
