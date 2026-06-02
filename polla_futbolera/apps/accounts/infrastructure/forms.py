from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserProfile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("bio", "avatar")
