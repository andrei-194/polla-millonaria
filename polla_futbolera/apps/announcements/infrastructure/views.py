from django.shortcuts import render


def como_jugar(request):
    return render(request, "como_jugar/index.html")
