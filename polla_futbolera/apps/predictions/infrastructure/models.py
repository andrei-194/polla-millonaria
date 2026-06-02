from django.conf import settings
from django.db import models


class Prediction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="predictions"
    )
    match = models.ForeignKey(
        "tournaments.Match", on_delete=models.CASCADE, related_name="predictions"
    )
    quiniela = models.ForeignKey(
        "quinielas.Quiniela", on_delete=models.CASCADE, related_name="predictions"
    )
    home_goals = models.PositiveSmallIntegerField()
    away_goals = models.PositiveSmallIntegerField()
    submitted_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "predictions_prediction"
        unique_together = ("user", "match", "quiniela")

    def __str__(self):
        return f"{self.user.username}: {self.home_goals}-{self.away_goals} ({self.match})"
