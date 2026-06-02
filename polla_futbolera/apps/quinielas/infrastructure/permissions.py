from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def jugador_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        is_privileged = request.user.is_staff or request.user.is_superuser
        if not is_privileged and not request.user.groups.filter(name="Jugador").exists():
            messages.error(request, "Necesitas ser jugador para acceder a esta sección")
            return redirect("quinielas:list")
        return view_func(request, *args, **kwargs)
    return wrapper


def moderador_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        es_moderador = request.user.groups.filter(name="Moderador").exists()
        if not (request.user.is_staff or es_moderador):
            messages.error(request, "No tienes permisos para acceder a esta sección")
            return redirect("quinielas:list")
        return view_func(request, *args, **kwargs)
    return wrapper
