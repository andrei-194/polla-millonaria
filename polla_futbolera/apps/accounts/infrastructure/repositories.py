from ..domain.entities import UserProfile as UserProfileEntity
from .models import UserProfile
import uuid


class UserProfileRepository:
    def get_by_user_id(self, user_id: uuid.UUID) -> UserProfileEntity | None:
        try:
            p = UserProfile.objects.get(user_id=user_id)
            return UserProfileEntity(
                user_id=p.user_id,
                bio=p.bio,
                total_points=p.total_points,
                total_predictions=p.total_predictions,
                correct_predictions=p.correct_predictions,
            )
        except UserProfile.DoesNotExist:
            return None
