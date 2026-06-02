from django.contrib import admin
from .models import Prediction


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "match", "quiniela", "home_goals", "away_goals", "submitted_at")
