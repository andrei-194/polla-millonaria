from django.urls import path
from . import views

app_name = "scoring"

urlpatterns = [
    path(
        "groups/<slug:slug>/tournaments/<int:tournament_id>/leaderboard/",
        views.leaderboard_view,
        name="leaderboard",
    ),
]
