from django import forms
from .models import Group


class CreateGroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", "description")


class JoinGroupForm(forms.Form):
    invitation_code = forms.CharField(max_length=30, label="Código de invitación")
