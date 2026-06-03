from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class ReglaPuntuacion:
    tipo_evento_id: uuid.UUID
    codigo_acierto: str
    puntos: int
    quiniela_id: Optional[uuid.UUID] = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class PuntuacionEvento:
    usuario_id: uuid.UUID
    evento_partido_id: uuid.UUID
    quiniela_id: uuid.UUID
    valor_pronosticado: str
    valor_resultado: str
    codigo_acierto: str
    puntos: int
    calculado_en: datetime = field(default_factory=datetime.utcnow)
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class RankingEntrada:
    usuario_id: int
    username: str
    puntos: int
    posicion: int = 0
    fechas_jugadas: int = 0
    exactos_total: int = 0
    aciertos_total: int = 0
