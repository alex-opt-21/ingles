import json
import sys
from pathlib import Path

from gtts import gTTS

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
# Assumes this script is located in <project>/scripts/ (same as before).
SRC_DIR = Path(__file__).resolve().parents[1]

# Change the filename here if your JSON has another name.
EXERCISES_FILE = SRC_DIR / "data" / "acciones.json"
ASSETS_DIR = SRC_DIR / "assets"

FORCE = "--force" in sys.argv


def main() -> None:
    if not EXERCISES_FILE.exists():
        raise FileNotFoundError(f"No encuentro el JSON: {EXERCISES_FILE}")

    with EXERCISES_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    exercises = data.get("exercises")
    if not isinstance(exercises, list):
        raise ValueError(
            "El JSON debe contener una lista 'exercises' en la raíz. "
            "Este generador está preparado para la práctica continua de 80 ejercicios."
        )

    # Verificar IDs y actualizar rutas para que cada ejercicio tenga su propio MP3.
    # Esto evita que 'eat', 'ate' y 'will eat' sobrescriban el mismo archivo.
    seen_ids = set()
    for ex in exercises:
        exercise_id = ex.get("id")
        answer = ex.get("answer")

        if not exercise_id:
            raise ValueError("Hay un ejercicio sin campo 'id'.")
        if exercise_id in seen_ids:
            raise ValueError(f"ID duplicado: {exercise_id}")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError(f"El ejercicio '{exercise_id}' no tiene una respuesta válida.")

        seen_ids.add(exercise_id)
        ex["audio"] = f"audio/{exercise_id}.mp3"

    # Guardar las rutas nuevas en el JSON antes de generar los audios.
    # Así la aplicación sabrá qué MP3 corresponde a cada ejercicio.
    with EXERCISES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Leyendo: {EXERCISES_FILE}")
    print(f"Guardando en: {ASSETS_DIR}")
    print(f"Ejercicios encontrados: {len(exercises)}\n")

    ok = 0
    skipped = 0
    failed = []

    for ex in exercises:
        destino = ASSETS_DIR / ex["audio"]
        destino.parent.mkdir(parents=True, exist_ok=True)

        if destino.exists() and not FORCE:
            print(f"SKIP (ya existe): {destino.name}")
            skipped += 1
            continue

        # Permite indicar un texto alternativo para pronunciaciones ambiguas.
        # Ejemplo: 'read' en pasado se sintetiza dentro de una oración contextual.
        text_to_speak = ex.get("audio_text", ex["answer"]).strip()

        try:
            gTTS(text=text_to_speak, lang="en", tld="com").save(str(destino))
            print(f"OK: {destino}")
            ok += 1
        except Exception as e:
            print(f"ERROR en {ex['id']}: {e}")
            failed.append(ex["id"])

    print(
        f"\nGenerados: {ok} | Omitidos: {skipped} | Fallidos: {len(failed)}"
    )
    if failed:
        print("Reintenta estos:", ", ".join(failed))
        print("Puedes ejecutar nuevamente con --force para regenerar todos los audios.")


if __name__ == "__main__":
    main()
