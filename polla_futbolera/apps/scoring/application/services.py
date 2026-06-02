from django.db.models import Sum, Count, Q

from .dtos import LeaderboardEntryDTO
from ..domain.entities import calculate_hit_type, POINTS_MAP, HitType
from ..infrastructure.models import Score
from apps.predictions.infrastructure.models import Prediction
from apps.tournaments.infrastructure.models import Match


class ScoringService:
    def calculate_scores_for_match(self, match_id: int) -> int:
        match = Match.objects.get(id=match_id)
        if not match.has_result():
            return 0

        predictions = Prediction.objects.filter(match=match)
        count = 0
        for prediction in predictions:
            hit_type = calculate_hit_type(
                prediction.home_goals,
                prediction.away_goals,
                match.home_score,
                match.away_score,
            )
            points = POINTS_MAP[hit_type]
            Score.objects.update_or_create(
                user_id=prediction.user_id,
                match_id=match_id,
                group_id=prediction.group_id,
                tournament_id=match.tournament_id,
                defaults={"points": points, "hit_type": hit_type.value},
            )
            count += 1
        return count

    def get_leaderboard(self, group_id: int, tournament_id: int) -> list[LeaderboardEntryDTO]:
        scores = (
            Score.objects.filter(group_id=group_id, tournament_id=tournament_id)
            .values("user_id", "user__username")
            .annotate(
                total_points=Sum("points"),
                exact_count=Count("id", filter=Q(hit_type="exact")),
                winner_count=Count("id", filter=Q(hit_type="winner")),
                miss_count=Count("id", filter=Q(hit_type="miss")),
            )
            .order_by("-total_points")
        )
        return [
            LeaderboardEntryDTO(
                username=s["user__username"],
                user_id=s["user_id"],
                total_points=s["total_points"] or 0,
                exact_count=s["exact_count"],
                winner_count=s["winner_count"],
                miss_count=s["miss_count"],
            )
            for s in scores
        ]
