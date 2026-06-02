from django.urls import path
from . import views

app_name = "tournaments"

urlpatterns = [
    path("", views.tournament_list, name="list"),
    path("groups/<slug:slug>/tournaments/add/", views.activate_tournament, name="activate"),
    path(
        "groups/<slug:slug>/tournaments/<int:tournament_id>/",
        views.tournament_detail,
        name="detail",
    ),
    path(
        "groups/<slug:slug>/tournaments/<int:tournament_id>/sync/",
        views.sync_tournament,
        name="sync",
    ),
]
