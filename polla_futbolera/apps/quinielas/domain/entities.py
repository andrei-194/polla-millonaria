from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QuinielaStatus(str, Enum):
    ACTIVE = "activa"
    FINISHED = "finalizada"


@dataclass
class Quiniela:
    name: str
    slug: str
    tournament_id: int
    id: int = 0
    description: str = ""
    status: QuinielaStatus = QuinielaStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Inscripcion:
    jugador_id: int
    quiniela_id: int
    id: int = 0
    activa: bool = True
    inscrito_en: datetime = field(default_factory=datetime.utcnow)
