from django.conf import settings as django_settings


def user_roles(request):
    user = request.user
    if not user.is_authenticated:
        return {
            "is_superadmin": False,
            "is_moderador": False,
            "is_jugador": False,
            "ads_enabled": getattr(django_settings, "ADS_ENABLED", False),
        }

    is_superadmin = bool(user.is_staff or user.is_superuser)
    group_names = set(user.groups.values_list("name", flat=True))
    is_moderador = not is_superadmin and "Moderador" in group_names
    is_jugador = not is_superadmin and not is_moderador and "Jugador" in group_names

    return {
        "is_superadmin": is_superadmin,
        "is_moderador": is_moderador,
        "is_jugador": is_jugador,
        # Superadmins no ven publicidad
        "ads_enabled": getattr(django_settings, "ADS_ENABLED", False) and not is_superadmin,
    }
