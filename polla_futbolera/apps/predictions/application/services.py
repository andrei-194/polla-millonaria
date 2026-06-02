from datetime import timedelta

from django.utils import timezone
from django.conf import settings

from .dtos import CreatePredictionDTO
from ..domain.exceptions import PredictionDeadlinePassedError
from ..infrastructure.models import Prediction
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
