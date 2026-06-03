from dataclasses import dataclass


@dataclass
class CreatePredictionDTO:
    user_id: int
    match_id: int
    quiniela_id: int
    home_goals: int
    away_goals: int


@dataclass
class CrearPronosticoEventoDTO:
    usuario_id: int
    evento_partido_id: int
    valor: str
