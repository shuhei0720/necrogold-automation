#!/usr/bin/env python3
"""Reproduce the timing analysis of the supplied 2026-11-05 video.

This is an offline analysis script, not a game controller. Its reference time,
HUD rectangles, and manual shop observations are specific to this recording.
It sends no input to any device. Requires Python 3, numpy, Pillow, and ffmpeg.
"""
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np


def read_exact(stream, count):
    chunks = []
    remaining = count
    while remaining:
        part = stream.read(remaining)
        if not part:
            break
        chunks.append(part)
        remaining -= len(part)
    return b"".join(chunks)


def frame_command(video):
    return ["ffmpeg", "-v", "error", "-i", str(video), "-vf",
            "transpose=2,scale=554:256", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reproduced"))
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / "source_manifest.json").read_text())
    video_name = "ScreenRecording_11-05-2026 11-45-14_1.mp4"
    actual = hashlib.sha256(args.video.read_bytes()).hexdigest()
    if actual != manifest[video_name]["sha256"]:
        raise SystemExit("This script is labelled for a different source video; refusing to reuse its labels.")
    args.out.mkdir(parents=True, exist_ok=True)

    # Take a known pause frame from this source. This is independent of the
    # automation's production templates and production coordinate constants.
    cmd = ["ffmpeg", "-v", "error", "-ss", "17.8", "-i", str(args.video),
           "-frames:v", "1", "-vf", "transpose=2,scale=554:256",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    reference = np.frombuffer(subprocess.check_output(cmd), np.uint8).reshape(256, 554, 3)
    mask = reference[35:61, 216:337].min(2) > 160

    process = subprocess.Popen(frame_command(args.video), stdout=subprocess.PIPE)
    rows = []
    frame_index = 0
    frame_bytes = 554 * 256 * 3
    try:
        while True:
            raw = read_exact(process.stdout, frame_bytes)
            if not raw:
                break
            if len(raw) != frame_bytes:
                raise RuntimeError("Truncated frame from decoder")
            image = np.frombuffer(raw, np.uint8).reshape(256, 554, 3)
            observed = image[35:61, 216:337].min(2) > 160
            overlap = (observed & mask).sum() / max((observed | mask).sum(), 1)
            region = image[2:23, 419:475]
            hearts = ((region[:, :, 0] > 100) & (region[:, :, 1] < 70)
                      & (region[:, :, 2] < 70)).sum()
            timer_ink = (image[240:255, 25:125].min(2) > 120).sum()
            if overlap > .80:
                kind = "pause"
            elif hearts > 50 and timer_ink > 40 and frame_index >= 228:
                kind = "floor"
            elif image.mean() > 15:
                kind = "other"
            else:
                kind = "transition"
            rows.append(dict(frame=frame_index, time=round(frame_index / 30, 6),
                             kind=kind, pause_score=round(float(overlap), 3),
                             hearts=int(hearts), timer_ink=int(timer_ink),
                             mean=round(float(image.mean()), 2)))
            frame_index += 1
    finally:
        process.stdout.close()
        return_code = process.wait()
    if return_code:
        raise RuntimeError("ffmpeg failed with status %d" % return_code)

    segments = []
    for row in rows:
        if not segments or segments[-1]["kind"] != row["kind"]:
            segments.append(dict(kind=row["kind"], start_frame=row["frame"],
                                 start=row["time"], end_frame=row["frame"], end=row["time"]))
        else:
            segments[-1]["end_frame"] = row["frame"]
            segments[-1]["end"] = row["time"]
    with (args.out / "frame_metrics.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "segments.json").write_text(json.dumps(segments, indent=2))

    floors = [s for s in segments if s["kind"] == "floor"]
    pauses = [s for s in segments if s["kind"] == "pause"]
    labels = json.loads((base / "shop_observations.json").read_text())["rows"]
    shop_ids = {row["run"] for row in labels if row["category"] == "shop_visible"}
    if len(floors) != len(labels) or len(pauses) != 41:
        raise RuntimeError("Segment counts changed; review labels before calculating statistics")
    cycles, decisions, restart = [], [], []
    for i, floor in enumerate(floors[:-1]):
        pause = next(p for p in pauses if p["start"] > floor["start"])
        restart.append(floors[i + 1]["start"] - pause["start"])
        if i + 1 not in shop_ids:
            cycles.append(floors[i + 1]["start"] - floor["start"])
            decisions.append(pause["start"] - floor["start"])

    def stats(values):
        return dict(n=len(values), minimum_s=min(values), median_s=float(np.median(values)),
                    p95_s=float(np.percentile(values, 95)), maximum_s=max(values))

    summary = dict(frames=len(rows), runs=len(floors), restart_count=len(pauses),
                   shop_count=len(shop_ids), quick_skip_cycle=stats(cycles),
                   quick_skip_to_pause=stats(decisions), restart=stats(restart),
                   goods_visible=stats([row["goods_elapsed_s"] for row in labels
                                        if row["goods_elapsed_s"] is not None]),
                   note="HUD boundaries are frame-derived; shop visibility is manually labelled. "
                        "These are not touch-event latency measurements.")
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
