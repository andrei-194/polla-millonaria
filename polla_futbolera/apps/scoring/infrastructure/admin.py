from django.contrib import admin
from .models import Score


@admin.register(Score)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ("user", "match", "quiniela", "points", "hit_type", "calculated_at")
