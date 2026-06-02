from django.conf import settings
from shared.infrastructure.http_client import BaseHTTPClient
from ..domain.ports import FootballAPIPort, MatchDTO, ResultDTO
from datetime import datetime


class FootballDataOrgAdapter(BaseHTTPClient, FootballAPIPort):
    """Adapter for football-data.org API v4"""

    def __init__(self):
        super().__init__(
            base_url=settings.FOOTBALL_API_BASE_URL,
            api_key=settings.FOOTBALL_API_KEY,
        )

    def _get_headers(self) -> dict:
        return {"X-Auth-Token": self.api_key}

    def fetch_fixtures(self, tournament_code: str, season: str) -> list[MatchDTO]:
        data = self.get(f"/competitions/{tournament_code}/matches", {"season": season})
        matches = []
        for m in data.get("matches", []):
            matches.append(MatchDTO(
                external_id=str(m["id"]),
                home_team_name=m["homeTeam"]["name"],
                away_team_name=m["awayTeam"]["name"],
                home_team_code=str(m["homeTeam"]["id"]),
                away_team_code=str(m["awayTeam"]["id"]),
                match_date=datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")),
                phase=m.get("stage", "GROUP_STAGE"),
                home_score=m["score"]["fullTime"].get("home"),
                away_score=m["score"]["fullTime"].get("away"),
                status=m["status"].lower(),
            ))
        return matches

    def fetch_results(self, match_external_id: str) -> ResultDTO:
        data = self.get(f"/matches/{match_external_id}")
        m = data["match"]
        return ResultDTO(
            external_id=match_external_id,
            home_score=m["score"]["fullTime"]["home"],
            away_score=m["score"]["fullTime"]["away"],
            status=m["status"].lower(),
        )


class StubFootballAPIAdapter(FootballAPIPort):
    """Stub adapter for development/testing when no API key is available"""

    def fetch_fixtures(self, tournament_code: str, season: str) -> list[MatchDTO]:
        return []

    def fetch_results(self, match_external_id: str) -> ResultDTO:
        return ResultDTO(
            external_id=match_external_id,
            home_score=0,
            away_score=0,
            status="finished",
        )
