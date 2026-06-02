from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from ..application.services import AccountService
from ..application.dtos import RegisterUserDTO
from ..domain.exceptions import UserAlreadyExistsError
from .forms import RegisterForm, ProfileForm
from .models import UserProfile


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            service = AccountService()
            try:
                with transaction.atomic():
                    service.register_user(RegisterUserDTO(
                        username=form.cleaned_data["username"],
                        email=form.cleaned_data["email"],
                        password=form.cleaned_data["password1"],
                    ))
                    user = authenticate(
                        request,
                        username=form.cleaned_data["username"],
                        password=form.cleaned_data["password1"],
                    )
                    UserProfile.objects.get_or_create(user=user)
                    login(request, user)
                    return redirect("quinielas:list")
            except UserAlreadyExistsError as e:
                messages.error(request, str(e))
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("quinielas:list")
        messages.error(request, "Credenciales inválidas")
    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


@login_required
def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil actualizado")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "accounts/profile.html", {"form": form, "user": request.user})
