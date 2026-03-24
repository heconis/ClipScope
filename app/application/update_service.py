from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.constants import DEFAULT_RELEASES_URL, UPDATE_INFO_URL
from app.models.update import UpdateCheckResult


@dataclass(slots=True)
class _VersionInfo:
    latest_version: str
    download_url: str
    release_notes_url: str | None
    message: str | None


class UpdateService:
    def __init__(self, update_info_url: str = UPDATE_INFO_URL, timeout_seconds: float = 3.0) -> None:
        self.update_info_url = update_info_url
        self.timeout_seconds = timeout_seconds

    def check_for_updates(self, current_version: str) -> UpdateCheckResult:
        info = self._fetch_version_info()
        latest_tuple = self._parse_version(info.latest_version)
        current_tuple = self._parse_version(current_version)
        return UpdateCheckResult(
            current_version=current_version,
            latest_version=info.latest_version,
            is_update_available=latest_tuple > current_tuple,
            download_url=info.download_url,
            release_notes_url=info.release_notes_url,
            message=info.message,
        )

    def _fetch_version_info(self) -> _VersionInfo:
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = client.get(self.update_info_url)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, dict):
            raise RuntimeError("version.json の形式が不正です。")

        latest_version = str(payload.get("latest_version") or "").strip()
        if not latest_version:
            raise RuntimeError("latest_version が見つかりません。")

        download_url = str(payload.get("download_url") or DEFAULT_RELEASES_URL).strip()
        if not download_url:
            download_url = DEFAULT_RELEASES_URL

        release_notes_url = str(payload.get("release_notes_url") or "").strip() or None
        message = str(payload.get("message") or "").strip() or None
        return _VersionInfo(
            latest_version=latest_version,
            download_url=download_url,
            release_notes_url=release_notes_url,
            message=message,
        )

    @staticmethod
    def _parse_version(version: str) -> tuple[int, int, int]:
        parts = version.strip().split(".")
        if len(parts) != 3:
            raise RuntimeError(f"バージョン形式が不正です: {version}")
        try:
            return tuple(int(part) for part in parts)  # type: ignore[return-value]
        except ValueError as error:
            raise RuntimeError(f"バージョン形式が不正です: {version}") from error
