from __future__ import annotations

from app.config.defaults import build_default_settings
from app.models.settings import AppSettings
from app.storage.settings_repository import SettingsRepository


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self.repository = repository

    def load(self) -> AppSettings:
        settings = self.repository.load()
        if settings is None:
            settings = build_default_settings()
            self.repository.save(settings)
        return settings

    def save(self, settings: AppSettings) -> AppSettings:
        self.repository.save(settings)
        return settings

    def get_defaults(self) -> AppSettings:
        return build_default_settings()

    def reset(self) -> AppSettings:
        settings = build_default_settings()
        self.repository.save(settings)
        return settings
