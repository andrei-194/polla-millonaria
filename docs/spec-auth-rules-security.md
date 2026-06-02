# Spec — Auth, Reglas de Negocio y Seguridad

**Versión:** 1.1  
**Fecha:** 2026-06-02  
**Scope:** Flujo de autenticación, administración de usuarios, reglas de negocio de torneos y pronósticos, hardening de seguridad.

---

## 1. Contexto y Cambios Respecto al Spec v1.0

El spec v1.0 dejó sin definir dos reglas de negocio críticas. Este documento las formaliza:

| Regla | Estado anterior | Estado nuevo |
|---|---|---|
| ¿Quién crea torneos? | No explicitado | **Solo el admin del sitio (staff Django)** |
| Plazo de pronósticos | `PREDICTION_DEADLINE_MINUTES` configurable | **Fijo: 120 minutos (2 horas) antes del partido** |

Además se define el endurecimiento de seguridad en frontend y backend que debe aplicarse a todo el sistema.

---

## 2. Flujo de Autenticación

### 2.1 Registro de usuario

**Pantalla:** `/accounts/register/`

**Campos del formulario:**
- `username` — requerido, 3–30 chars, solo letras/números/guion bajo
- `email` — requerido, formato válido, único en el sistema
- `password1` — mínimo 8 chars, no puede ser solo numérico, no puede ser igual al username
- `password2` — confirmación (debe coincidir con `password1`)

**Flujo exitoso:**
1. Usuario completa el form y envía
2. Backend valida (ver sección 5.1)
3. Se crea `User` + `UserProfile` en una transacción atómica
4. Se autologa al usuario (`login()`)
5. Redirige a `/groups/`

**Flujo fallido:**
- El form se re-renderiza con errores inline sobre cada campo
- No se revela si un email o username ya existe (mensaje genérico: "No se pudo completar el registro")
- Se aplica rate limiting (ver sección 5.2)

**Template:** `accounts/register.html`  
**Vista:** `accounts/infrastructure/views.py::register_view`

---

### 2.2 Login

**Pantalla:** `/accounts/login/`

**Campos:**
- `username` — requerido
- `password` — requerido

**Flujo exitoso:**
1. `authenticate()` valida credenciales
2. `login()` crea sesión
3. Redirige a `next` (si existe en query param) o a `/groups/`

**Flujo fallido:**
- Mensaje de error genérico: "Usuario o contraseña incorrectos" (nunca indicar cuál de los dos falló)
- No bloquear cuenta tras intentos fallidos en MVP (agregar en v2 con `django-axes`)
- Rate limiting aplicado (ver sección 5.2)

**Seguridad sesión:**
- `SESSION_COOKIE_HTTPONLY = True` (siempre)
- `SESSION_COOKIE_SECURE = True` (producción)
- `SESSION_COOKIE_SAMESITE = "Lax"` (protección CSRF)
- `SESSION_EXPIRE_AT_BROWSER_CLOSE = False`
- Duración de sesión: 14 días (`SESSION_COOKIE_AGE = 1209600`)

**Template:** `accounts/login.html`

---

### 2.3 Logout

**Endpoint:** `POST /accounts/logout/` (solo POST, nunca GET)

- Invalida la sesión con `logout()`
- Redirige a `/accounts/login/`
- El botón de logout en el frontend debe estar dentro de un `<form method="POST">` con CSRF token

---

### 2.4 Cambio de contraseña

**Endpoint:** `GET/POST /accounts/password/change/` (requiere login)

Usa el `PasswordChangeView` nativo de Django con validadores configurados en `AUTH_PASSWORD_VALIDATORS`:

```python
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
```

Tras el cambio exitoso, invalida todas las sesiones del usuario excepto la actual usando `update_session_auth_hash()`.

---

### 2.5 Perfil de usuario

**Endpoint:** `GET/POST /accounts/profile/` (requiere login)

**Campos editables:**
- `bio` — texto libre, máx 500 chars
- `avatar` — imagen (JPG/PNG/WEBP), máx 2 MB, validación de content-type en backend

**Solo lectura (mostrar):**
- `username`, `email`
- Estadísticas: `total_points`, `total_predictions`, `correct_predictions`, `accuracy_percentage`

**Validación de avatar en backend:**
```python
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_AVATAR_SIZE_MB = 2
```

---

## 3. Administración de Usuarios (Django Admin)

### 3.1 Quién administra usuarios

Solo los usuarios con `is_staff=True` acceden a `/admin/`. No existe panel de administración para usuarios regulares.

### 3.2 Acciones disponibles en el admin

**Sobre `User`:**
- Ver, crear, editar, desactivar (`is_active=False`)
- No eliminar físicamente (usar desactivación)
- Cambiar contraseña desde el admin
- Promover a staff (`is_staff=True`) solo para dar acceso al panel admin

**Sobre `UserProfile`:**
- Ver estadísticas
- Editar `bio` y `avatar` en casos de soporte

### 3.3 Desactivación de usuario

Un usuario con `is_active=False`:
- No puede hacer login
- Sus datos existentes (pronósticos, puntuaciones) se conservan
- No aparece en leaderboards activos

---

## 4. Reglas de Negocio — Cambios Formalizados

### 4.1 Torneos: solo el admin del sitio puede crearlos

**Regla:** Los torneos son creados exclusivamente por el administrador del sitio (usuario con `is_staff=True`) desde el panel Django Admin. Ningún usuario regular puede crear torneos, ni siquiera el admin de un grupo.

**Razón:** Los torneos representan competiciones reales (Champions League, Copa América, etc.) que se sincronizan con una API externa. Deben ser curados por el operador del sitio para garantizar consistencia de datos.

**Impacto en código:**

*Eliminado:* No debe existir ninguna vista pública para crear torneos. Si existe `POST /tournaments/create/` o similar, debe eliminarse.

*Existente y correcto:* La vista `activate_tournament` en `tournaments/infrastructure/views.py` permite a un admin de grupo **activar** un torneo existente en su grupo. Esto sí está permitido — los grupos eligen qué torneos (ya creados por el admin del sitio) quieren jugar.

*Protección en capa de dominio (`tournaments/domain/`):**
```python
# En TournamentService — NO es una vista, es validación de dominio
def create_tournament(self, dto: CreateTournamentDTO, requesting_user) -> Tournament:
    if not requesting_user.is_staff:
        raise PermissionDeniedError("Solo el administrador puede crear torneos")
    ...
```

*Protección en admin (`tournaments/infrastructure/admin.py`):*
- `Tournament` solo visible y editable para `is_staff=True` (comportamiento default del admin)
- Agregar `readonly_fields` en `MatchAdmin` para impedir edición manual de resultados (los resultados solo los actualiza el worker de sincronización)

**Flujo completo:**
```
Admin del sitio → Django Admin → Crea Tournament + sincroniza fixtures
                                        ↓
Admin de grupo → /groups/<slug>/tournaments/add/ → Activa el torneo en su grupo
                                        ↓
Miembro del grupo → Ve los partidos y hace pronósticos
```

---

### 4.2 Pronósticos: cierre estricto 2 horas antes del partido

**Regla:** Un usuario puede crear o editar un pronóstico **únicamente si faltan más de 2 horas** para el inicio del partido. Una vez que `ahora >= partido.match_date - 2 horas`, el pronóstico queda bloqueado permanentemente.

**Constante (reemplaza `PREDICTION_DEADLINE_MINUTES`):**

```python
# config/settings/base.py
PREDICTION_DEADLINE_MINUTES = 120  # 2 horas — NO configurable por usuario
```

La variable de entorno `PREDICTION_DEADLINE_MINUTES` se elimina del `.env.example`. Este valor es una regla de negocio, no configuración de infraestructura.

**Implementación en dominio (`predictions/domain/`):**

```python
# predictions/domain/entities.py
from datetime import datetime, timedelta, timezone

PREDICTION_DEADLINE_MINUTES = 120

class PredictionDeadline:
    @staticmethod
    def is_open(match_date: datetime) -> bool:
        now = datetime.now(tz=timezone.utc)
        deadline = match_date - timedelta(minutes=PREDICTION_DEADLINE_MINUTES)
        return now < deadline

    @staticmethod
    def minutes_remaining(match_date: datetime) -> int:
        now = datetime.now(tz=timezone.utc)
        deadline = match_date - timedelta(minutes=PREDICTION_DEADLINE_MINUTES)
        delta = deadline - now
        return max(0, int(delta.total_seconds() / 60))
```

**Regla en el servicio de aplicación:**

```python
# predictions/application/services.py
def create_or_update_prediction(self, dto: CreatePredictionDTO) -> Prediction:
    match = self.match_repo.get_by_id(dto.match_id)
    if not PredictionDeadline.is_open(match.match_date):
        raise PredictionDeadlinePassedError(
            "El plazo para pronosticar este partido ha cerrado (2 horas antes del inicio)"
        )
    ...
```

**Protección en vista (segunda línea de defensa):**

```python
# predictions/infrastructure/views.py
@login_required
def predict_view(request, slug, tournament_id, match_id):
    match = get_object_or_404(Match, id=match_id)
    if not PredictionDeadline.is_open(match.match_date):
        messages.error(request, "El plazo para pronosticar este partido ha cerrado")
        return redirect("tournaments:detail", slug=slug, tournament_id=tournament_id)
    ...
```

**En el template (UI):** Mostrar el tiempo restante para cerrar el pronóstico. Una vez cerrado, reemplazar el formulario por el resultado del pronóstico existente (solo lectura). No ocultar el estado — mostrarlo explícitamente.

---

## 5. Seguridad — Hardening Frontend y Backend

### 5.1 Validación de inputs

**Regla:** Toda validación de negocio ocurre en el backend. El frontend puede tener validación HTML5 (`required`, `minlength`, `type="email"`) solo como ayuda UX — nunca como barrera de seguridad.

**En formularios Django (Forms):**

```python
# accounts/infrastructure/forms.py
class RegisterForm(UserCreationForm):
    username = forms.CharField(
        min_length=3,
        max_length=30,
        validators=[RegexValidator(r'^[\w]+$', 'Solo letras, números y guion bajo')]
    )
    email = forms.EmailField(max_length=254)

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Este email ya está registrado")
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso")
        return username
```

**Nota de seguridad:** La validación de unicidad de email/username en el form da información al atacante. Evaluar si en el contexto privado del sistema esto es aceptable. Para MVP sí lo es.

**En todos los formularios:**
- `strip=True` por defecto en `CharField`
- Longitudes máximas siempre definidas
- No confiar en `request.POST` directamente — siempre pasar por un `Form` o `ModelForm`

---

### 5.2 Rate limiting

Instalar `django-ratelimit` (agregar a `requirements/base.txt`).

**Endpoints a proteger:**

| Endpoint | Límite | Clave |
|---|---|---|
| `POST /accounts/login/` | 10 intentos / 5 min | IP |
| `POST /accounts/register/` | 5 intentos / 10 min | IP |
| `POST /accounts/password/change/` | 5 intentos / 10 min | usuario |
| `POST /groups/join/` | 10 intentos / 5 min | usuario |

**Implementación:**

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key="ip", rate="10/5m", method="POST", block=True)
def login_view(request):
    ...

@ratelimit(key="ip", rate="5/10m", method="POST", block=True)
def register_view(request):
    ...
```

Si se excede el límite, retornar HTTP 429 con un template de error amigable (no el default de Django).

---

### 5.3 CSRF

- Siempre habilitado (Django default)
- Todos los formularios POST incluyen `{% csrf_token %}`
- El `logout` usa POST (no GET) con CSRF token
- En producción: `CSRF_COOKIE_SECURE = True`, `CSRF_COOKIE_HTTPONLY = True`

---

### 5.4 Autorización por vista

**Principio:** cada vista verifica que el usuario autenticado tenga permiso para la acción solicitada. No asumir que "si llegó hasta aquí ya tiene permiso".

**Patrón estándar:**

```python
@login_required  # ← 1. ¿Está autenticado?
def predict_view(request, slug, tournament_id, match_id):
    group = get_object_or_404(Group, slug=slug)
    membership = get_object_or_404(GroupMembership, user=request.user, group=group)
    # ↑ 2. ¿Es miembro del grupo? Si no, 404 (no revelar que el grupo existe)
    match = get_object_or_404(Match, id=match_id, tournament__grouptournament__group=group)
    # ↑ 3. ¿El partido pertenece a un torneo activo en este grupo?
```

**Reglas por recurso:**

| Recurso | Quién puede leer | Quién puede escribir |
|---|---|---|
| Torneos (crear) | `is_staff` | `is_staff` (solo Django Admin) |
| Torneos (activar en grupo) | Miembro del grupo | Admin del grupo |
| Pronósticos propios | Dueño | Dueño (si deadline abierto) |
| Pronósticos del grupo | Miembro del grupo (solo tras cierre del deadline) | — |
| Leaderboard | Miembro del grupo | — |
| Miembros del grupo | Miembro del grupo | Admin del grupo |

---

### 5.5 Protección de templates

**Regla:** nunca mostrar datos sensibles de otros usuarios en templates.

```django
{# CORRECTO: pronósticos del rival solo si el deadline cerró #}
{% if match.is_deadline_passed %}
    {% for pred in match.predictions.all %}
        {{ pred.user.username }}: {{ pred.home_goals }}-{{ pred.away_goals }}
    {% endfor %}
{% else %}
    <p>Los pronósticos de otros jugadores se revelan cuando cierre el plazo.</p>
{% endif %}
```

**Escapado automático:** Django escapa HTML por defecto. No usar `| safe` salvo contenido explícitamente controlado.

---

### 5.6 Headers de seguridad HTTP

Activar `django.middleware.security.SecurityMiddleware` (ya incluido) y configurar:

```python
# config/settings/production.py
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

En desarrollo estas opciones deben estar desactivadas para no forzar HTTPS local.

---

### 5.7 Subida de archivos (avatares)

```python
# accounts/infrastructure/forms.py
import magic  # python-magic — detecta content-type real, no el declarado

class ProfileForm(ModelForm):
    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError("El avatar no puede superar 2 MB")
            mime = magic.from_buffer(avatar.read(2048), mime=True)
            avatar.seek(0)
            if mime not in ["image/jpeg", "image/png", "image/webp"]:
                raise forms.ValidationError("Formato no válido. Solo JPG, PNG o WEBP")
        return avatar
```

Agregar `python-magic` a `requirements/base.txt`. Los avatares se sirven desde una ruta separada, nunca desde `STATIC_ROOT`.

---

### 5.8 Dependencias de seguridad a agregar

```
# requirements/base.txt (agregar)
django-ratelimit==4.*
python-magic==0.4.*

# requirements/production.txt (agregar)
django-axes==7.*      # para v2: bloqueo de cuentas tras intentos fallidos
```

---

## 6. Cambios a Aplicar en el Código Existente

### Prioridad 1 — Reglas de negocio (bloqueantes)

| Archivo | Cambio |
|---|---|
| `config/settings/base.py` | `PREDICTION_DEADLINE_MINUTES = 120` como constante fija, remover de `.env.example` |
| `predictions/domain/entities.py` | Agregar clase `PredictionDeadline` con `is_open()` y `minutes_remaining()` |
| `predictions/application/services.py` | Usar `PredictionDeadline.is_open()` antes de crear/editar pronóstico |
| `predictions/infrastructure/views.py` | Verificar `PredictionDeadline.is_open()` antes de renderizar el form |
| `tournaments/infrastructure/views.py` | Eliminar cualquier vista que permita a usuarios no-staff **crear** torneos |

### Prioridad 2 — Seguridad (implementar antes del primer deploy)

| Archivo | Cambio |
|---|---|
| `requirements/base.txt` | Agregar `django-ratelimit`, `python-magic` |
| `config/settings/base.py` | Agregar `AUTH_PASSWORD_VALIDATORS` completo |
| `config/settings/production.py` | Agregar todos los headers de seguridad HTTP (sección 5.6) |
| `accounts/infrastructure/views.py` | Agregar `@ratelimit` en `login_view` y `register_view` |
| `accounts/infrastructure/forms.py` | Agregar validadores de unicidad, longitud y regex |
| `accounts/infrastructure/forms.py` | Agregar `clean_avatar()` con validación de mime type |
| `templates/accounts/login.html` | Cambiar logout a `<form POST>` si no lo está |

### Prioridad 3 — UX de seguridad (antes de usuarios reales)

| Componente | Cambio |
|---|---|
| Template `predictions/predict.html` | Mostrar countdown al cierre del plazo |
| Template `predictions/group_predictions.html` | Ocultar pronósticos ajenos hasta que cierre el deadline |
| Template `tournaments/detail.html` | Indicar claramente qué partidos tienen el plazo cerrado |

---

## 7. Orden de Implementación

```
1. settings: fijar PREDICTION_DEADLINE_MINUTES = 120, agregar AUTH_PASSWORD_VALIDATORS
2. predictions/domain: implementar PredictionDeadline
3. predictions/application: usar PredictionDeadline en create_or_update_prediction
4. predictions/views: guard en predict_view
5. requirements: agregar django-ratelimit, python-magic
6. accounts/forms: validadores + clean_avatar
7. accounts/views: @ratelimit en login y register
8. templates: countdown, ocultar pronósticos, marcar partidos cerrados
9. settings/production: headers HTTP de seguridad
10. Verificación manual: intentar crear torneo como usuario normal → debe fallar
11. Verificación manual: intentar pronosticar partido < 2h → debe fallar
```

---

*Este spec complementa el spec v1.0. En caso de conflicto, este documento prevalece sobre las secciones correspondientes del v1.0.*
