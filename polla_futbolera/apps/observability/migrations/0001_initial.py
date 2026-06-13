# Generated 2026-06-13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PerformanceMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(db_index=True, max_length=100)),
                ("duration_ms", models.FloatField()),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("quiniela_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("fecha_id", models.IntegerField(blank=True, null=True)),
                ("match_id", models.IntegerField(blank=True, null=True)),
                ("extra", models.JSONField(blank=True, default=dict)),
                ("success", models.BooleanField(default=True)),
                ("error_msg", models.TextField(blank=True)),
                ("alerta_enviada", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Métrica de Performance",
                "verbose_name_plural": "Métricas de Performance",
                "db_table": "observability_performance_metric",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="performancemetric",
            index=models.Index(fields=["label", "timestamp"], name="idx_pm_label_timestamp"),
        ),
        migrations.AddIndex(
            model_name="performancemetric",
            index=models.Index(fields=["timestamp"], name="idx_pm_timestamp"),
        ),
    ]
