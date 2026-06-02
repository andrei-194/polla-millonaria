from django.contrib import admin
from .models import Tournament, Team, Match


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "status", "external_code")
    list_filter = ("status",)
    search_fields = ("name", "external_code")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "external_code")
    search_fields = ("name", "external_code")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tournament", "phase", "status", "match_date")
    list_filter = ("status", "tournament")
