# backend/app/main.py
"""
API principal do aplicativo
"""
import os
import logging
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.models import (
    LinkCreate,
    LinkUpdate,
    LinkResponse,
    ConversionStatusResponse,
    HealthResponse,
    ConversionStatus,
)
from app.converter import ConverterService
from app import __version__

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Instância global do serviço
converter_service: ConverterService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    global converter_service

    # Startup
    downloads_dir = os.getenv("DOWNLOADS_DIR", "downloads")
    temp_dir = os.getenv("TEMP_DIR", "temp")

    converter_service = ConverterService(downloads_dir=downloads_dir, temp_dir=temp_dir)

    logger.info("Aplicação iniciada")

    yield

    # Shutdown
    if converter_service:
        converter_service.stop_conversion()
        converter_service.cleanup_temp()

    logger.info("Aplicação encerrada")


# Cria aplicação
app = FastAPI(
    title="YouTube to MP3 Converter",
    description="API para conversão de vídeos do YouTube para MP3",
    version=__version__,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_converter_service() -> ConverterService:
    """Dependency para obter o serviço de conversão"""
    global converter_service
    if converter_service is None:
        converter_service = ConverterService()
    return converter_service


# ==================== ENDPOINTS ====================


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Verifica saúde da API"""
    return {"status": "healthy", "version": __version__, "timestamp": datetime.now()}


@app.post("/api/links", status_code=status.HTTP_201_CREATED)
async def add_link(
    link: LinkCreate, service: ConverterService = Depends(get_converter_service)
):
    """Adiciona novo link para conversão"""
    try:
        task_id = service.add_task(link.url)
        task = service.get_task(task_id)
        return task.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/links")
async def get_all_links(service: ConverterService = Depends(get_converter_service)):
    """Retorna todos os links"""
    return service.get_all_tasks()


@app.get("/api/links/{link_id}")
async def get_link(
    link_id: str, service: ConverterService = Depends(get_converter_service)
):
    """Retorna link específico"""
    task = service.get_task(link_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado"
        )
    return task.to_dict()


@app.put("/api/links/{link_id}")
async def update_link(
    link_id: str,
    link: LinkUpdate,
    service: ConverterService = Depends(get_converter_service),
):
    """Atualiza URL de um link"""
    try:
        success = service.update_task_url(link_id, link.url)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Link não encontrado ou não pode ser atualizado",
            )
        task = service.get_task(link_id)
        return task.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.delete("/api/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: str, service: ConverterService = Depends(get_converter_service)
):
    """Remove um link"""
    success = service.remove_task(link_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link não encontrado"
        )
    return None


@app.delete("/api/links", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_links(service: ConverterService = Depends(get_converter_service)):
    """Remove todos os links"""
    service.clear_all()
    return None


@app.post("/api/convert/start")
async def start_conversion(
    background_tasks: BackgroundTasks,
    service: ConverterService = Depends(get_converter_service),
):
    """Inicia processo de conversão"""
    if not service.tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum link para converter"
        )

    pending = [
        t for t in service.tasks.values() if t.status == ConversionStatus.PENDING
    ]
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum link pendente para converter",
        )

    success = service.start_conversion()

    return {
        "status": "converting" if success else "already_converting",
        "message": "Conversão iniciada" if success else "Conversão já em andamento",
    }


@app.post("/api/convert/stop")
async def stop_conversion(service: ConverterService = Depends(get_converter_service)):
    """Para processo de conversão"""
    service.stop_conversion()
    return {"status": "stopped", "message": "Conversão parada"}


@app.get("/api/convert/status", response_model=ConversionStatusResponse)
async def get_conversion_status(
    service: ConverterService = Depends(get_converter_service),
):
    """Retorna status da conversão"""
    return service.get_status()


@app.get("/api/download/{task_id}")
async def download_file(
    task_id: str, service: ConverterService = Depends(get_converter_service)
):
    """Faz download do arquivo MP3 convertido"""
    task = service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada"
        )

    if task.status != ConversionStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo ainda não está pronto",
        )

    file_path = service.get_file_path(task_id)

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado"
        )

    return FileResponse(path=file_path, filename=task.filename, media_type="audio/mpeg")


# Monta arquivos estáticos do frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
