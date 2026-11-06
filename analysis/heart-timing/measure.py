"""提供された2動画の心臓膨張を原寸で再計測する開発用スクリプト。

必要: Python3、numpy、ffmpeg/ffprobe。スマホの自動操作からは呼ばない。
実行: python3 analysis/heart-timing/measure.py /path/to/videos /tmp/heart-events.csv
動画はGitへ保存しない。既知動画の色閾値であり、一般的なゲーム認識器ではない。
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

SOURCES = (
    ("stationary", "ScreenRecording_11-06-2026 11-26-58_1.mp4",
     "11c12501da8f25b404aba9ef2dd4cfd90e5be0d52867b175690d0f9e6fde4a63", 1.0, 18.9),
    ("walking", "ScreenRecording_11-06-2026 11-54-10_1.mp4",
     "6bc9c7a28196ad8074a8dce4827ff3baf32c67a811c57d31a75f716b5c4b5e8c", 0.7, 9.4),
)
WIDTH, HEIGHT = 1108, 512


def measure(video_dir):
    all_events, summaries = [], []
    for source, name, digest, lo, hi in SOURCES:
        video = video_dir / name
        if hashlib.sha256(video.read_bytes()).hexdigest() != digest:
            raise ValueError("source hash mismatch: " + name)
        meta = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_frames",
            "-show_entries", "stream=width,height,avg_frame_rate:frame=best_effort_timestamp_time",
            "-of", "json", str(video)]))
        stream = meta["streams"][0]
        if (stream["width"], stream["height"], stream["avg_frame_rate"]) != (WIDTH, HEIGHT, "30/1"):
            raise ValueError("unexpected native video geometry/rate")
        pts = [float(frame["best_effort_timestamp_time"]) for frame in meta["frames"]]
        process = subprocess.Popen([
            "ffmpeg", "-v", "error", "-i", str(video), "-map", "0:v:0", "-f", "rawvideo",
            "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        frames = []
        try:
            for index, timestamp in enumerate(pts):
                raw = process.stdout.read(WIDTH * HEIGHT * 3)
                if len(raw) != WIDTH * HEIGHT * 3:
                    raise ValueError("truncated decoded frame")
                image = np.frombuffer(raw, dtype=np.uint8).reshape(HEIGHT, WIDTH, 3)
                # 中央の淡いピンク点ではなく、膨張する赤い本体を測る。
                roi = image[400:502, 506:598].astype(np.int16)
                r, g, b = roi[:, :, 0], roi[:, :, 1], roi[:, :, 2]
                red_area = int(((r >= 100) & (10*g <= 7*r) & (10*b <= 7*r)).sum())
                # 独立な色域でも同じ膨張フレームになることを照合する。
                lower = image[450:504, 520:588].astype(np.int16)
                r, g, b = lower[:, :, 0], lower[:, :, 1], lower[:, :, 2]
                warm_area = int(((r >= 100) & (g >= 50) & (b >= 50) & (abs(g-b) <= 30)
                                 & (4*r > 5*g) & (4*r > 5*b)).sum())
                if lo <= timestamp <= hi and (red_area >= 2300) != (warm_area >= 400):
                    raise ValueError("independent colour masks disagree")
                frames.append((timestamp, red_area >= 2300))
            if process.stdout.read(1):
                raise ValueError("unexpected extra frame bytes")
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.wait(timeout=10)
        if process.returncode:
            raise ValueError("ffmpeg decode failed")
        groups = []
        for index, (timestamp, expanded) in enumerate(frames):
            if expanded and lo <= timestamp <= hi:
                if not groups or index != groups[-1][-1]+1:
                    groups.append([])
                groups[-1].append(index)
        events = []
        for pulse, indices in enumerate(groups, 1):
            first, last = indices[0], indices[-1]
            if first == 0 or last+1 == len(frames) or frames[first-1][1] or frames[last+1][1]:
                raise ValueError("partial pulse at analysis boundary")
            events.append({
                "video": source, "pulse": pulse, "first_frame": first, "last_frame": last,
                "onset_after_s": pts[first-1], "onset_by_s": pts[first],
                "offset_after_s": pts[last], "offset_by_s": pts[last+1],
                "observed_mid_s": (pts[first]+pts[last])/2,
                "expanded_frames": len(indices), "nominal_display_s": len(indices)/30,
            })
        mids = np.array([event["observed_mid_s"] for event in events])
        period, epoch = np.polyfit(np.arange(len(mids)), mids, 1)
        summaries.append({"video": source, "source_sha256": digest, "native_size": [WIDTH, HEIGHT],
                          "fps": 30, "analysis_interval_s": [lo, hi], "pulses": len(events),
                          "period_s": float(period), "bpm": float(60/period),
                          "first_fitted_mid_s": float(epoch),
                          "max_mid_residual_s": float(max(abs(mids-(epoch+period*np.arange(len(mids))))))})
        all_events.extend(events)
    return all_events, summaries


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: measure.py VIDEO_DIRECTORY OUTPUT_CSV")
    events, summaries = measure(Path(sys.argv[1]))
    output = Path(sys.argv[2])
    with output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(events[0]))
        writer.writeheader()
        for event in events:
            writer.writerow({key: format(value, ".6f") if isinstance(value, float) else value
                             for key, value in event.items()})
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
