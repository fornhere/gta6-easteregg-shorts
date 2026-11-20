#!/usr/bin/env python3
"""Word-timed transcript with faster-whisper (bundled default for motor.sh).

Interface (kept stable so you can swap in your own script):
    python transkript.py <audio|video> --out <dir> --dil <lang>
Writes <dir>/<name>.json ({"words": [{"word", "start", "end"}], "segments": [...], "text": ...}), .srt and .txt.

Runs on an NVIDIA GPU when available (motor.sh adds the CUDA libraries), otherwise on CPU.
Model: GTA6_WHISPER_MODEL (default: large-v3 on GPU, small on CPU). GTA6_WHISPER_CPU=1 forces CPU.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys

# The CUDA .so files ship inside pip packages; restart once with LD_LIBRARY_PATH so the loader finds them.
if not os.environ.get("GTA6_CUDA_HAZIR"):
    try:
        import nvidia.cublas
        import nvidia.cudnn
        libs = [str(pathlib.Path(p) / "lib") for m in (nvidia.cublas, nvidia.cudnn) for p in m.__path__]
        env = dict(os.environ, GTA6_CUDA_HAZIR="1",
                   LD_LIBRARY_PATH=":".join(libs + [os.environ.get("LD_LIBRARY_PATH", "")]))
        os.execve(sys.executable, [sys.executable, *sys.argv], env)
    except ImportError:
        pass  # no CUDA packages (no GPU / macOS): CPU below

import numpy as np
from faster_whisper import WhisperModel


def model_yukle(cihaz):
    secim = os.environ.get("GTA6_WHISPER_MODEL")
    if cihaz == "cuda":
        return WhisperModel(secim or "large-v3", device="cuda", compute_type="int8_float32")
    return WhisperModel(secim or "small", device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)


def cozumle(ses, dil, cihaz):
    model = model_yukle(cihaz)
    segs, _ = model.transcribe(ses, language=dil, beam_size=5, word_timestamps=True,
                               vad_filter=True, condition_on_previous_text=False)
    return list(segs)  # the GPU runs lazily: errors surface here, not at load time


def srt_zaman(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("girdi")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dil", default="en")
    a = ap.parse_args()

    kaynak = pathlib.Path(a.girdi).expanduser().resolve()
    out = pathlib.Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    ham = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(kaynak), "-map", "0:a:0",
                                   "-ac", "1", "-ar", "16000", "-f", "f32le", "-"])
    ses = np.frombuffer(ham, dtype=np.float32)

    cihaz = "cpu" if os.environ.get("GTA6_WHISPER_CPU") else "cuda"
    try:
        segs = cozumle(ses, a.dil, cihaz)
    except Exception as e:  # no GPU, no CUDA libraries, out of memory ...
        if cihaz == "cpu":
            raise
        print(f"GPU kullanılamadı ({type(e).__name__}: {str(e)[:120]}); CPU'ya geçiliyor", file=sys.stderr)
        cihaz = "cpu"
        segs = cozumle(ses, a.dil, cihaz)
    segments, words = [], []
    for i, s in enumerate(segs):
        segments.append({"id": i, "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()})
        for w in s.words or []:
            words.append({"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)})

    ad = kaynak.stem
    veri = {"language": a.dil, "duration": round(len(ses) / 16000, 3),
            "text": " ".join(s["text"] for s in segments), "segments": segments, "words": words}
    (out / f"{ad}.json").write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / f"{ad}.srt").write_text("\n".join(
        f"{s['id'] + 1}\n{srt_zaman(s['start'])} --> {srt_zaman(s['end'])}\n{s['text']}\n" for s in segments),
        encoding="utf-8")
    (out / f"{ad}.txt").write_text(veri["text"] + "\n", encoding="utf-8")
    print(json.dumps({"cikti": str(out / ad), "cihaz": cihaz, "kelime": len(words)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
