#!/usr/bin/env python3
"""Extract exact indexed reference frames; no phone connection or input."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name("source_manifest.json").read_text())
    if digest(args.video) != manifest["sha256"]:
        raise SystemExit("Source hash does not match the annotated video")
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
        "-of", "json", str(args.video),
    ]))["streams"][0]
    if (probe["width"], probe["height"], probe["r_frame_rate"]) != (1108, 512, "30/1"):
        raise SystemExit("Unexpected geometry or frame rate; do not stretch/rotate")
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    for item in manifest["reference_frames"]:
        output = args.out / item["filename"]
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-i", str(args.video),
            "-vf", f"select=eq(n\\,{item['frame_index']})", "-frames:v", "1",
            "-fps_mode", "vfr", "-q:v", "2", str(output),
        ], check=True)
        if not output.is_file() or not output.stat().st_size:
            raise SystemExit(f"Frame was not produced: {output.name}")
        results.append({**item, "sha256": digest(output), "bytes": output.stat().st_size})
    (args.out / "extraction.json").write_text(json.dumps({
        "source_sha256": manifest["sha256"], "rotation_degrees": 0,
        "output_dimensions": [1108, 512], "frames": results,
    }, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"extracted": len(results), "output": str(args.out)}))


if __name__ == "__main__":
    main()
