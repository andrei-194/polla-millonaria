import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class EventoEstado(str, Enum):
    ABIERTO   = "abierto"
    CERRADO   = "cerrado"
    PUNTUADO  = "puntuado"
    CANCELADO = "cancelado"


@dataclass
class TipoEvento:
    codigo: str
    nombre: str
    descripcion: str
    config: dict
    activo: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class EventoPartido:
    partido_id: uuid.UUID
    quiniela_id: uuid.UUID
    tipo_evento_id: uuid.UUID
    plazo_cierre: datetime
    estado: EventoEstado = EventoEstado.ABIERTO
    resultado: Optional[str] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    creado_en: datetime = field(default_factory=datetime.utcnow)

    def esta_abierto(self) -> bool:
        from datetime import timezone
        return (
            self.estado == EventoEstado.ABIERTO
            and datetime.now(timezone.utc) < self.plazo_cierre
        )


@dataclass
class PronosticoEvento:
    usuario_id: uuid.UUID
    evento_partido_id: uuid.UUID
    valor: str
    enviado_en: datetime = field(default_factory=datetime.utcnow)
    id: uuid.UUID = field(default_factory=uuid.uuid4)


_SCORE_RE = re.compile(r"^\d{1,2}-\d{1,2}$")


def validar_valor(tipo_evento: TipoEvento, valor: str) -> bool:
    if "choices" in tipo_evento.config:
        return valor in tipo_evento.config["choices"]
    if tipo_evento.codigo == "SCORE":
        return bool(_SCORE_RE.match(valor))
    return False
