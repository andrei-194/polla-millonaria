import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


@dataclass
class Prediction:
    user_id: uuid.UUID
    match_id: uuid.UUID
    group_id: uuid.UUID
    home_goals: int
    away_goals: int
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    submitted_at: datetime = field(default_factory=datetime.utcnow)

    def is_exact(self, home_result: int, away_result: int) -> bool:
        return self.home_goals == home_result and self.away_goals == away_result

    def is_winner_correct(self, home_result: int, away_result: int) -> bool:
        def outcome(h, a):
            if h > a:
                return "home"
            if a > h:
                return "away"
            return "draw"

        return outcome(self.home_goals, self.away_goals) == outcome(home_result, away_result)


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
