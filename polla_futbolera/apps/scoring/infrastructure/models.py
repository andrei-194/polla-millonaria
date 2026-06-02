from django.conf import settings
from django.db import models


class Score(models.Model):
    HIT_TYPE_CHOICES = [
        ("exact", "Exacto"),
        ("goal_diff", "Diferencia correcta"),
        ("winner", "Ganador correcto"),
        ("miss", "Incorrecto"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="scores"
    )
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, related_name="scores"
    )
    tournament = models.ForeignKey(
        "tournaments.Tournament", on_delete=models.CASCADE, related_name="scores"
    )
    match = models.ForeignKey(
        "tournaments.Match", on_delete=models.CASCADE, related_name="scores"
    )
    points = models.SmallIntegerField(default=0)
    hit_type = models.CharField(max_length=20, choices=HIT_TYPE_CHOICES, default="miss")
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scoring_score"
        unique_together = ("user", "match", "group")

    def __str__(self):
        return f"{self.user.username}: {self.points}pts ({self.hit_type})"
