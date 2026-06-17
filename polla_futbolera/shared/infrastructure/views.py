from django.http import JsonResponse
from django.shortcuts import render, redirect

from apps.quinielas.infrastructure.models import Inscripcion


def health_check(request):
    return JsonResponse({"status": "ok"})


def home_view(request):
    if request.user.is_authenticated:
        return redirect("quinielas:list")
    total_jugadores = (
        Inscripcion.objects.filter(activa=True)
        .values("jugador")
        .distinct()
        .count()
    )
    return render(request, "landing/home.html", {"total_jugadores": total_jugadores})
