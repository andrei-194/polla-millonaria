from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Anuncio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titulo", models.CharField(max_length=120)),
                ("cuerpo", models.TextField(help_text="Texto visible para el jugador. HTML básico permitido.")),
                ("emoji", models.CharField(blank=True, default="", max_length=10)),
                ("cta_texto", models.CharField(blank=True, default="", max_length=60, verbose_name="Texto del botón")),
                ("cta_url", models.CharField(blank=True, default="", max_length=200, verbose_name="URL del botón")),
                ("activo", models.BooleanField(default=True)),
                ("inicio", models.DateTimeField(blank=True, help_text="Dejar vacío para mostrar desde ya.", null=True)),
                ("fin", models.DateTimeField(blank=True, help_text="Dejar vacío para no vencer nunca.", null=True)),
                ("orden", models.PositiveSmallIntegerField(default=0, help_text="Menor número = aparece primero.")),
            ],
            options={
                "verbose_name": "Anuncio",
                "verbose_name_plural": "Anuncios",
                "ordering": ["orden", "-id"],
            },
        ),
    ]
