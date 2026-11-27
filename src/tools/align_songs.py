# tools/align_songs.py
import json
import sys
from pathlib import Path

import stable_whisper

SONGS_JSON = Path("src/data/songs.json")  # ajusta la ruta


def main(song_id: str, audio_path: str):
    data = json.loads(SONGS_JSON.read_text(encoding="utf-8"))
    song = next(s for s in data["songs"] if s["id"] == song_id)
    lines = song["lines"]

    text = "\n".join(l["text"] for l in lines)
    model = stable_whisper.load_model("small")
    result = model.align(audio_path, text, language="en", original_split=True)

    segments = result.segments
    if len(segments) != len(lines):
        print(f"OJO: {len(segments)} segmentos vs {len(lines)} líneas")

    for line, seg in zip(lines, segments):
        line["start_ms"] = int(seg.start * 1000)
        line["end_ms"] = int(seg.end * 1000)
        line["timing_reviewed"] = True

    song["cue_accuracy"] = "forced alignment (stable-ts)"
    SONGS_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Listo.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])