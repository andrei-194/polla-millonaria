from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", RedirectView.as_view(url="/quinielas/", permanent=False)),
    path("admin/", admin.site.urls),
    path("health/", include("shared.infrastructure.urls")),
    path("accounts/", include("apps.accounts.infrastructure.urls")),
    path("quinielas/", include("apps.quinielas.infrastructure.urls")),
    path("torneos/", include("apps.tournaments.infrastructure.urls")),
    path("pronosticos/", include("apps.predictions.infrastructure.urls")),
    path("scoring/", include("apps.scoring.infrastructure.urls")),
    path("notificaciones/", include("apps.notifications.infrastructure.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
