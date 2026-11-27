from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import stable_whisper

PAD_BEFORE_S = 0.10   # margen al cortar cada clip
PAD_AFTER_S = 0.25
GAP_NEW_GROUP_S = 2.0  # sin letra: una pausa mayor a esto abre un grupo nuevo


def parse_lyrics(path: Path) -> tuple[list[str], list[str]]:
    """Devuelve (líneas, grupo_de_cada_línea)."""
    lines, groups, current = [], [], "Part 1"
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = re.fullmatch(r"\[(.+?)\]", raw)
        if m:
            current = m.group(1).strip()
        else:
            lines.append(raw)
            groups.append(current)
    return lines, groups


def cut_clip(audio: Path, start_s: float, end_s: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    start = max(0.0, start_s - PAD_BEFORE_S)
    duration = (end_s + PAD_AFTER_S) - start
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}",
         "-t", f"{duration:.3f}", "-i", str(audio),
         "-c:a", "libmp3lame", "-q:a", "4", str(out)],
        check=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="id de la canción en songs.json")
    ap.add_argument("--json", default="src/data/songs.json")
    ap.add_argument("--assets", default="src/assets",
                    help="carpeta base donde viven las rutas 'audio/...'")
    ap.add_argument("--lyrics", help="txt con tu letra (opcional)")
    ap.add_argument("--model", default="small")
    args = ap.parse_args()

    json_path = Path(args.json)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    song = next((s for s in data["songs"] if s.get("id") == args.id), None)
    if song is None:
        raise SystemExit(f"No existe la canción '{args.id}' en {json_path}")

    assets = Path(args.assets)
    audio = assets / song["audio"]
    if not audio.exists():
        raise SystemExit(f"No encuentro el audio: {audio}")

    model = stable_whisper.load_model(args.model)

    if args.lyrics:
        texts, groups = parse_lyrics(Path(args.lyrics))
        result = model.align(
            str(audio), "\n".join(texts), language="en", original_split=True
        )
        segments = list(result.segments)
        if len(segments) != len(texts):
            print(f"Aviso: {len(texts)} líneas de letra pero {len(segments)} "
                  "segmentos alineados. Revisa el resultado.")
        texts = [s.text.strip() for s in segments] if len(segments) != len(texts) else texts
        if len(groups) != len(segments):
            groups = (groups + [groups[-1]] * len(segments))[:len(segments)]
    else:
        result = model.transcribe(str(audio), language="en")
        segments = list(result.segments)
        texts = [s.text.strip() for s in segments]
        groups, n, prev_end = [], 1, None
        for s in segments:
            if prev_end is not None and s.start - prev_end > GAP_NEW_GROUP_S:
                n += 1
            groups.append(f"Part {n}")
            prev_end = s.end

    clips_rel = Path("audio/music/clips") / args.id
    lines = []
    for i, (seg, text, group) in enumerate(zip(segments, texts, groups), start=1):
        clip_rel = clips_rel / f"{i:03d}.mp3"
        cut_clip(audio, seg.start, seg.end, assets / clip_rel)
        lines.append({
            "text": text,
            "start_ms": int(round(seg.start * 1000)),
            "group": group,
            "timing_reviewed": False,   # cámbialo a true cuando lo revises
            "end_ms": int(round(seg.end * 1000)),
            "clip": clip_rel.as_posix(),
        })

    song["lines"] = lines
    if segments:
        song["duration_ms"] = song.get("duration_ms") or int(round(segments[-1].end * 1000))
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Listo: {len(lines)} líneas guardadas en {json_path}")


if __name__ == "__main__":
    main()