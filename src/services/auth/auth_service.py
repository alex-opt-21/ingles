
import os
import httpx
from typing import Optional
from copy import deepcopy


# ==================================================
# CONFIGURACIÓN DEL SERVIDOR
# ==================================================

API_URL = os.getenv(
    "BRIGHT_ENGLISH_API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

TIMEOUT = 15.0

_TOKEN = None
_CURRENT_EMAIL = None
_CURRENT_USER = None


# ==================================================
# COMUNICACIÓN CON FASTAPI
# ==================================================

def _request(method, endpoint, data=None, authenticated=False):

    headers = {}

    if authenticated:
        if not _TOKEN:
            raise RuntimeError("Debes iniciar sesión nuevamente.")

        headers["Authorization"] = f"Bearer {_TOKEN}"

    try:
        response = httpx.request(
            method,
            f"{API_URL}{endpoint}",
            json=data,
            headers=headers,
            timeout=TIMEOUT,
        )

        if response.is_error:
            try:
                detail = response.json().get(
                    "detail",
                    "Error de comunicación con el servidor."
                )
            except Exception:
                detail = "Error de comunicación con el servidor."

            raise RuntimeError(str(detail))

        return response.json()

    except httpx.ConnectError:
        raise RuntimeError(
            "No se pudo conectar con Bright English. "
            "Comprueba que el servidor esté funcionando."
        )

    except httpx.TimeoutException:
        raise RuntimeError(
            "El servidor tardó demasiado en responder."
        )


def _update_cache(user):
    global _CURRENT_USER

    if user:
        _CURRENT_USER = deepcopy(user)


def _require_email(email):

    email = (email or "").strip().lower()

    if not email:
        raise RuntimeError("Correo de usuario no válido.")

    if _CURRENT_EMAIL != email or not _TOKEN:
        raise RuntimeError(
            "La sesión no corresponde a este usuario. "
            "Inicia sesión nuevamente."
        )

    return email


# ==================================================
# REGISTRO
# ==================================================

def register(name, email, password, confirm):
    """Devuelve (True, usuario) o (False, mensaje)."""

    global _TOKEN, _CURRENT_EMAIL, _CURRENT_USER

    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""
    confirm = confirm or ""

    if not name:
        return False, "Escribe tu nombre."

    if not email or "@" not in email:
        return False, "Correo no válido."

    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."

    if password != confirm:
        return False, "Las contraseñas no coinciden."

    try:
        result = _request(
            "POST",
            "/register",
            {
                "name": name,
                "email": email,
                "password": password,
            }
        )

        _TOKEN = result["token"]
        _CURRENT_EMAIL = email
        _update_cache(result["user"])

        return True, deepcopy(_CURRENT_USER)

    except RuntimeError as error:
        return False, str(error)


# ==================================================
# INICIO DE SESIÓN
# ==================================================

def login(email, password):
    """Devuelve (True, usuario) o (False, mensaje)."""

    global _TOKEN, _CURRENT_EMAIL, _CURRENT_USER

    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return False, "Completa correo y contraseña."

    try:
        result = _request(
            "POST",
            "/login",
            {
                "email": email,
                "password": password,
            }
        )

        _TOKEN = result["token"]
        _CURRENT_EMAIL = email
        _update_cache(result["user"])

        return True, deepcopy(_CURRENT_USER)

    except RuntimeError as error:
        return False, str(error)


# ==================================================
# CERRAR SESIÓN
# ==================================================

def logout():
    global _TOKEN, _CURRENT_EMAIL, _CURRENT_USER

    _TOKEN = None
    _CURRENT_EMAIL = None
    _CURRENT_USER = None


# ==================================================
# OBTENER USUARIO
# ==================================================

def get_user(email: str) -> Optional[dict]:

    email = (email or "").strip().lower()

    if email != _CURRENT_EMAIL or not _TOKEN:
        return None

    try:
        result = _request(
            "GET",
            "/me",
            authenticated=True
        )

        _update_cache(result)

        return deepcopy(_CURRENT_USER)

    except RuntimeError as error:
        print(f"[ERROR] No se pudo obtener el usuario: {error}")
        return None


# ==================================================
# GUARDAR PROGRESO GENERAL
# ==================================================

def save_progress(email: str, progress: dict) -> None:
    """
    Envía el progreso del estudiante al servidor central.
    """

    if not isinstance(progress, dict):
        raise TypeError("progress debe ser un diccionario.")

    email = _require_email(email)

    try:
        result = _request(
            "PUT",
            "/progress",
            progress,
            authenticated=True
        )

        _update_cache(result["user"])

        print("[OK] Progreso sincronizado con el servidor.")

    except RuntimeError as error:
        print(f"[ERROR] No se pudo sincronizar el progreso: {error}")
        raise


# ==================================================
# MÓDULOS Y SESIONES
# ==================================================

def save_module_progress(
    email: str,
    module: str,
    lesson: str,
    level: str,
    state: dict,
) -> None:

    import json

    if not isinstance(state, dict):
        raise TypeError("state debe ser un diccionario.")

    json.dumps(state, ensure_ascii=False)

    user = get_user(email)

    if not user:
        raise RuntimeError("No se pudo recuperar el usuario.")

    progress = user.get("progress", {})

    progress.setdefault(module, {})
    progress[module].setdefault(lesson, {})

    progress[module][lesson][level] = state

    save_progress(email, {"progress": progress})


def get_module_progress(
    email: str,
    module: str,
    lesson: str,
    level: str,
) -> Optional[dict]:

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

    user = get_user(email)

    if not user:
        raise RuntimeError("No se pudo recuperar el usuario.")

    progress = user.get("progress", {})

    if module in progress:

        if lesson in progress[module]:
            progress[module][lesson].pop(level, None)

            if not progress[module][lesson]:
                progress[module].pop(lesson)

        if not progress[module]:
            progress.pop(module)

    save_progress(email, {"progress": progress})


# ==================================================
# SESIÓN ACTIVA LEGACY
# ==================================================

def save_active_session(email: str, session_state: dict):

    if not isinstance(session_state, dict):
        raise TypeError("session_state debe ser un diccionario.")

    save_progress(email, {"active_session": session_state})


def get_active_session(email: str) -> Optional[dict]:

    user = get_user(email)

    return user.get("active_session") if user else None


def clear_active_session(email: str):

    save_progress(email, {"active_session": None})


# ==================================================
# LOGROS
# ==================================================

DEFAULT_ACHIEVEMENTS = {
    "unlocked": [],
    "completed_modules": [],
    "perfect_practices": 0,
}


def save_achievements(email: str, achievements: dict):

    if not isinstance(achievements, dict):
        raise TypeError("achievements debe ser un diccionario.")

    save_progress(email, {"achievements": achievements})


def get_achievements(email: str) -> dict:

    user = get_user(email)

    if not user:
        return deepcopy(DEFAULT_ACHIEVEMENTS)

    return user.get(
        "achievements",
        deepcopy(DEFAULT_ACHIEVEMENTS)
    )


# ==================================================
# RANKING CENTRAL
# ==================================================

def get_ranking(limit=None):

    try:
        result = _request("GET", "/ranking")

        students = result.get("ranking", [])

        if limit is not None:
            students = students[:limit]

        return students

    except RuntimeError as error:
        print(f"[ERROR] No se pudo cargar el ranking: {error}")
        return []
