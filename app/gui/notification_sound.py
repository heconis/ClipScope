from __future__ import annotations

import os
import sys
from pathlib import Path

from app.config.constants import APP_NAME


def play_new_clip_sound() -> bool:
    try:
        import winsound  # Windows only
    except ImportError:
        return False

    sound_path = _resolve_sound_path()
    if sound_path is None:
        return False

    try:
        winsound.PlaySound(
            str(sound_path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except Exception:
        return False
    return True


def _resolve_sound_path() -> Path | None:
    candidates: list[Path] = []

    override = os.getenv("CLIPSCOPE_NOTIFY_SOUND_PATH")
    if override:
        candidates.append(Path(override).expanduser())

    appdata_dir = os.getenv("APPDATA")
    if appdata_dir:
        candidates.append(Path(appdata_dir) / APP_NAME / "notify.wav")

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "assets" / "sound" / "notify.wav")
        candidates.append(Path(sys.executable).resolve().parent / "notify.wav")

    candidates.append(Path(__file__).resolve().parents[2] / "assets" / "sound" / "notify.wav")

    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved

    return None
