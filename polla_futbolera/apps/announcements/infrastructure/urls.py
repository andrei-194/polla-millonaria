from django.urls import path
from .views import como_jugar

app_name = "announcements"

urlpatterns = [
    path("", como_jugar, name="como_jugar"),
]
