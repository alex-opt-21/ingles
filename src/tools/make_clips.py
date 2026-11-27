import json
import subprocess
import sys
from pathlib import Path

try: 
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass

SONGS_JSON = Path("src/data/songs.json")
ASSETS = Path("src/assets")


def main(song_id: str, pad_before: int = 600, pad_after: int = 400):
    data = json.loads(SONGS_JSON.read_text(encoding="utf-8"))
    song = next(s for s in data["songs"] if s["id"] == song_id)

    source = ASSETS / song["audio"]
    rel_dir = Path("audio/music/clips") / song_id
    out_dir = ASSETS / rel_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, line in enumerate(song["lines"], start=1):
        start = max(0, line["start_ms"] - pad_before) / 1000
        end = (line["end_ms"] + pad_after) / 1000
        name = f"{i:03d}.mp3"
        # -ss antes de -i + recodificación = corte preciso al milisegundo.
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
            "-i", str(source),
            "-c:a", "libmp3lame", "-b:a", "192k",
            str(out_dir / name),
        ]
        subprocess.run(cmd, check=True)
        line["clip"] = (rel_dir / name).as_posix()
        print(f"{name}: {start:.2f}s -> {end:.2f}s  {line['text'][:40]}")

    SONGS_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Listo. Clips en", out_dir)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], *(int(a) for a in args[1:3]))