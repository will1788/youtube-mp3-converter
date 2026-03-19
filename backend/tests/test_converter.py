# backend/tests/test_converter.py
"""
Testes TDD para o serviço de conversão
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import asyncio

from app.converter import ConverterService, ConversionTask, ConversionStatus
from app.utils import validate_youtube_url, sanitize_filename, extract_video_id


class TestYouTubeURLValidation:
    """Testes para validação de URLs do YouTube"""

    def test_valid_youtube_url_standard(self):
        """Deve aceitar URL padrão do YouTube"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert validate_youtube_url(url) is True

    def test_valid_youtube_url_short(self):
        """Deve aceitar URL curta do YouTube (youtu.be)"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert validate_youtube_url(url) is True

    def test_valid_youtube_url_with_playlist(self):
        """Deve aceitar URL com parâmetros de playlist"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest"
        assert validate_youtube_url(url) is True

    def test_valid_youtube_url_mobile(self):
        """Deve aceitar URL mobile do YouTube"""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        assert validate_youtube_url(url) is True

    def test_invalid_url_empty(self):
        """Deve rejeitar URL vazia"""
        assert validate_youtube_url("") is False

    def test_invalid_url_none(self):
        """Deve rejeitar URL None"""
        assert validate_youtube_url(None) is False

    def test_invalid_url_other_domain(self):
        """Deve rejeitar URLs de outros domínios"""
        url = "https://vimeo.com/123456"
        assert validate_youtube_url(url) is False

    def test_invalid_url_malformed(self):
        """Deve rejeitar URLs malformadas"""
        url = "not-a-url"
        assert validate_youtube_url(url) is False

    def test_invalid_url_youtube_without_video_id(self):
        """Deve rejeitar URL do YouTube sem ID de vídeo"""
        url = "https://www.youtube.com/watch"
        assert validate_youtube_url(url) is False


class TestVideoIDExtraction:
    """Testes para extração do ID do vídeo"""

    def test_extract_id_standard_url(self):
        """Deve extrair ID de URL padrão"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_id_short_url(self):
        """Deve extrair ID de URL curta"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_id_with_timestamp(self):
        """Deve extrair ID ignorando timestamp"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=60"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_id_invalid_url(self):
        """Deve retornar None para URL inválida"""
        url = "https://invalid.com/video"
        assert extract_video_id(url) is None


class TestFilenameSanitization:
    """Testes para sanitização de nomes de arquivo"""

    def test_sanitize_normal_filename(self):
        """Deve manter filename normal"""
        filename = "My Video Title"
        result = sanitize_filename(filename)
        assert result == "My Video Title"

    def test_sanitize_special_characters(self):
        """Deve remover caracteres especiais"""
        filename = "Video: Title | Part 1/2 <test>"
        result = sanitize_filename(filename)
        assert "/" not in result
        assert ":" not in result
        assert "|" not in result
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_long_filename(self):
        """Deve truncar filenames muito longos"""
        filename = "A" * 300
        result = sanitize_filename(filename)
        assert len(result) <= 200

    def test_sanitize_empty_filename(self):
        """Deve retornar nome padrão para filename vazio"""
        result = sanitize_filename("")
        assert result == "audio"

    def test_sanitize_whitespace_only(self):
        """Deve tratar filename apenas com espaços"""
        result = sanitize_filename("   ")
        assert result == "audio"


class TestConverterService:
    """Testes para o serviço de conversão"""

    def test_service_initialization(self, converter_service):
        """Deve inicializar o serviço corretamente"""
        assert converter_service is not None
        assert os.path.exists(converter_service.downloads_dir)
        assert os.path.exists(converter_service.temp_dir)

    def test_add_task(self, converter_service, valid_youtube_url):
        """Deve adicionar tarefa de conversão"""
        task_id = converter_service.add_task(valid_youtube_url)
        assert task_id is not None
        assert task_id in converter_service.tasks

    def test_add_duplicate_task(self, converter_service, valid_youtube_url):
        """Não deve adicionar URL duplicada"""
        task_id1 = converter_service.add_task(valid_youtube_url)
        task_id2 = converter_service.add_task(valid_youtube_url)
        assert task_id1 == task_id2

    def test_add_invalid_url(self, converter_service, invalid_youtube_url):
        """Deve rejeitar URL inválida"""
        with pytest.raises(ValueError):
            converter_service.add_task(invalid_youtube_url)

    def test_remove_task(self, converter_service, valid_youtube_url):
        """Deve remover tarefa"""
        task_id = converter_service.add_task(valid_youtube_url)
        converter_service.remove_task(task_id)
        assert task_id not in converter_service.tasks

    def test_get_task_status(self, converter_service, valid_youtube_url):
        """Deve retornar status da tarefa"""
        task_id = converter_service.add_task(valid_youtube_url)
        status = converter_service.get_task_status(task_id)
        assert status == ConversionStatus.PENDING

    def test_get_all_tasks(self, converter_service, sample_urls):
        """Deve retornar todas as tarefas"""
        for url in sample_urls:
            converter_service.add_task(url)

        tasks = converter_service.get_all_tasks()
        assert len(tasks) == len(sample_urls)

    def test_clear_all_tasks(self, converter_service, sample_urls):
        """Deve limpar todas as tarefas"""
        for url in sample_urls:
            converter_service.add_task(url)

        converter_service.clear_all()
        assert len(converter_service.tasks) == 0


class TestConversionTask:
    """Testes para a classe ConversionTask"""

    def test_task_creation(self, valid_youtube_url):
        """Deve criar tarefa corretamente"""
        task = ConversionTask(url=valid_youtube_url)
        assert task.url == valid_youtube_url
        assert task.status == ConversionStatus.PENDING
        assert task.progress == 0
        assert task.filename is None

    def test_task_to_dict(self, valid_youtube_url):
        """Deve converter tarefa para dicionário"""
        task = ConversionTask(url=valid_youtube_url)
        data = task.to_dict()

        assert "id" in data
        assert "url" in data
        assert "status" in data
        assert "progress" in data
        assert data["url"] == valid_youtube_url


class TestConversionProcess:
    """Testes para o processo de conversão"""

    @pytest.mark.asyncio
    async def test_conversion_updates_progress(
        self, converter_service, valid_youtube_url
    ):
        """Deve atualizar progresso durante conversão"""
        task_id = converter_service.add_task(valid_youtube_url)

        # Mock do yt-dlp para teste
        with patch.object(converter_service, "_download_and_convert") as mock_convert:
            mock_convert.return_value = ("test_video.mp3", "Test Video")

            await converter_service.convert_task(task_id)

            task = converter_service.tasks[task_id]
            assert task.status == ConversionStatus.COMPLETED
            assert task.progress == 100

    @pytest.mark.asyncio
    async def test_conversion_creates_file(self, converter_service, valid_youtube_url):
        """Deve criar arquivo MP3 após conversão"""
        task_id = converter_service.add_task(valid_youtube_url)

        with patch.object(converter_service, "_download_and_convert") as mock_convert:
            # Cria arquivo de teste
            test_file = os.path.join(converter_service.downloads_dir, "test.mp3")
            with open(test_file, "w") as f:
                f.write("test")

            mock_convert.return_value = (test_file, "Test Video")

            await converter_service.convert_task(task_id)

            task = converter_service.tasks[task_id]
            assert task.filename is not None

    @pytest.mark.asyncio
    async def test_conversion_can_be_cancelled(
        self, converter_service, valid_youtube_url
    ):
        """Deve poder cancelar conversão em andamento"""
        task_id = converter_service.add_task(valid_youtube_url)

        # Inicia conversão
        converter_service.start_conversion()

        # Cancela
        converter_service.stop_conversion()

        assert converter_service.is_converting is False

    @pytest.mark.asyncio
    async def test_conversion_handles_error(self, converter_service, valid_youtube_url):
        """Deve tratar erros durante conversão"""
        task_id = converter_service.add_task(valid_youtube_url)

        with patch.object(converter_service, "_download_and_convert") as mock_convert:
            mock_convert.side_effect = Exception("Download failed")

            await converter_service.convert_task(task_id)

            task = converter_service.tasks[task_id]
            assert task.status == ConversionStatus.ERROR


class TestCleanup:
    """Testes para limpeza de arquivos"""

    def test_cleanup_temp_files(self, converter_service, test_temp_dir):
        """Deve limpar arquivos temporários"""
        # Cria arquivo temp
        temp_file = test_temp_dir / "temp_file.tmp"
        temp_file.write_text("temp content")

        converter_service.cleanup_temp()

        assert not temp_file.exists()

    def test_cleanup_preserves_completed_downloads(
        self, converter_service, test_downloads_dir
    ):
        """Deve preservar downloads completos durante cleanup temp"""
        # Cria arquivo de download
        download_file = test_downloads_dir / "completed.mp3"
        download_file.write_text("mp3 content")

        converter_service.cleanup_temp()

        assert download_file.exists()

    def test_cleanup_all_removes_everything(
        self, converter_service, test_downloads_dir, test_temp_dir
    ):
        """Deve remover tudo no cleanup completo"""
        # Cria arquivos
        (test_downloads_dir / "file.mp3").write_text("content")
        (test_temp_dir / "temp.tmp").write_text("content")

        converter_service.cleanup_all()

        assert len(list(test_downloads_dir.iterdir())) == 0
        assert len(list(test_temp_dir.iterdir())) == 0
