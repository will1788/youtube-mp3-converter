# backend/tests/conftest.py
"""
Configurações e fixtures para os testes
"""
import pytest
import os
import sys
import shutil
from pathlib import Path

# Adiciona o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app, get_converter_service
from app.converter import ConverterService


@pytest.fixture
def test_downloads_dir(tmp_path):
    """Cria diretório temporário para downloads de teste"""
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    return downloads


@pytest.fixture
def test_temp_dir(tmp_path):
    """Cria diretório temporário para arquivos temp"""
    temp = tmp_path / "temp"
    temp.mkdir()
    return temp


@pytest.fixture
def converter_service(test_downloads_dir, test_temp_dir):
    """Cria instância do serviço de conversão para testes"""
    service = ConverterService(
        downloads_dir=str(test_downloads_dir), temp_dir=str(test_temp_dir)
    )
    yield service
    # Cleanup
    service.cleanup_all()


@pytest.fixture
def client(converter_service):
    """Cliente de teste para a API"""

    def get_test_converter():
        return converter_service

    app.dependency_overrides[get_converter_service] = get_test_converter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def valid_youtube_url():
    """URL válida do YouTube para testes"""
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def invalid_youtube_url():
    """URL inválida para testes"""
    return "https://invalid-url.com/watch"


@pytest.fixture
def sample_urls():
    """Lista de URLs de exemplo"""
    return [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=9bZkp7q19f0",
        "https://youtu.be/kJQP7kiw5Fk",
    ]
