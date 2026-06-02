from django.urls import path
from . import views

app_name = "scoring"

urlpatterns = [
    path("quinielas/<slug:slug>/leaderboard/", views.leaderboard_view, name="leaderboard"),
]
