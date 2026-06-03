from datetime import timedelta

from django.utils import timezone
from django.conf import settings

from .dtos import CreatePredictionDTO, CrearPronosticoEventoDTO
from ..domain.entities import validar_valor, TipoEvento as TipoEventoEntity
from ..domain.exceptions import PredictionDeadlinePassedError, ValorInvalidoError, EventoCerradoError
from ..infrastructure.models import Prediction, EventoPartido, PronosticoEvento, TipoEvento
from apps.tournaments.infrastructure.models import Match


class PredictionService:
    def create_or_update_prediction(self, dto: CreatePredictionDTO) -> Prediction:
        match = Match.objects.get(id=dto.match_id)
        deadline_minutes = settings.PREDICTION_DEADLINE_MINUTES

        if timezone.now() >= match.match_date - timedelta(minutes=deadline_minutes):
            raise PredictionDeadlinePassedError("El plazo para pronosticar ha cerrado")

        prediction, _ = Prediction.objects.update_or_create(
            user_id=dto.user_id,
            match_id=dto.match_id,
            quiniela_id=dto.quiniela_id,
            defaults={
                "home_goals": dto.home_goals,
                "away_goals": dto.away_goals,
            },
        )
        return prediction

    def crear_pronostico_evento(self, dto: CrearPronosticoEventoDTO) -> PronosticoEvento:
        evento = EventoPartido.objects.select_related("tipo_evento").get(id=dto.evento_partido_id)

        if not evento.esta_abierto():
            raise EventoCerradoError("El plazo para pronosticar este evento ha cerrado")

        tipo = evento.tipo_evento
        tipo_entity = TipoEventoEntity(
            codigo=tipo.codigo,
            nombre=tipo.nombre,
            descripcion=tipo.descripcion,
            config=tipo.config,
        )
        if not validar_valor(tipo_entity, dto.valor):
            raise ValorInvalidoError(
                f"Valor '{dto.valor}' no es válido para el tipo {tipo.codigo}"
            )

        pronostico, _ = PronosticoEvento.objects.update_or_create(
            usuario_id=dto.usuario_id,
            evento_partido=evento,
            defaults={"valor": dto.valor},
        )
        return pronostico

    def get_quiniela_predictions(self, match_id: int, quiniela_id: int, requesting_user_id: int):
        match = Match.objects.get(id=match_id)
        deadline_minutes = settings.PREDICTION_DEADLINE_MINUTES

        if timezone.now() < match.match_date - timedelta(minutes=deadline_minutes):
            return Prediction.objects.filter(
                match_id=match_id, quiniela_id=quiniela_id, user_id=requesting_user_id
            ).select_related("user")

        return Prediction.objects.filter(
            match_id=match_id, quiniela_id=quiniela_id
        ).select_related("user")
