import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Fecha",
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
                ("numero", models.PositiveSmallIntegerField()),
                ("nombre", models.CharField(max_length=100)),
                ("fecha_inicio", models.DateField()),
                ("fecha_fin", models.DateField()),
                (
                    "torneo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fechas",
                        to="tournaments.tournament",
                    ),
                ),
            ],
            options={
                "verbose_name": "Fecha / Jornada",
                "db_table": "tournaments_fecha",
                "ordering": ["numero"],
                "unique_together": {("torneo", "numero")},
            },
        ),
        migrations.AddField(
            model_name="match",
            name="fecha",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="partidos",
                to="tournaments.fecha",
            ),
        ),
    ]
