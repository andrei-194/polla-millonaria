from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0003_match_idx_match_tournament_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="home_score_et",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="match",
            name="away_score_et",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="match",
            name="home_score_pen",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="match",
            name="away_score_pen",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="match",
            name="match_duration",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="match",
            name="penalty_winner",
            field=models.CharField(blank=True, max_length=1, null=True),
        ),
    ]
