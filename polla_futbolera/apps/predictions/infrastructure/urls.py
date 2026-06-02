from django.urls import path
from . import views

app_name = "predictions"

urlpatterns = [
    path(
        "groups/<slug:slug>/tournaments/<int:tournament_id>/matches/<int:match_id>/predict/",
        views.predict_view,
        name="predict",
    ),
    path(
        "groups/<slug:slug>/tournaments/<int:tournament_id>/predictions/",
        views.group_predictions_view,
        name="group_predictions",
    ),
]
