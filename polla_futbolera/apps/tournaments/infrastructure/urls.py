from django.urls import path
from . import views

app_name = "tournaments"

urlpatterns = [
    path("", views.tournament_list, name="list"),
    path("<int:tournament_id>/partidos/", views.tournament_matches, name="matches"),
    path("<int:tournament_id>/sync/", views.sync_tournament, name="sync"),
]
