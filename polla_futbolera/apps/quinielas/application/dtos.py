from dataclasses import dataclass


@dataclass
class InscribirJugadorDTO:
    jugador_id: int
    quiniela_id: int
    moderador_id: int


@dataclass
class DarDeBajaDTO:
    inscripcion_id: int
    moderador_id: int
