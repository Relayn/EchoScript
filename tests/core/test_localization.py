"""
Юнит-тесты для модуля локализации (app.core.localization).
"""

from unittest.mock import MagicMock, patch

# Мы импортируем модуль целиком, чтобы было удобнее патчить его зависимости
from app.core import localization


@patch("app.core.localization.load_language", return_value="en_US")
@patch("locale.getdefaultlocale")
def test_get_active_language_from_config(
    mock_locale: MagicMock, mock_load_lang: MagicMock
) -> None:
    """
    Тест: Язык успешно загружается из конфига (высший приоритет).
    """
    # Act
    lang = localization.get_active_language()

    # Assert
    assert lang == ["en_US"]
    mock_load_lang.assert_called_once()
    # Проверяем, что getdefaultlocale не был вызван, т.к. сработал конфиг
    mock_locale.assert_not_called()


@patch("app.core.localization.load_language", return_value=None)
@patch("locale.getdefaultlocale", return_value=("ru_RU", "cp1251"))
def test_get_active_language_from_system_locale(
    mock_locale: MagicMock, mock_load_lang: MagicMock
) -> None:
    """
    Тест: Язык определяется из системной локали, если конфиг пуст.
    """
    # Act
    lang = localization.get_active_language()

    # Assert
    assert lang == ["ru"]
    mock_load_lang.assert_called_once()
    mock_locale.assert_called_once()


@patch("app.core.localization.load_language", return_value=None)
@patch("locale.getdefaultlocale", side_effect=ValueError("Locale error"))
def test_get_active_language_fallback_on_error(
    mock_locale: MagicMock, mock_load_lang: MagicMock
) -> None:
    """
    Тест: Возвращается None, если и конфиг пуст, и локаль вызвала ошибку.
    """
    # Act
    lang = localization.get_active_language()

    # Assert
    assert lang is None
    mock_load_lang.assert_called_once()
    mock_locale.assert_called_once()


@patch("app.core.localization.load_language", return_value=None)
@patch("locale.getdefaultlocale", return_value=(None, None))
def test_get_active_language_fallback_on_none_locale(
    mock_locale: MagicMock, mock_load_lang: MagicMock
) -> None:
    """
    Тест: Возвращается None, если системная локаль не определена (возвращает None).
    """
    # Act
    lang = localization.get_active_language()

    # Assert
    assert lang is None
