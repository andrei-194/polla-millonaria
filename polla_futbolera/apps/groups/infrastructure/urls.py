from django.urls import path
from . import views

app_name = "groups"

urlpatterns = [
    path("", views.group_list, name="list"),
    path("create/", views.group_create, name="create"),
    path("join/", views.group_join, name="join"),
    path("<slug:slug>/", views.group_detail, name="detail"),
    path("<slug:slug>/invite/", views.group_invite, name="invite"),
    path("<slug:slug>/members/<int:user_id>/remove/", views.member_remove, name="member_remove"),
]
