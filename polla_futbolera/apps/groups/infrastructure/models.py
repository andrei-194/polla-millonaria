from django.conf import settings
from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=120)
    description = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_groups"
    )
    invitation_code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups_group"

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    ROLE_CHOICES = [("admin", "Admin"), ("member", "Member")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups_membership"
        unique_together = ("user", "group")

    def is_admin(self) -> bool:
        return self.role == "admin"

    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"
