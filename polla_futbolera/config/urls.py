from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/groups/", permanent=False)),
    path("admin/", admin.site.urls),
    path("health/", include("shared.infrastructure.urls")),
    path("accounts/", include("apps.accounts.infrastructure.urls")),
    path("groups/", include("apps.groups.infrastructure.urls")),
    path("tournaments/", include("apps.tournaments.infrastructure.urls")),
    path("predictions/", include("apps.predictions.infrastructure.urls")),
    path("scoring/", include("apps.scoring.infrastructure.urls")),
    path("notifications/", include("apps.notifications.infrastructure.urls")),
]
