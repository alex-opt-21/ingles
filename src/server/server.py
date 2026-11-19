
import os
import json
import hmac
import hashlib
import secrets
import base64
import threading
import time

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field


# ==================================================
# CONFIGURACIÓN
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
USERS_FILE = STORAGE_DIR / "users.json"

API_SECRET = os.getenv("BRIGHT_ENGLISH_SECRET")

if not API_SECRET or len(API_SECRET) < 32:
    raise RuntimeError(
        "Configura BRIGHT_ENGLISH_SECRET con al menos 32 caracteres."
    )

ITERATIONS = 200_000
file_lock = threading.RLock()

app = FastAPI(
    title="Bright English API",
    description="Servidor centralizado mediante archivos JSON",
    version="1.0.0",
)

security = HTTPBearer()


# ==================================================
# ARCHIVOS JSON
# ==================================================

def load_users():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        return {"users": {}}

    try:
        with USERS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError("Formato JSON inválido.")

        if not isinstance(data.get("users"), dict):
            raise ValueError("No existe el apartado users.")

        return data

    except (json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(
            f"El archivo users.json está dañado: {error}"
        )


def save_users(data):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = USERS_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )
        file.flush()
        os.fsync(file.fileno())

    os.replace(temporary_file, USERS_FILE)


# ==================================================
# CONTRASEÑAS
# ==================================================

def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS
    )

    return salt.hex(), hashed.hex()


# ==================================================
# AUTENTICACIÓN MEDIANTE TOKEN
# ==================================================

def create_token(email):
    payload = {
        "email": email,
        "exp": int(time.time()) + 86400
    }

    raw = json.dumps(payload).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")

    signature = hmac.new(
        API_SECRET.encode(),
        encoded.encode(),
        hashlib.sha256
    ).digest()

    signed = base64.urlsafe_b64encode(
        signature
    ).decode().rstrip("=")

    return f"{encoded}.{signed}"


def verify_token(token):
    try:
        encoded, signature = token.split(".")

        expected = hmac.new(
            API_SECRET.encode(),
            encoded.encode(),
            hashlib.sha256
        ).digest()

        received = base64.urlsafe_b64decode(
            signature + "=" * (-len(signature) % 4)
        )

        if not hmac.compare_digest(expected, received):
            raise ValueError("Firma inválida.")

        raw = base64.urlsafe_b64decode(
            encoded + "=" * (-len(encoded) % 4)
        )

        payload = json.loads(raw)

        if payload["exp"] < time.time():
            raise ValueError("Token vencido.")

        return payload["email"]

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o vencida."
        )



# ==================================================
# USUARIO AUTENTICADO
# ==================================================

def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    email = verify_token(credentials.credentials)

    with file_lock:
        user = load_users()["users"].get(email)

    if not user or not user.get("active", True):
        raise HTTPException(
            status_code=401,
            detail="Usuario no disponible."
        )

    return email


# ==================================================
# VERIFICACIÓN DE ADMINISTRADOR
# ==================================================

def current_admin(email: str = Depends(current_user)):
    with file_lock:
        user = load_users()["users"].get(email)

    if not user or user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos de administrador."
        )

    return email


# ==================================================
# MODELOS
# ==================================================

class RegisterData(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginData(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ProgressData(BaseModel):
    xp: Optional[int] = Field(default=None, ge=0)
    completed: Optional[list] = None
    achievements: Optional[dict] = None
    progress: Optional[dict] = None
    active_session: Optional[dict] = None


# ==================================================
# RESPUESTA PÚBLICA
# ==================================================

def public_user(email, user):
    return {
        "email": email,
        "name": user.get("name", "Estudiante"),
        "xp": user.get("xp", 0),
        "completed": user.get("completed", []),
        "achievements": user.get("achievements", {
            "unlocked": [],
            "completed_modules": [],
            "perfect_practices": 0
        }),
        "progress": user.get("progress", {}),
        "active_session": user.get("active_session")
    }


# ==================================================
# INICIO DEL SERVIDOR
# ==================================================

@app.get("/")
def home():
    return {
        "message": "Bright English API funcionando",
        "version": "1.0.0"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# ==================================================
# REGISTRO
# ==================================================

@app.post("/register")
def register(data: RegisterData):

    email = str(data.email).strip().lower()
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Escribe tu nombre."
        )

    salt, hashed = hash_password(data.password)

    with file_lock:
        database = load_users()

        if email in database["users"]:
            raise HTTPException(
                status_code=409,
                detail="Ese correo ya está registrado."
            )

        database["users"][email] = {
            "name": name,
            "salt": salt,
            "hash": hashed,
            "xp": 0,
            "completed": [],
            "active_session": None,
            "achievements": {
                "unlocked": [],
                "completed_modules": [],
                "perfect_practices": 0
            },
            "progress": {},
            "role": "user",
            "active": True
        }

        save_users(database)

        user = database["users"][email]

    return {
        "message": "Cuenta creada correctamente.",
        "token": create_token(email),
        "user": public_user(email, user)
    }


# ==================================================
# INICIO DE SESIÓN
# ==================================================

@app.post("/login")
def login(data: LoginData):

    email = str(data.email).strip().lower()

    with file_lock:
        user = load_users()["users"].get(email)

    if not user or not user.get("active", True):
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos."
        )

    salt = bytes.fromhex(user["salt"])

    _, hashed = hash_password(data.password, salt)

    if not hmac.compare_digest(hashed, user["hash"]):
        raise HTTPException(
            status_code=401,
            detail="Correo o contraseña incorrectos."
        )

    return {
        "message": "Inicio de sesión correcto.",
        "token": create_token(email),
        "user": public_user(email, user)
    }


# ==================================================
# PERFIL DEL USUARIO
# ==================================================

@app.get("/me")
def me(email: str = Depends(current_user)):

    with file_lock:
        user = load_users()["users"].get(email)

    return public_user(email, user)


# ==================================================
# GUARDAR PROGRESO
# ==================================================

@app.put("/progress")
def update_progress(
    data: ProgressData,
    email: str = Depends(current_user)
):

    updates = data.model_dump(exclude_unset=True)

    with file_lock:
        database = load_users()
        user = database["users"].get(email)

        if not user:
            raise HTTPException(
                status_code=404,
                detail="Usuario no encontrado."
            )

        user.update(updates)

        save_users(database)

    return {
        "message": "Progreso guardado correctamente.",
        "user": public_user(email, user)
    }


# ==================================================
# RANKING GENERAL
# ==================================================

@app.get("/ranking")
def ranking():

    with file_lock:
        users = load_users()["users"]

    students = []

    for email, user in users.items():

        if user.get("role", "user") != "user":
            continue

        if not user.get("active", True):
            continue

        students.append({
            "name": user.get("name", "Estudiante"),
            "email": email,
            "xp": user.get("xp", 0),
            "completed": len(user.get("completed", []))
        })

    students.sort(
        key=lambda student: (
            -student["xp"],
            student["name"].lower()
        )
    )

    return {"ranking": students}

# ==================================================
# ADMINISTRACIÓN: LISTAR USUARIOS
# ==================================================

@app.get("/admin/users")
def admin_users(email: str = Depends(current_admin)):

    with file_lock:
        users = load_users()["users"]

        result = []

        for user_email, user in users.items():

            result.append({
                "email": user_email,
                "name": user.get("name", "Estudiante"),
                "role": user.get("role", "user"),
                "active": user.get("active", True),
                "xp": user.get("xp", 0),
                "completed": user.get("completed", []),
                "achievements": user.get("achievements", {}),
                "progress": user.get("progress", {})
            })

    return {
        "total": len(result),
        "users": result
    }
