from django import forms
from .models import Prediction


class PredictionForm(forms.ModelForm):
    class Meta:
        model = Prediction
        fields = ("home_goals", "away_goals")
        widgets = {
            "home_goals": forms.NumberInput(
                attrs={"min": 0, "max": 20, "class": "form-control"}
            ),
            "away_goals": forms.NumberInput(
                attrs={"min": 0, "max": 20, "class": "form-control"}
            ),
        }
