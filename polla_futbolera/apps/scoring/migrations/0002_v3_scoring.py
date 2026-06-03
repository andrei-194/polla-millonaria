import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scoring", "0001_initial"),
        ("predictions", "0002_v3_eventos"),
        ("quinielas", "0001_initial"),
        ("tournaments", "0002_fecha_match_fecha_fk"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReglaPuntuacion",
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
                ("codigo_acierto", models.CharField(max_length=20)),
                ("puntos", models.SmallIntegerField()),
                (
                    "tipo_evento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reglas",
                        to="predictions.tipoevento",
                    ),
                ),
                (
                    "quiniela",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reglas_puntos",
                        to="quinielas.quiniela",
                    ),
                ),
            ],
            options={
                "verbose_name": "Regla de Puntuación",
                "db_table": "scoring_regla_puntuacion",
                "unique_together": {("tipo_evento", "quiniela", "codigo_acierto")},
            },
        ),
        migrations.CreateModel(
            name="PuntuacionEvento",
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
                ("valor_pronosticado", models.CharField(max_length=50)),
                ("valor_resultado", models.CharField(max_length=50)),
                ("codigo_acierto", models.CharField(max_length=20)),
                ("puntos", models.SmallIntegerField(default=0)),
                ("calculado_en", models.DateTimeField(auto_now=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="puntuaciones",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "evento_partido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="puntuaciones",
                        to="predictions.eventopartido",
                    ),
                ),
                (
                    "quiniela",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="puntuaciones",
                        to="quinielas.quiniela",
                    ),
                ),
            ],
            options={
                "verbose_name": "Puntuación de Evento",
                "db_table": "scoring_puntuacion_evento",
                "unique_together": {("usuario", "evento_partido")},
            },
        ),
        migrations.CreateModel(
            name="RankingFecha",
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
                ("puntos", models.SmallIntegerField(default=0)),
                ("posicion", models.PositiveSmallIntegerField(default=0)),
                ("calculado_en", models.DateTimeField(auto_now=True)),
                (
                    "quiniela",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rankings_fecha",
                        to="quinielas.quiniela",
                    ),
                ),
                (
                    "fecha",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rankings",
                        to="tournaments.fecha",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rankings_fecha",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Ranking por Fecha",
                "db_table": "scoring_ranking_fecha",
                "ordering": ["posicion"],
                "unique_together": {("quiniela", "fecha", "usuario")},
            },
        ),
        migrations.CreateModel(
            name="RankingAcumulado",
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
                ("puntos_total", models.SmallIntegerField(default=0)),
                ("posicion", models.PositiveSmallIntegerField(default=0)),
                ("fechas_jugadas", models.PositiveSmallIntegerField(default=0)),
                ("exactos_total", models.PositiveSmallIntegerField(default=0)),
                ("aciertos_total", models.PositiveSmallIntegerField(default=0)),
                ("calculado_en", models.DateTimeField(auto_now=True)),
                (
                    "quiniela",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ranking_acumulado",
                        to="quinielas.quiniela",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ranking_acumulado",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Ranking Acumulado",
                "db_table": "scoring_ranking_acumulado",
                "ordering": ["posicion"],
                "unique_together": {("quiniela", "usuario")},
            },
        ),
    ]
