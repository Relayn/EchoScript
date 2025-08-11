"""
Модуль для управления локализацией (i18n) приложения.

Этот модуль инициализирует gettext и предоставляет готовую функцию `_`
для использования в других частях приложения.
"""

import gettext
import locale
import os

from app.core.config import load_language

DOMAIN = "messages"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")


def get_active_language() -> list[str] | None:
    """
    Определяет активный язык в следующем порядке приоритета:
    1. Язык, сохраненный в конфиге пользователя.
    2. Язык по умолчанию операционной системы.
    3. None (будет использован язык из исходного кода).
    """
    # 1. Проверяем сохраненный конфиг
    saved_lang = load_language()
    if saved_lang:
        return [saved_lang]

    # 2. Если в конфиге ничего нет, определяем язык системы
    try:
        system_lang, _ = locale.getdefaultlocale()
        if system_lang:
            return [system_lang.split("_")[0]]
    except Exception:  # nosec B110
        pass  # Игнорируем ошибки определения локали

    # 3. Возвращаем None, если ничего не найдено
    return None


# Инициализируем переводчик один раз при импорте модуля.
active_languages = get_active_language()

# gettext.translation возвращает объект-переводчик.
# fallback=True означает, что если перевод не найден, вернется исходная строка.
translation = gettext.translation(
    DOMAIN, localedir=LOCALE_DIR, languages=active_languages, fallback=True
)

# Предоставляем функцию `gettext` из этого объекта под стандартным именем `_`
# для использования в других модулях.
_ = translation.gettext
