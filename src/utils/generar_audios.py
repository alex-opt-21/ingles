import json
import sys
from pathlib import Path

from gtts import gTTS

# Rutas
SRC_DIR = Path(__file__).resolve().parents[1] 
ROOT_DIR = Path(__file__).resolve().parents[2]  

EXERCISES_FILE = SRC_DIR / "data" / "acciones.json"
ASSETS_DIR = SRC_DIR / "assets" 

FORCE = "--force" in sys.argv 

with open(EXERCISES_FILE, encoding="utf-8") as f:
    exercises = json.load(f)["exercises"]

print(f"Leyendo: {EXERCISES_FILE}")
print(f"Guardando en: {ASSETS_DIR}")
print(f"Ejercicios encontrados: {len(exercises)}\n")

ok, skipped, failed = 0, 0, []

for ex in exercises:
    destino = ASSETS_DIR / ex["audio"]
    destino.parent.mkdir(parents=True, exist_ok=True)

    if destino.exists() and not FORCE:
        print(f"SKIP (ya existe): {destino.name}")
        skipped += 1
        continue

    try:
        gTTS(text=ex["answer"].lower(), lang="en", tld="com").save(str(destino))
        print(f"OK: {destino}")
        ok += 1
    except Exception as e:
        print(f"ERROR en {ex['id']}: {e}")
        failed.append(ex["id"])

print(f"\nGenerados: {ok} | Omitidos: {skipped} | Fallidos: {len(failed)}")
if failed:
    print("Reintenta estos:", ", ".join(failed))