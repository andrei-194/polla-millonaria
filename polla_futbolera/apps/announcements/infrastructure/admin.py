from django.contrib import admin
from .models import Anuncio


@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = ("orden", "emoji", "titulo", "activo", "inicio", "fin")
    list_display_links = ("titulo",)
    list_editable = ("activo", "orden")
    list_filter = ("activo",)
    search_fields = ("titulo", "cuerpo")
    ordering = ("orden", "-id")
    fieldsets = (
        (None, {"fields": ("titulo", "cuerpo", "emoji")}),
        ("Llamada a acción", {"fields": ("cta_texto", "cta_url")}),
        ("Visibilidad", {"fields": ("activo", "orden", "inicio", "fin")}),
    )
