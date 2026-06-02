from django.contrib import admin
from .models import Quiniela, Inscripcion


@admin.register(Quiniela)
class QuinielaAdmin(admin.ModelAdmin):
    list_display = ("name", "tournament", "status", "created_at")
    list_filter = ("status", "tournament")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ("jugador", "quiniela", "activa", "inscrito_en")
    list_filter = ("activa", "quiniela")
    search_fields = ("jugador__username", "quiniela__name")
    raw_id_fields = ("jugador",)
