import argparse
import hashlib
import json
import re
from pathlib import Path
from gtts import gTTS

SRC_DIR = Path(__file__).resolve().parents[1]
AUDIO_DIR = SRC_DIR / "assets" / "audio" / "phrases"


def phrase_text(ex):
    for field in ("answer", "phrase", "text"):
        if ex.get(field):
            return str(ex[field]).strip()
    raise ValueError("No encuentro la frase. Incluye 'answer' en el JSON.")


def ruta_audio(texto):
    texto = texto.strip()
    nombre = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")[:42].rstrip("_")
    nombre = nombre or "phrase"
    digest = hashlib.sha1(texto.encode("utf-8")).hexdigest()[:10]
    return f"audio/phrases/{nombre}_{digest}.mp3"


def leer_items(ruta):
    with ruta.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, data, None
    if isinstance(data, dict):
        for clave in ("phrases", "exercises"):
            if isinstance(data.get(clave), list):
                return data[clave], data, clave
    raise ValueError("JSON no reconocido. Esperaba una lista o {'phrases': [...]}.")


def elegir_json(entrada):
    if entrada:
        p = Path(entrada)
        if p.is_file():
            return p
        raise FileNotFoundError(f"No existe el JSON: {p}")
    for nombre in ("phrases.json", "frases.json"):
        p = SRC_DIR / "data" / nombre
        if p.is_file():
            return p
    raise FileNotFoundError("No hallé el JSON en src/data/. Usa --json src/data/EL_NOMBRE_REAL.json")


def main():
    parser = argparse.ArgumentParser(description="Genera audio MP3 de frases para Saylo")
    parser.add_argument("--json", help="Ruta al JSON de phrases")
    parser.add_argument("--force", action="store_true", help="Sobrescribe MP3 existentes")
    parser.add_argument("--slow", action="store_true", help="Pronunciación más lenta")
    args = parser.parse_args()

    ruta_json = elegir_json(args.json)
    items, raw, key = leer_items(ruta_json)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Leyendo: {ruta_json}")
    print(f"Guardando en: {AUDIO_DIR}")
    print(f"Frases encontradas: {len(items)}\n")

    backup = ruta_json.with_suffix(ruta_json.suffix + ".bak")
    if not backup.exists():
        backup.write_text(ruta_json.read_text(encoding="utf-8"), encoding="utf-8")

    ok, existing, errors = 0, 0, []
    nombres_generados = set()
    for num, item in enumerate(items, start=1):
        etiqueta = str(item.get("id", num)) if isinstance(item, dict) else str(num)
        try:
            if not isinstance(item, dict):
                raise ValueError("El ejercicio no es un objeto JSON")
            texto = phrase_text(item)
            src = ruta_audio(texto)
            archivo = SRC_DIR / "assets" / Path(src)
            item["audio"] = src
            if src in nombres_generados:
                print(f"DUPLICADA {etiqueta}: {texto!r} -> {src}")
                continue
            nombres_generados.add(src)
            if archivo.exists() and not args.force:
                print(f"SKIP {etiqueta}: {archivo.name}")
                existing += 1
                continue
            temporal = archivo.with_suffix(".mp3.part")
            try:
                gTTS(text=texto, lang="en", tld="com", slow=args.slow).save(str(temporal))
                temporal.replace(archivo)
            finally:
                temporal.unlink(missing_ok=True)
            print(f"OK {etiqueta}: {texto} -> {archivo.name}")
            ok += 1
        except Exception as error:
            errors.append((etiqueta, str(error)))
            print(f"ERROR {etiqueta}: {error}")

    if isinstance(raw, dict) and key:
        raw[key] = items
    elif isinstance(raw, list):
        raw = items
    ruta_json.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nGenerados: {ok} | Ya existentes: {existing} | Errores: {len(errors)}")
    if errors:
        print("Revisa estos ejercicios:")
        for etiqueta, error in errors:
            print(f"  {etiqueta}: {error}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
