
import re
import secrets

from services.auth import auth_service as auth


def _load_users():
    """Lee los usuarios existentes de users.json."""
    data = auth._load()
    data.setdefault("users", {})
    return data


def _public_user(email, user):
    """Devuelve información segura, sin contraseña ni salt."""
    return {
        "email": email,
        "name": user.get("name", ""),
        "role": user.get("role", "user"),
        "active": user.get("active", True),
        "xp": user.get("xp", 0),
        "completed": list(user.get("completed", [])),
    }


def admin_login(email, password):
    """Solo permite entrar a cuentas administrativas activas."""
    email = (email or "").strip().lower()
    password = password or ""

    if not email or not password:
        return False, "Completa el correo y la contraseña."

    user = _load_users()["users"].get(email)

    if not user or user.get("role", "user") != "admin":
        return False, "Credenciales administrativas incorrectas."

    if not user.get("active", True):
        return False, "La cuenta administrativa está desactivada."

    try:
        expected = user["hash"]
        salt = bytes.fromhex(user["salt"])
        given = auth._hash(password, salt)
    except (KeyError, ValueError, TypeError):
        return False, "No se pudieron validar las credenciales."

    if not secrets.compare_digest(expected, given):
        return False, "Credenciales administrativas incorrectas."

    return True, _public_user(email, user)


def list_users():
    """Lista todas las cuentas registradas."""
    users = _load_users()["users"]
    return [
        _public_user(email, user)
        for email, user in sorted(users.items())
    ]


def create_user(name, email, password):
    """Crea una cuenta normal desde la administración."""
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = password or ""

    if not name:
        return False, "El nombre es obligatorio."

    if not auth.EMAIL_RE.match(email):
        return False, "El correo no es válido."

    if len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."

    data = _load_users()

    if email in data["users"]:
        return False, "Ya existe una cuenta con ese correo."

    salt = secrets.token_bytes(16)
    data["users"][email] = {
        "name": name,
        "salt": salt.hex(),
        "hash": auth._hash(password, salt),
        "xp": 0,
        "completed": [],
        "role": "user",
        "active": True,
    }

    try:
        auth._save(data)
    except OSError:
        return False, "No se pudo guardar el usuario."

    return True, _public_user(email, data["users"][email])


def update_user(email, name):
    """Permite modificar el nombre de una cuenta."""
    email = (email or "").strip().lower()
    name = (name or "").strip()

    if not name:
        return False, "El nombre es obligatorio."

    data = _load_users()
    user = data["users"].get(email)

    if user is None:
        return False, "No se encontró el usuario."

    user["name"] = name

    try:
        auth._save(data)
    except OSError:
        return False, "No se pudieron guardar los cambios."

    return True, "Usuario actualizado correctamente."


def set_user_active(email, active):
    """Activa o desactiva una cuenta sin borrar su progreso."""
    email = (email or "").strip().lower()
    data = _load_users()
    user = data["users"].get(email)

    if user is None:
        return False, "No se encontró el usuario."

    if user.get("role", "user") == "admin":
        return False, "No se puede desactivar una cuenta administrativa desde esta función."

    user["active"] = bool(active)

    try:
        auth._save(data)
    except OSError:
        return False, "No se pudo guardar el cambio."

    return True, "Estado del usuario actualizado."
def delete_user(email):
    """Elimina una cuenta normal sin permitir borrar administradores."""
    email = (email or "").strip().lower()
    data = _load_users()
    user = data["users"].get(email)

    if user is None:
        return False, "No se encontró el usuario."

    if user.get("role", "user") == "admin":
        return False, "No se puede eliminar una cuenta administrativa."

    del data["users"][email]

    try:
        auth._save(data)
    except OSError:
        return False, "No se pudo eliminar el usuario."

    return True, "Usuario eliminado correctamente."
