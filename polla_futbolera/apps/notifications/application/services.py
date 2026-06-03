from django.core.mail import send_mail
from django.conf import settings

from .dtos import NotificationDTO
from ..infrastructure.models import Notification


class NotificationService:
    def create(
        self,
        user_id: int,
        notification_type: str,
        message: str,
        metadata: dict | None = None,
    ) -> Notification:
        return Notification.objects.create(
            user_id=user_id,
            notification_type=notification_type,
            message=message,
            metadata=metadata or {},
        )

    def get_for_user(self, user_id: int, limit: int = 50) -> list[NotificationDTO]:
        notifications = Notification.objects.filter(user_id=user_id).order_by("-created_at")[:limit]
        return [
            NotificationDTO(
                id=n.id,
                notification_type=n.notification_type,
                message=n.message,
                read=n.read,
                created_at=n.created_at,
            )
            for n in notifications
        ]

    def mark_read(self, notification_id: int, user_id: int) -> None:
        Notification.objects.filter(id=notification_id, user_id=user_id).update(read=True)

    def mark_all_read(self, user_id: int) -> None:
        Notification.objects.filter(user_id=user_id, read=False).update(read=True)

    def send_invitation(
        self,
        user_id: int,
        group_name: str,
        invite_link: str,
        user_email: str,
    ) -> None:
        self.create(
            user_id,
            "invitation",
            f"Te invitaron al grupo '{group_name}'",
            {"invite_link": invite_link},
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@polla.com")
        send_mail(
            subject=f"Invitación al grupo {group_name}",
            message=f"Únete usando este link: {invite_link}",
            from_email=from_email,
            recipient_list=[user_email],
            fail_silently=True,
        )
