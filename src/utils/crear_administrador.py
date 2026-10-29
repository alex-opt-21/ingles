
import getpass
import re
import secrets
import sys
from pathlib import Path

# Permite importar los servicios desde la carpeta src.
SRC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC_DIR))

from services.auth import auth_service as auth


def crear_administrador():
    print("\n=== CREAR CUENTA ADMINISTRADORA ===\n")

    nombre = input("Nombre del administrador: ").strip()
    correo = input("Correo del administrador: ").strip().lower()
    contrasena = getpass.getpass("Contraseña (mínimo 6 caracteres): ")
    confirmar = getpass.getpass("Repite la contraseña: ")

    if not nombre:
        print("Error: el nombre es obligatorio.")
        return

    if not auth.EMAIL_RE.match(correo):
        print("Error: el correo no es válido.")
        return

    if len(contrasena) < 6:
        print("Error: la contraseña debe tener al menos 6 caracteres.")
        return

    if contrasena != confirmar:
        print("Error: las contraseñas no coinciden.")
        return

    data = auth._load()
    usuarios = data.setdefault("users", {})

    if correo in usuarios:
        print("Error: ya existe una cuenta con ese correo.")
        print("No se modificó ninguna cuenta existente.")
        return

    salt = secrets.token_bytes(16)

    usuarios[correo] = {
        "name": nombre,
        "salt": salt.hex(),
        "hash": auth._hash(contrasena, salt),
        "xp": 0,
        "completed": [],
        "role": "admin",
        "active": True,
    }

    try:
        auth._save(data)
    except OSError as error:
        print(f"No se pudo guardar la cuenta: {error}")
        return

    print("\nAdministrador creado correctamente.")
    print(f"Correo: {correo}")
    print("Ya puedes cerrar este programa.")


if __name__ == "__main__":
    crear_administrador()
