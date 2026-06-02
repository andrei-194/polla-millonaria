from .dtos import MatchSummaryDTO
from ..domain.ports import FootballAPIPort
from ..infrastructure.models import Tournament, Match, Team


class TournamentService:
    def __init__(self, football_api: FootballAPIPort | None = None):
        self.football_api = football_api

    def sync_fixtures(self, tournament: Tournament) -> int:
        if not self.football_api:
            return 0
        fixtures = self.football_api.fetch_fixtures(tournament.external_code, tournament.season)
        count = 0
        for fixture in fixtures:
            home_team, _ = Team.objects.get_or_create(
                external_code=fixture.home_team_code,
                defaults={"name": fixture.home_team_name},
            )
            away_team, _ = Team.objects.get_or_create(
                external_code=fixture.away_team_code,
                defaults={"name": fixture.away_team_name},
            )
            _, created = Match.objects.update_or_create(
                external_id=fixture.external_id,
                defaults={
                    "tournament": tournament,
                    "home_team": home_team,
                    "away_team": away_team,
                    "match_date": fixture.match_date,
                    "phase": fixture.phase,
                    "status": fixture.status,
                },
            )
            if created:
                count += 1
        return count

    def get_matches(self, tournament_id: int) -> list[MatchSummaryDTO]:
        matches = (
            Match.objects.filter(tournament_id=tournament_id)
            .select_related("home_team", "away_team")
            .order_by("match_date")
        )
        return [
            MatchSummaryDTO(
                id=m.id,
                home_team=m.home_team.name,
                away_team=m.away_team.name,
                match_date=m.match_date,
                phase=m.phase,
                home_score=m.home_score,
                away_score=m.away_score,
                status=m.status,
                external_id=m.external_id,
            )
            for m in matches
        ]
