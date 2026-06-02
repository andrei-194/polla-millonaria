from django import forms
from django.contrib.auth import get_user_model
from .models import Inscripcion

User = get_user_model()


class InscribirJugadorForm(forms.Form):
    jugador = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Jugador",
        empty_label="Selecciona un jugador",
    )

    def __init__(self, *args, quiniela=None, **kwargs):
        super().__init__(*args, **kwargs)
        ya_inscritos = []
        if quiniela is not None:
            ya_inscritos = Inscripcion.objects.filter(
                quiniela=quiniela, activa=True
            ).values_list("jugador_id", flat=True)
        self.fields["jugador"].queryset = (
            User.objects.filter(groups__name="Jugador", is_active=True)
            .exclude(id__in=ya_inscritos)
            .order_by("username")
        )
