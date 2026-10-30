import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

from gtts import gTTS


SRC_DIR = Path(__file__).resolve().parents[1]  
JSON_PREDETERMINADO = SRC_DIR / "data" / "preguntas.json"
ASSETS_DIR = SRC_DIR / "assets"
AUDIO_DIR = ASSETS_DIR / "audio" / "questions"


def ruta_audio(respuesta: str) -> str:
    """Nombre estable para que el JSON coincida con el MP3 generado."""
    respuesta = respuesta.strip()
    nombre = re.sub(r"[^a-z0-9]+", "_", respuesta.lower()).strip("_")[:42].rstrip("_")
    nombre = nombre or "answer"
    codigo = hashlib.sha1(respuesta.encode("utf-8")).hexdigest()[:10]
    return f"audio/questions/{nombre}_{codigo}.mp3"


def leer_preguntas(ruta: Path):
    with ruta.open("r", encoding="utf-8") as archivo:
        contenido = json.load(archivo)

    if isinstance(contenido, list):
        preguntas = contenido
    elif isinstance(contenido, dict):
        preguntas = next(
            (contenido[k] for k in ("exercises", "questions", "preguntas")
             if isinstance(contenido.get(k), list)),
            None,
        )
    else:
        preguntas = None

    if preguntas is None:
        raise ValueError(
            "JSON no reconocido. Se espera una lista o un objeto con "
            "'exercises', 'questions' o 'preguntas'."
        )
    return contenido, preguntas


def guardar_json(ruta: Path, contenido):
    """Copia de seguridad y guardado atómico para no corromper el JSON."""
    copia = ruta.with_suffix(ruta.suffix + ".bak")
    if not copia.exists():
        shutil.copy2(ruta, copia)
        print(f"Copia de seguridad: {copia}")

    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    try:
        temporal.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporal.replace(ruta)
    finally:
        temporal.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audios de respuestas para Questions de Saylo")
    parser.add_argument("--json", default=str(JSON_PREDETERMINADO), help="Ruta al preguntas.json")
    parser.add_argument("--force", action="store_true", help="Volver a generar los MP3 existentes")
    parser.add_argument("--slow", action="store_true", help="Leer la respuesta más despacio")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar los nombres sin generar ni escribir")
    args = parser.parse_args(argv)

    ruta_json = Path(args.json).resolve()
    if not ruta_json.is_file():
        parser.error(f"No se encontró el JSON: {ruta_json}")

    contenido, preguntas = leer_preguntas(ruta_json)
    if not args.dry_run:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    print(f"JSON: {ruta_json}")
    print(f"Carpeta de MP3: {AUDIO_DIR}")
    print(f"Preguntas: {len(preguntas)}\n")

    generados = 0
    existentes = 0
    duplicados = 0
    errores = []
    modificados = False
    vistos = set()

    for indice, pregunta in enumerate(preguntas, 1):
        identificador = str(pregunta.get("id", indice)) if isinstance(pregunta, dict) else str(indice)
        try:
            if not isinstance(pregunta, dict):
                raise ValueError("La pregunta no es un objeto JSON")

            # El audio que se escucha luego de acertar es la RESPUESTA, no la pregunta.
            respuesta = str(pregunta.get("answer") or "").strip()
            if not respuesta:
                raise ValueError("La pregunta no tiene 'answer'")

            url_audio = ruta_audio(respuesta)
            destino = ASSETS_DIR / url_audio
            if args.dry_run:
                print(f"PREVISUALIZACIÓN {identificador}: {respuesta!r} => {url_audio}")
                continue

            if url_audio in vistos:
                duplicados += 1
                print(f"REUTILIZADO {identificador}: {destino.name}")
            elif destino.exists() and not args.force:
                existentes += 1
                print(f"EXISTE {identificador}: {destino.name}")
            else:
                destino.parent.mkdir(parents=True, exist_ok=True)
                temporal = destino.with_suffix(".mp3.part")
                try:
                    gTTS(text=respuesta, lang="en", tld="com", slow=args.slow).save(str(temporal))
                    if not temporal.is_file() or temporal.stat().st_size == 0:
                        raise RuntimeError("gTTS no produjo un archivo válido")
                    temporal.replace(destino)
                finally:
                    temporal.unlink(missing_ok=True)
                generados += 1
                print(f"GENERADO {identificador}: {respuesta} => {destino.name}")

            vistos.add(url_audio)
            if pregunta.get("audio") != url_audio:
                pregunta["audio"] = url_audio
                modificados = True

        except Exception as error:
            errores.append((identificador, str(error)))
            print(f"ERROR {identificador}: {error}")

    if modificados:
        guardar_json(ruta_json, contenido)
        print("\nActualicé el campo 'audio' de preguntas.json.")
    elif args.dry_run:
        print("\nModo preview: no se generaron MP3 ni se modificó el JSON.")
    else:
        print("\nEl JSON ya tiene las rutas correctas.")

    print(
        f"\nGenerados: {generados} | Existentes: {existentes} | "
        f"Reutilizados: {duplicados} | Errores: {len(errores)}"
    )
    if errores:
        for id_pregunta, error in errores:
            print(f"  - {id_pregunta}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
