from django.contrib import admin
from .models import Tournament, Team, Match, GroupTournament


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "season", "status", "external_code")


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "external_code")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tournament", "phase", "status", "match_date")


@admin.register(GroupTournament)
class GroupTournamentAdmin(admin.ModelAdmin):
    list_display = ("group", "tournament", "activated_at")
