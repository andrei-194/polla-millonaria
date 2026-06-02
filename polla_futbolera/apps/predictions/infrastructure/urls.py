from django.urls import path
from . import views

app_name = "predictions"

urlpatterns = [
    path(
        "quinielas/<slug:slug>/partidos/<int:match_id>/predecir/",
        views.predict_view,
        name="predict",
    ),
    path(
        "quinielas/<slug:slug>/partidos/<int:match_id>/pronosticos/",
        views.quiniela_predictions_view,
        name="quiniela_predictions",
    ),
]
