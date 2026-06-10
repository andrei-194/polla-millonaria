from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from shared.infrastructure.views import home_view

urlpatterns = [
    path("", home_view, name="home"),
    path("admin/", admin.site.urls),
    path("health/", include("shared.infrastructure.urls")),
    path("accounts/", include("apps.accounts.infrastructure.urls")),
    path("quinielas/", include("apps.quinielas.infrastructure.urls")),
    path("torneos/", include("apps.tournaments.infrastructure.urls")),
    path("notificaciones/", include("apps.notifications.infrastructure.urls")),
    path("como-jugar/", include("apps.announcements.infrastructure.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
