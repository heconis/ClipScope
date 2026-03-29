from __future__ import annotations

from app.models.clip import ClipItem


def build_player_page(clip: ClipItem | None, updated_at: str | None = None) -> str:
    if clip is None:
        return """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <style>
    html, body {
      margin: 0;
      width: 100%;
      height: 100%;
      background: transparent;
      overflow: hidden;
      font-family: sans-serif;
    }
    .empty {
      width: 100%;
      height: 100%;
      display: grid;
      place-items: center;
      color: #6b7280;
      font-size: 18px;
    }
  </style>
</head>
<body>
  <div class="empty"></div>
  <script>
    async function checkClipChange() {
      try {
        const response = await fetch('/api/player-state', { cache: 'no-store' });
        const data = await response.json();
        if (data.clip_id) {
          window.location.reload();
        }
      } catch (error) {
        console.error('player polling failed', error);
      }
    }

    setInterval(checkClipChange, 1000);
  </script>
</body>
</html>
"""

    embed_url = (
        "https://clips.twitch.tv/embed"
        f"?clip={clip.clip_id}&parent=127.0.0.1&autoplay=true&muted=false"
    )
    duration_ms = int(max(0.0, clip.duration_seconds) * 1000)

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <style>
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: transparent;
    }}
    #stage {{
      width: 100%;
      height: 100%;
      opacity: 0;
      transition: opacity 260ms ease;
      will-change: opacity;
    }}
    #stage.visible {{
      opacity: 1;
    }}
    #stage.fade-out {{
      opacity: 0;
    }}
    iframe {{
      width: 100%;
      height: 100%;
      border: 0;
    }}
  </style>
</head>
<body>
  <div id="stage">
    <iframe id="player-frame" src="{embed_url}" allowfullscreen="true" scrolling="no"></iframe>
  </div>
  <script>
    const currentClipId = {clip.clip_id!r};
    const currentUpdatedAt = {updated_at!r};
    const clipDurationMs = {duration_ms};
    const playerStatePollMs = 250;
    const manualStopFadeDurationMs = 320;
    const stage = document.getElementById('stage');
    const playerFrame = document.getElementById('player-frame');
    let fadeOutScheduled = false;
    let selectionClearScheduled = false;
    let manualStopInProgress = false;

    requestAnimationFrame(() => {{
      stage.classList.add('visible');
    }});

    function scheduleFadeOut() {{
      if (fadeOutScheduled || clipDurationMs <= 0) return;
      fadeOutScheduled = true;
      // Twitch iframe playback can start a bit later than page load.
      // Keep a safety margin to avoid fading out too early.
      const fadeOutAtMs = Math.max(800, clipDurationMs + 1600);
      setTimeout(() => {{
        stage.classList.add('fade-out');
      }}, fadeOutAtMs);
    }}

    function scheduleSelectionClear() {{
      if (selectionClearScheduled || clipDurationMs <= 0) return;
      selectionClearScheduled = true;
      const clearAtMs = Math.max(1100, clipDurationMs + 1900);
      setTimeout(async () => {{
        try {{
          await fetch('/api/clear-selection', {{
            method: 'POST',
            cache: 'no-store',
          }});
        }} catch (error) {{
          console.error('clear selection failed', error);
        }}
      }}, clearAtMs);
    }}

    function fadeOutToEmpty() {{
      if (manualStopInProgress) return;
      manualStopInProgress = true;
      stage.classList.add('fade-out');
      setTimeout(() => {{
        window.location.replace('/obs-player');
      }}, manualStopFadeDurationMs);
    }}

    playerFrame.addEventListener('load', scheduleFadeOut, {{ once: true }});
    playerFrame.addEventListener('load', scheduleSelectionClear, {{ once: true }});
    // Fallback in case load event is delayed.
    setTimeout(scheduleFadeOut, 2500);
    setTimeout(scheduleSelectionClear, 2500);

    async function checkClipChange() {{
      try {{
        const response = await fetch('/api/player-state', {{ cache: 'no-store' }});
        const data = await response.json();
        const selectionCleared = !data.clip_id;
        const clipChanged = Boolean(data.clip_id && data.clip_id !== currentClipId);
        const reselectionChanged =
          Boolean(data.clip_id && data.clip_id === currentClipId) &&
          (
            (currentUpdatedAt && data.updated_at && data.updated_at !== currentUpdatedAt) ||
            (!currentUpdatedAt && data.updated_at)
          );

        if (selectionCleared) {{
          fadeOutToEmpty();
          return;
        }}

        if (clipChanged || reselectionChanged) {{
          window.location.reload();
        }}
      }} catch (error) {{
        console.error('player polling failed', error);
      }}
    }}

    setInterval(checkClipChange, playerStatePollMs);
  </script>
</body>
</html>
"""
