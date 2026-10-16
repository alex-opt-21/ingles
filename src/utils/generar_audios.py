import json
from pathlib import Path

from gtts import gTTS

BASE_DIR = Path(__file__).parent
EXERCISES_FILE = BASE_DIR / "data" / "acciones.json"
ASSETS_DIR = BASE_DIR / "assets"

with open(EXERCISES_FILE, encoding="utf-8") as f:
    exercises = json.load(f)["exercises"]

for ex in exercises:
    destino = ASSETS_DIR / ex["audio"]    
    destino.parent.mkdir(parents=True, exist_ok=True)

    texto = ex["answer"].lower()               
    gTTS(text=texto, lang="en", tld="com").save(str(destino))
    print(f"OK: {destino}")