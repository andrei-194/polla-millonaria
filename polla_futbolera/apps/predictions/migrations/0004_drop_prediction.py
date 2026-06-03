from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("predictions", "0003_seed_tipo_eventos"),
    ]

    operations = [
        migrations.DeleteModel(name="Prediction"),
    ]
