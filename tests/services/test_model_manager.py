"""
Юнит-тесты для ModelManager, отвечающего за загрузку моделей.
"""
import hashlib
import os
from unittest.mock import patch, MagicMock

import pytest

from app.core.models import ModelSize
from app.services.model_manager import ModelManager


@pytest.fixture
def model_manager(tmp_path) -> ModelManager:
    """Фикстура для создания экземпляра ModelManager с временной директорией."""
    # Используем monkeypatch, чтобы переопределить корневую директорию для кэша
    with patch("app.services.model_manager.ModelManager._get_download_root", return_value=str(tmp_path)):
        manager = ModelManager(ModelSize.TINY)
        return manager


def test_ensure_model_is_available_already_downloaded_and_valid(model_manager, tmp_path):
    """
    Тест: модель уже существует и ее контрольная сумма верна.
    Ожидание: новая загрузка не происходит.
    """
    # Arrange
    dummy_content = b"dummy model content"
    dummy_hash = hashlib.sha256(dummy_content).hexdigest()
    model_path = tmp_path / "tiny.pt"
    model_path.write_bytes(dummy_content)

    # Мокаем словарь _MODELS, чтобы подставить наш ожидаемый хеш
    with patch("whisper._MODELS", {"tiny": f"https://example.com/{dummy_hash}/tiny.pt"}):
        with patch.object(model_manager, "_download_model") as mock_download:
            # Act
            result_path = model_manager.ensure_model_is_available()

            # Assert
            mock_download.assert_not_called()  # Загрузка не должна была вызываться
            assert result_path == str(model_path)


def test_ensure_model_is_available_corrupted_file(model_manager, tmp_path):
    """
    Тест: файл модели существует, но его контрольная сумма неверна.
    Ожидание: старый файл удаляется, запускается новая загрузка.
    """
    # Arrange
    (tmp_path / "tiny.pt").write_bytes(b"corrupted content")
    correct_hash = "a" * 64  # Заведомо неверный хеш

    with patch("whisper._MODELS", {"tiny": f"https://example.com/{correct_hash}/tiny.pt"}):
        with patch.object(model_manager, "_download_model") as mock_download:
            with patch("os.remove") as mock_remove:
                # Act
                model_manager.ensure_model_is_available()

                # Assert
                mock_remove.assert_called_once_with(str(tmp_path / "tiny.pt"))
                mock_download.assert_called_once()


@patch("urllib.request.urlopen")
def test_download_model_atomic_operation(mock_urlopen, model_manager, tmp_path):
    """
    Тест: _download_model выполняет атомарную загрузку (скачивание в .part, затем переименование).
    """
    # Arrange
    dummy_content = b"newly downloaded content"
    part_path = str(tmp_path / "tiny.pt.part")
    final_path = str(tmp_path / "tiny.pt")

    # Настраиваем мок для urlopen, чтобы он имитировал ответ сервера
    mock_response = MagicMock()
    mock_response.read.side_effect = [dummy_content, b""]
    mock_response.info.return_value = {"Content-Length": len(dummy_content)}
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Act
    model_manager._download_model()

    # Assert
    # Проверяем, что временный .part файл был переименован в финальный,
    # а сам .part файл больше не существует.
    assert os.path.exists(part_path) is False
    assert os.path.exists(final_path) is True
    assert (tmp_path / "tiny.pt").read_bytes() == dummy_content