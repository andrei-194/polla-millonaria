from .dtos import InscribirJugadorDTO, DarDeBajaDTO
from ..domain.exceptions import JugadorYaInscritoError, JugadorNoInscritoError
from ..infrastructure.models import Quiniela, Inscripcion


class QuinielaService:
    def listar_activas(self):
        return Quiniela.objects.filter(status="activa").select_related("tournament")

    def inscribir_jugador(self, dto: InscribirJugadorDTO) -> Inscripcion:
        inscripcion, created = Inscripcion.objects.get_or_create(
            jugador_id=dto.jugador_id,
            quiniela_id=dto.quiniela_id,
            defaults={"activa": True},
        )
        if not created:
            if inscripcion.activa:
                raise JugadorYaInscritoError("El jugador ya está inscrito en esta quiniela")
            inscripcion.activa = True
            inscripcion.save(update_fields=["activa"])
        return inscripcion

    def dar_de_baja(self, inscripcion_id: int) -> None:
        try:
            inscripcion = Inscripcion.objects.get(id=inscripcion_id)
        except Inscripcion.DoesNotExist:
            raise JugadorNoInscritoError("Inscripción no encontrada")
        inscripcion.activa = False
        inscripcion.save(update_fields=["activa"])

    def jugador_inscrito(self, jugador_id: int, quiniela_id: int) -> bool:
        return Inscripcion.objects.filter(
            jugador_id=jugador_id, quiniela_id=quiniela_id, activa=True
        ).exists()

    def listar_inscripciones(self, quiniela_id: int):
        return Inscripcion.objects.filter(
            quiniela_id=quiniela_id
        ).select_related("jugador")
