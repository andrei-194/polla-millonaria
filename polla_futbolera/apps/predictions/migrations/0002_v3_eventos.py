import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("predictions", "0001_initial"),
        ("quinielas", "0001_initial"),
        ("tournaments", "0002_fecha_match_fecha_fk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TipoEvento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("codigo", models.CharField(max_length=20, unique=True)),
                ("nombre", models.CharField(max_length=100)),
                ("descripcion", models.TextField(blank=True)),
                ("config", models.JSONField(default=dict)),
                ("activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Tipo de Evento",
                "db_table": "predictions_tipo_evento",
            },
        ),
        migrations.CreateModel(
            name="EventoPartido",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("abierto", "Abierto"),
                            ("cerrado", "Cerrado"),
                            ("puntuado", "Puntuado"),
                            ("cancelado", "Cancelado"),
                        ],
                        default="abierto",
                        max_length=20,
                    ),
                ),
                ("resultado", models.CharField(blank=True, max_length=50, null=True)),
                ("plazo_cierre", models.DateTimeField()),
                (
                    "partido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="eventos",
                        to="tournaments.match",
                    ),
                ),
                (
                    "quiniela",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="eventos",
                        to="quinielas.quiniela",
                    ),
                ),
                (
                    "tipo_evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="eventos",
                        to="predictions.tipoevento",
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento de Partido",
                "db_table": "predictions_evento_partido",
                "unique_together": {("partido", "quiniela", "tipo_evento")},
            },
        ),
        migrations.CreateModel(
            name="PronosticoEvento",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("valor", models.CharField(max_length=50)),
                ("enviado_en", models.DateTimeField(auto_now=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pronosticos_eventos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "evento_partido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pronosticos",
                        to="predictions.eventopartido",
                    ),
                ),
            ],
            options={
                "verbose_name": "Pronóstico de Evento",
                "db_table": "predictions_pronostico_evento",
                "unique_together": {("usuario", "evento_partido")},
            },
        ),
    ]
