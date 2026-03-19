# backend/app/converter.py
"""
Serviço de conversão YouTube para MP3
"""
import os
import asyncio
import logging
from typing import Dict, Optional, List, Callable
from pathlib import Path
import shutil
import re
import yt_dlp

from app.models import ConversionTask, ConversionStatus
from app.utils import validate_youtube_url, sanitize_filename, extract_video_id

logger = logging.getLogger(__name__)


class ConverterService:
    """Serviço para conversão de vídeos do YouTube para MP3"""

    def __init__(self, downloads_dir: str = "downloads", temp_dir: str = "temp"):
        self.downloads_dir = downloads_dir
        self.temp_dir = temp_dir
        self.tasks: Dict[str, ConversionTask] = {}
        self.is_converting = False
        self.current_task_id: Optional[str] = None
        self._stop_requested = False
        self._conversion_task: Optional[asyncio.Task] = None
        self._progress_callback: Optional[Callable] = None

        # Cria diretórios se não existirem
        os.makedirs(self.downloads_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def set_progress_callback(self, callback: Callable):
        """Define callback para atualizações de progresso"""
        self._progress_callback = callback

    def add_task(self, url: str) -> str:
        """
        Adiciona nova tarefa de conversão.

        Args:
            url: URL do YouTube

        Returns:
            ID da tarefa criada

        Raises:
            ValueError: Se URL for inválida
        """
        if not validate_youtube_url(url):
            raise ValueError("URL do YouTube inválida")

        # Verifica se URL já existe
        video_id = extract_video_id(url)
        for task_id, task in self.tasks.items():
            if extract_video_id(task.url) == video_id:
                return task_id

        task = ConversionTask(url=url)
        self.tasks[task.id] = task
        logger.info(f"Tarefa adicionada: {task.id}")
        return task.id

    def update_task_url(self, task_id: str, new_url: str) -> bool:
        """
        Atualiza URL de uma tarefa.

        Args:
            task_id: ID da tarefa
            new_url: Nova URL

        Returns:
            True se atualizado com sucesso
        """
        if task_id not in self.tasks:
            return False

        if not validate_youtube_url(new_url):
            raise ValueError("URL do YouTube inválida")

        task = self.tasks[task_id]

        # Não permite atualizar se está convertendo ou completo
        if task.status in [ConversionStatus.CONVERTING, ConversionStatus.COMPLETED]:
            return False

        task.url = new_url
        task.status = ConversionStatus.PENDING
        task.progress = 0
        task.error = None
        return True

    def remove_task(self, task_id: str) -> bool:
        """
        Remove uma tarefa e seus arquivos associados.

        Args:
            task_id: ID da tarefa

        Returns:
            True se removido com sucesso
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]

        # Remove arquivo se existir
        if task.filename:
            file_path = os.path.join(self.downloads_dir, task.filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Arquivo removido: {file_path}")
                except Exception as e:
                    logger.error(f"Erro ao remover arquivo: {e}")

        del self.tasks[task_id]
        logger.info(f"Tarefa removida: {task_id}")
        return True

    def get_task(self, task_id: str) -> Optional[ConversionTask]:
        """Retorna uma tarefa pelo ID"""
        return self.tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[ConversionStatus]:
        """Retorna status de uma tarefa"""
        task = self.tasks.get(task_id)
        return task.status if task else None

    def get_all_tasks(self) -> List[dict]:
        """Retorna todas as tarefas como lista de dicionários"""
        return [task.to_dict() for task in self.tasks.values()]

    def clear_all(self):
        """Remove todas as tarefas e arquivos"""
        # Para conversão se estiver em andamento
        self.stop_conversion()

        # Remove arquivos
        for task in self.tasks.values():
            if task.filename:
                file_path = os.path.join(self.downloads_dir, task.filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Erro ao remover arquivo: {e}")

        self.tasks.clear()
        self.cleanup_all()
        logger.info("Todas as tarefas foram removidas")

    def start_conversion(self) -> bool:
        """
        Inicia o processo de conversão.

        Returns:
            True se iniciado com sucesso
        """
        if self.is_converting:
            return False

        pending_tasks = [
            t for t in self.tasks.values() if t.status == ConversionStatus.PENDING
        ]

        if not pending_tasks:
            return False

        self.is_converting = True
        self._stop_requested = False
        self._conversion_task = asyncio.create_task(self._convert_all())
        logger.info("Conversão iniciada")
        return True

    def stop_conversion(self):
        """Para o processo de conversão"""
        self._stop_requested = True
        self.is_converting = False

        # Reseta tarefas que estavam convertendo
        if self.current_task_id and self.current_task_id in self.tasks:
            task = self.tasks[self.current_task_id]
            if task.status == ConversionStatus.CONVERTING:
                task.status = ConversionStatus.PENDING
                task.progress = 0

        self.current_task_id = None
        self.cleanup_temp()
        logger.info("Conversão parada")

    async def _convert_all(self):
        """Converte todas as tarefas pendentes"""
        try:
            for task_id, task in list(self.tasks.items()):
                if self._stop_requested:
                    break

                if task.status == ConversionStatus.PENDING:
                    await self.convert_task(task_id)
        finally:
            self.is_converting = False
            self.current_task_id = None

    async def convert_task(self, task_id: str):
        """
        Converte uma tarefa específica.

        Args:
            task_id: ID da tarefa
        """
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.status = ConversionStatus.CONVERTING
        task.progress = 0
        self.current_task_id = task_id

        try:
            filename, title = await self._download_and_convert(task)

            if self._stop_requested:
                # Limpa arquivo parcial
                if filename and os.path.exists(filename):
                    os.remove(filename)
                task.status = ConversionStatus.PENDING
                task.progress = 0
                return

            task.filename = os.path.basename(filename)
            task.title = title
            task.status = ConversionStatus.COMPLETED
            task.progress = 100
            logger.info(f"Conversão completa: {task_id}")

        except Exception as e:
            logger.error(f"Erro na conversão {task_id}: {e}")
            task.status = ConversionStatus.ERROR
            task.error = str(e)

        finally:
            self.cleanup_temp()
            if self._progress_callback:
                await self._progress_callback(task_id, task.to_dict())

    async def _download_and_convert(self, task: ConversionTask) -> tuple:
        """
        Faz download e converte o vídeo para MP3.

        Args:
            task: Tarefa de conversão

        Returns:
            Tupla (caminho_arquivo, titulo)
        """

        def progress_hook(d):
            if self._stop_requested:
                raise Exception("Conversão cancelada")

            if d["status"] == "downloading":
                try:
                    percent_str = d.get("_percent_str", "0%")
                    # Limpa os códigos de cor ANSI embutidos pelo yt-dlp
                    percent_clean = re.sub(r"\x1b\[[0-9;]*m", "", percent_str)
                    percent = percent_clean.replace("%", "").strip()
                    task.progress = min(float(percent) * 0.9, 90)  # 90% para download
                except Exception:
                    pass
            elif d["status"] == "finished":
                task.progress = 95  # 95% após download, antes da conversão

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(self.downloads_dir, "%(title)s.%(ext)s"),
            "ffmpeg_location": r"C:\ffmpeg\ffmpeg-master-latest-win64-gpl\bin",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "proxy": "",
            "source_address": "0.0.0.0",
            "socket_timeout": 30,
            "retries": 10,
        }

        loop = asyncio.get_event_loop()

        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                original_filepath = ydl.prepare_filename(info)
                final_filepath = f"{os.path.splitext(original_filepath)[0]}.mp3"
                return final_filepath, info.get("title", "Audio")

        return await loop.run_in_executor(None, download)

    def get_file_path(self, task_id: str) -> Optional[str]:
        """Retorna caminho do arquivo convertido"""
        task = self.tasks.get(task_id)
        if not task or not task.filename:
            return None

        file_path = os.path.join(self.downloads_dir, task.filename)
        if os.path.exists(file_path):
            return file_path
        return None

    def cleanup_temp(self):
        """Limpa arquivos temporários"""
        if os.path.exists(self.temp_dir):
            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    logger.error(f"Erro ao limpar temp: {e}")

    def cleanup_all(self):
        """Limpa todos os arquivos (temp e downloads)"""
        self.cleanup_temp()

        # Limpa downloads
        if os.path.exists(self.downloads_dir):
            for item in os.listdir(self.downloads_dir):
                item_path = os.path.join(self.downloads_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                except Exception as e:
                    logger.error(f"Erro ao limpar downloads: {e}")

    def get_status(self) -> dict:
        """Retorna status geral do serviço"""
        pending = sum(
            1 for t in self.tasks.values() if t.status == ConversionStatus.PENDING
        )
        completed = sum(
            1 for t in self.tasks.values() if t.status == ConversionStatus.COMPLETED
        )

        return {
            "is_converting": self.is_converting,
            "current_task_id": self.current_task_id,
            "tasks_pending": pending,
            "tasks_completed": completed,
            "tasks_total": len(self.tasks),
        }
