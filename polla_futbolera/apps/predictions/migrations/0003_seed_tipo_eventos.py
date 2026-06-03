from django.db import migrations


TIPOS_EVENTO = [
    {
        "codigo": "SCORE",
        "nombre": "Marcador Exacto",
        "descripcion": "¿Cuál será el marcador final?",
        "config": {},
    },
    {
        "codigo": "WINNER",
        "nombre": "Ganador del Partido",
        "descripcion": "¿Quién gana el partido? H=Local, D=Empate, A=Visitante",
        "config": {"choices": ["H", "D", "A"]},
    },
    {
        "codigo": "BTTS",
        "nombre": "Ambos Anotan",
        "descripcion": "¿Anotan ambos equipos?",
        "config": {"choices": ["yes", "no"]},
    },
    {
        "codigo": "OU25",
        "nombre": "Más/Menos 2.5 Goles",
        "descripcion": "¿Más o menos de 2.5 goles totales en el partido?",
        "config": {"choices": ["over", "under"], "threshold": 2.5},
    },
]


def seed_tipos_evento(apps, schema_editor):
    TipoEvento = apps.get_model("predictions", "TipoEvento")
    for tipo in TIPOS_EVENTO:
        TipoEvento.objects.get_or_create(codigo=tipo["codigo"], defaults=tipo)


def rollback_tipos_evento(apps, schema_editor):
    TipoEvento = apps.get_model("predictions", "TipoEvento")
    TipoEvento.objects.filter(codigo__in=["SCORE", "WINNER", "BTTS", "OU25"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("predictions", "0002_v3_eventos"),
    ]

    operations = [
        migrations.RunPython(seed_tipos_evento, rollback_tipos_evento),
    ]
