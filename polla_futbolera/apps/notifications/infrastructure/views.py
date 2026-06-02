from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from ..application.services import NotificationService


@login_required
def notification_list(request):
    service = NotificationService()
    notifications = service.get_for_user(request.user.id)
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
@require_POST
def mark_read(request, notification_id):
    service = NotificationService()
    service.mark_read(notification_id, request.user.id)
    return redirect("notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    service = NotificationService()
    service.mark_all_read(request.user.id)
    return redirect("notifications:list")
