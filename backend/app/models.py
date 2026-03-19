# backend/app/models.py
"""
Modelos de dados para a aplicação
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from enum import Enum
from datetime import datetime
import uuid


class ConversionStatus(str, Enum):
    """Status possíveis de uma conversão"""

    PENDING = "pending"
    CONVERTING = "converting"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class LinkCreate(BaseModel):
    """Schema para criação de link"""

    url: str = Field(..., min_length=1, description="URL do YouTube")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        from app.utils import validate_youtube_url

        if not validate_youtube_url(v):
            raise ValueError("URL do YouTube inválida")
        return v.strip()


class LinkUpdate(BaseModel):
    """Schema para atualização de link"""

    url: str = Field(..., min_length=1, description="Nova URL do YouTube")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        from app.utils import validate_youtube_url

        if not validate_youtube_url(v):
            raise ValueError("URL do YouTube inválida")
        return v.strip()


class LinkResponse(BaseModel):
    """Schema de resposta para link"""

    id: str
    url: str
    status: ConversionStatus
    progress: float = 0
    filename: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversionTask:
    """Classe para representar uma tarefa de conversão"""

    def __init__(self, url: str):
        self.id = str(uuid.uuid4())
        self.url = url
        self.status = ConversionStatus.PENDING
        self.progress: float = 0
        self.filename: Optional[str] = None
        self.title: Optional[str] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now()

    def to_dict(self) -> dict:
        """Converte para dicionário"""
        return {
            "id": self.id,
            "url": self.url,
            "status": (
                self.status.value
                if isinstance(self.status, ConversionStatus)
                else self.status
            ),
            "progress": self.progress,
            "filename": self.filename,
            "title": self.title,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


class ConversionStatusResponse(BaseModel):
    """Schema de resposta para status de conversão"""

    is_converting: bool
    current_task_id: Optional[str] = None
    tasks_pending: int
    tasks_completed: int
    tasks_total: int


class HealthResponse(BaseModel):
    """Schema de resposta para health check"""

    status: str
    version: str
    timestamp: datetime
