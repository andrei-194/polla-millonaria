from django.http import JsonResponse
from django.shortcuts import render, redirect


def health_check(request):
    return JsonResponse({"status": "ok"})


def home_view(request):
    if request.user.is_authenticated:
        return redirect("quinielas:list")
    return render(request, "landing/home.html")
