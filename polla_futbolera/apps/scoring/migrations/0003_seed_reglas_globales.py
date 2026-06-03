from django.db import migrations


REGLAS_DEFAULTS = [
    ("SCORE",  "EXACT",     3),
    ("SCORE",  "GOAL_DIFF", 2),
    ("SCORE",  "WINNER",    1),
    ("SCORE",  "MISS",      0),
    ("WINNER", "HIT",       3),
    ("WINNER", "MISS",      0),
    ("BTTS",   "HIT",       2),
    ("BTTS",   "MISS",      0),
    ("OU25",   "HIT",       2),
    ("OU25",   "MISS",      0),
]


def seed_reglas(apps, schema_editor):
    TipoEvento = apps.get_model("predictions", "TipoEvento")
    ReglaPuntuacion = apps.get_model("scoring", "ReglaPuntuacion")
    for codigo_tipo, codigo_acierto, puntos in REGLAS_DEFAULTS:
        tipo = TipoEvento.objects.get(codigo=codigo_tipo)
        ReglaPuntuacion.objects.update_or_create(
            tipo_evento=tipo,
            quiniela=None,
            codigo_acierto=codigo_acierto,
            defaults={"puntos": puntos},
        )


def rollback_reglas(apps, schema_editor):
    ReglaPuntuacion = apps.get_model("scoring", "ReglaPuntuacion")
    ReglaPuntuacion.objects.filter(quiniela=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("scoring", "0002_v3_scoring"),
        ("predictions", "0003_seed_tipo_eventos"),
    ]

    operations = [
        migrations.RunPython(seed_reglas, rollback_reglas),
    ]
