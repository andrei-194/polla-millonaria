from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import User, UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, label="Nombre")
    last_name = forms.CharField(max_length=150, required=False, label="Apellido")

    class Meta:
        model = UserProfile
        fields = ("bio", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            profile.user.first_name = self.cleaned_data["first_name"]
            profile.user.last_name = self.cleaned_data["last_name"]
            profile.user.save(update_fields=["first_name", "last_name"])
        return profile


class GenerarCodigoForm(forms.Form):
    max_uses = forms.IntegerField(
        required=False,
        min_value=1,
        label="Máximo de usos",
        help_text="Dejá vacío para usos ilimitados",
    )
    expires_at = forms.DateTimeField(
        required=False,
        label="Fecha de expiración",
        help_text="Dejá vacío para sin expiración",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )


class RegistroViaCodigoForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
