from django.conf import settings
from django.db import models


class Tournament(models.Model):
    STATUS_CHOICES = [("active", "Activo"), ("finished", "Finalizado")]

    name = models.CharField(max_length=150)
    external_code = models.CharField(max_length=50, unique=True)
    season = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tournaments_tournament"

    def __str__(self):
        return f"{self.name} ({self.season})"


class Team(models.Model):
    name = models.CharField(max_length=100)
    external_code = models.CharField(max_length=50, unique=True)
    logo_url = models.URLField(blank=True, default="")

    class Meta:
        db_table = "tournaments_team"

    def __str__(self):
        return self.name


class GroupTournament(models.Model):
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, related_name="group_tournaments"
    )
    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, related_name="group_tournaments"
    )
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    activated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tournaments_grouptournament"
        unique_together = ("group", "tournament")

    def __str__(self):
        return f"{self.group.name} — {self.tournament.name}"


class Match(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Programado"),
        ("in_progress", "En curso"),
        ("finished", "Finalizado"),
        ("postponed", "Postergado"),
    ]

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="matches")
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_matches")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_matches")
    external_id = models.CharField(max_length=100, unique=True)
    phase = models.CharField(max_length=50, default="group")
    match_date = models.DateTimeField()
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tournaments_match"
        ordering = ["match_date"]

    def has_result(self) -> bool:
        return self.home_score is not None and self.away_score is not None

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} ({self.match_date:%Y-%m-%d})"
