from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)

    class Meta:
        db_table = "accounts_user"

    @property
    def accuracy_percentage(self) -> float:
        profile = getattr(self, "profile", None)
        if not profile:
            return 0.0
        return profile.accuracy_percentage


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    bio = models.TextField(blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    total_points = models.IntegerField(default=0)
    total_predictions = models.IntegerField(default=0)
    correct_predictions = models.IntegerField(default=0)

    class Meta:
        db_table = "accounts_userprofile"

    @property
    def accuracy_percentage(self) -> float:
        if self.total_predictions == 0:
            return 0.0
        return (self.correct_predictions / self.total_predictions) * 100

    def __str__(self):
        return f"Profile({self.user.username})"
