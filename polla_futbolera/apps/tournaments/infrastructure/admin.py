from django.contrib import admin
from .models import Tournament, Team, Match, Fecha


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "status", "external_code")
    list_filter = ("status",)
    search_fields = ("name", "external_code")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "external_code")
    search_fields = ("name", "external_code")


@admin.register(Fecha)
class FechaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "torneo", "numero", "fecha_inicio", "fecha_fin")
    list_filter = ("torneo",)
    search_fields = ("nombre",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tournament", "fecha", "phase", "status", "match_date")
    list_filter = ("status", "tournament", "fecha")
    search_fields = ("home_team__name", "away_team__name")
