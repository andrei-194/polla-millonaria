from dataclasses import dataclass


@dataclass
class CrearPronosticoEventoDTO:
    usuario_id: int
    evento_partido_id: int
    valor: str
