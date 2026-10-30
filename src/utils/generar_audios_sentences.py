import argparse
import hashlib
import json
import re
from pathlib import Path
from gtts import gTTS

SRC_DIR = Path(__file__).resolve().parents[1]  # script en src/scripts/
AUDIO_DIR = SRC_DIR / "assets" / "audio" / "sentences"


def oracion_completa(ex):
    """Obtiene la oración íntegra. Nunca genera un MP3 de una sola palabra por accidente."""
    for field in ("sentence", "full_sentence", "expected_sentence"):
        if ex.get(field):
            return str(ex[field]).strip()

    prompt = str(ex.get("prompt") or "")
    answer = str(ex.get("answer") or "").strip()
    hueco = r"_{2,}|\{blank\}|\[blank\]|\.{3,}|…+"
    if prompt and answer and re.search(hueco, prompt, flags=re.I):
        return re.sub(hueco, lambda _: answer, prompt, count=1, flags=re.I).strip()

    # Sin frase explícita ni hueco identificable, no sabemos qué pronunciar.
    raise ValueError(
        "No encuentro una oración completa. Incluye 'sentence' en el JSON, "
        "o usa un 'prompt' con ___ y su 'answer'."
    )


def ruta_audio(oracion):
    """Nombre legible + hash: no depende del orden ni de IDs de preguntas."""
    oracion = oracion.strip()
    nombre = re.sub(r"[^a-z0-9]+", "_", oracion.lower()).strip("_")[:42].rstrip("_")
    nombre = nombre or "sentence"
    digest = hashlib.sha1(oracion.encode("utf-8")).hexdigest()[:10]
    return f"audio/sentences/{nombre}_{digest}.mp3"


def leer_ejercicios(ruta):
    with ruta.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for clave in ("exercises", "sentences", "oraciones"):
            if isinstance(data.get(clave), list):
                return data[clave]
    raise ValueError(
        "JSON no reconocido. Esperaba una lista o {'exercises': [...]}, "
        "{'sentences': [...]}, {'oraciones': [...]}."
    )


def elegir_json(entrada):
    if entrada:
        p = Path(entrada)
        if p.is_file():
            return p
        raise FileNotFoundError(f"No existe el JSON: {p}")
    for nombre in ("sentences.json", "sentencias.json", "oraciones.json"):
        p = SRC_DIR / "data" / nombre
        if p.is_file():
            return p
    raise FileNotFoundError(
        "No hallé el JSON en src/data/. Usa --json src/data/EL_NOMBRE_REAL.json"
    )


def main():
    parser = argparse.ArgumentParser(description="Genera audio MP3 de oraciones para Saylo")
    parser.add_argument("--json", help="Ruta real al JSON de oraciones")
    parser.add_argument("--force", action="store_true", help="Sobrescribe MP3 existentes")
    parser.add_argument("--slow", action="store_true", help="Pronunciación un poco más lenta")
    args = parser.parse_args()

    ruta_json = elegir_json(args.json)
    ejercicios = leer_ejercicios(ruta_json)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Leyendo: {ruta_json}")
    print(f"Guardando en: {AUDIO_DIR}")
    print(f"Ejercicios encontrados: {len(ejercicios)}\n")

    ok, existing, errors = 0, 0, []
    nombres_generados = set()
    for num, ejercicio in enumerate(ejercicios, start=1):
        etiqueta = str(ejercicio.get("id", num)) if isinstance(ejercicio, dict) else str(num)
        try:
            if not isinstance(ejercicio, dict):
                raise ValueError("El ejercicio no es un objeto JSON")
            oracion = oracion_completa(ejercicio)
            src = ruta_audio(oracion)
            archivo = SRC_DIR / "assets" / Path(src)
            if src in nombres_generados:
                print(f"DUPLICADA {etiqueta}: {oracion!r} -> {src}")
                continue
            nombres_generados.add(src)
            if archivo.exists() and not args.force:
                print(f"SKIP {etiqueta}: {archivo.name}")
                existing += 1
                continue
            # Escribir primero en temporal para no dejar MP3 truncados ante fallos.
            temporal = archivo.with_suffix(".mp3.part")
            try:
                gTTS(text=oracion, lang="en", tld="com", slow=args.slow).save(str(temporal))
                temporal.replace(archivo)
            finally:
                temporal.unlink(missing_ok=True)
            print(f"OK {etiqueta}: {oracion} -> {archivo.name}")
            ok += 1
        except Exception as error:
            errors.append((etiqueta, str(error)))
            print(f"ERROR {etiqueta}: {error}")

    print(f"\nGenerados: {ok} | Ya existentes: {existing} | Errores: {len(errors)}")
    if errors:
        print("Revisa estos ejercicios:")
        for etiqueta, error in errors:
            print(f"  {etiqueta}: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
