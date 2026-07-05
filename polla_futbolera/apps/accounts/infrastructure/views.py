import base64
import io

import qrcode
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction

from apps.quinielas.infrastructure.permissions import moderador_required
from ..application.services import AccountService, InvitationCodeService
from ..application.dtos import RegisterUserDTO, CreateInvitationCodeDTO, RegisterViaCodeDTO
from ..domain.exceptions import (
    UserAlreadyExistsError,
    InvalidInvitationCodeError,
    InvitationCodeExhaustedError,
    InvitationCodeInactiveError,
)
from .forms import RegisterForm, ProfileForm, GenerarCodigoForm, RegistroViaCodigoForm, LoginForm
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
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("quinielas:list")
        messages.error(request, "Credenciales inválidas")
    else:
        form = LoginForm(request)
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


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


@moderador_required
def gestion_invitacion_view(request):
    svc = InvitationCodeService()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "desactivar":
            codigo = svc.get_active_code()
            if codigo:
                codigo.deactivate()
                messages.success(request, "Código de invitación desactivado.")
            return redirect("accounts:gestion_invitacion")
        if action == "generar":
            form = GenerarCodigoForm(request.POST)
            if form.is_valid():
                svc.create_code(CreateInvitationCodeDTO(
                    created_by_id=request.user.id,
                    expires_at=form.cleaned_data.get("expires_at"),
                    max_uses=form.cleaned_data.get("max_uses"),
                ))
                messages.success(request, "Nuevo código de invitación generado.")
                return redirect("accounts:gestion_invitacion")
    else:
        form = GenerarCodigoForm()

    codigo_activo = svc.get_active_code()
    invite_url = None
    qr_data_url = None
    if codigo_activo:
        invite_url = request.build_absolute_uri(
            f"/accounts/registrarse/{codigo_activo.code}/"
        )
        img = qrcode.make(invite_url)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    return render(request, "accounts/gestion_invitacion.html", {
        "form": form,
        "codigo_activo": codigo_activo,
        "invite_url": invite_url,
        "qr_data_url": qr_data_url,
    })


def registrarse_via_codigo_view(request, code):
    svc = InvitationCodeService()
    razon = None
    try:
        invitation = svc.get_valid_code(str(code))
    except InvitationCodeInactiveError:
        razon = "inactivo"
    except InvitationCodeExhaustedError:
        razon = "agotado"
    except InvalidInvitationCodeError:
        razon = "invalido"

    if razon:
        return render(request, "accounts/codigo_invalido.html", {"razon": razon})

    if request.method == "POST":
        form = RegistroViaCodigoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = svc.register_via_code(
                        invitation,
                        RegisterViaCodeDTO(
                            code=str(code),
                            username=form.cleaned_data["username"],
                            email=form.cleaned_data["email"],
                            password=form.cleaned_data["password1"],
                        ),
                    )
                    login(request, user)
                    messages.success(request, f"¡Bienvenido, {user.username}! Ya sos jugador.")
                    return redirect("quinielas:list")
            except UserAlreadyExistsError as e:
                messages.error(request, str(e))
    else:
        form = RegistroViaCodigoForm()

    return render(request, "accounts/registrarse_via_codigo.html", {
        "form": form,
        "codigo": invitation,
    })
