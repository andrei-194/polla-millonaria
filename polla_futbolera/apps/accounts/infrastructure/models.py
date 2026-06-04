import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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


def _default_expiry():
    return timezone.now() + timedelta(hours=72)


class InvitationCode(models.Model):
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_invitation_codes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    uses_count = models.IntegerField(default=0)
    max_uses = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "accounts_invitationcode"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active", "created_at"], name="idx_invitation_active_created"),
        ]

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() >= self.expires_at:
            return False
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True

    def register_use(self):
        self.uses_count += 1
        self.save(update_fields=["uses_count"])

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=["is_active"])

    def __str__(self):
        return f"InvitationCode({self.code}, active={self.is_active})"
