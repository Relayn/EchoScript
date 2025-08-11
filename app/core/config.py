"""
Модуль для управления конфигурацией приложения.

Отвечает за сохранение и загрузку настроек пользователя, таких как
выбранный язык интерфейса.
"""

import os
import pathlib

# Определяем платформо-независимый путь к директории с конфигами
# Например, ~/.config/echoscript/ в Linux или
# C:\Users\User\AppData\Roaming\echoscript в Windows
CONFIG_DIR = pathlib.Path(os.getenv("APPDATA") or os.path.expanduser("~/.config"))
APP_CONFIG_DIR = CONFIG_DIR / "EchoScript"
APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _get_lang_config_path() -> pathlib.Path:
    """Возвращает путь к файлу конфигурации языка."""
    return APP_CONFIG_DIR / "lang.conf"


def save_language(lang_code: str) -> None:
    """Сохраняет выбранный код языка в конфигурационный файл."""
    try:
        _get_lang_config_path().write_text(lang_code, encoding="utf-8")
    except IOError:
        # Не критичная ошибка, просто не сможем сохранить язык
        pass


def load_language() -> str | None:
    """Загружает код языка из конфигурационного файла, если он существует."""
    config_path = _get_lang_config_path()
    if not config_path.exists():
        return None
    try:
        return config_path.read_text(encoding="utf-8").strip()
    except IOError:
        return None
