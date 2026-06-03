from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .models import Tournament


@login_required
def tournament_list(request):
    tournaments = Tournament.objects.filter(status="active")
    return render(request, "tournaments/list.html", {"tournaments": tournaments})
