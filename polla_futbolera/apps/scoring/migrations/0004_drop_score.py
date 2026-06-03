from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scoring", "0003_seed_reglas_globales"),
    ]

    operations = [
        migrations.DeleteModel(name="Score"),
    ]
