from django import template

register = template.Library()

_PHASE_TRANSLATIONS = {
    "group": "Fase de grupos",
    "group_stage": "Fase de grupos",
    "regular_season": "Temporada regular",
    "round_of_16": "Octavos de final",
    "last_16": "Octavos de final",
    "round_of_8": "Cuartos de final",
    "quarter_final": "Cuartos de final",
    "quarter_finals": "Cuartos de final",
    "round_of_4": "Semifinales",
    "semi_final": "Semifinales",
    "semi_finals": "Semifinales",
    "third_place": "Tercer puesto",
    "final": "Final",
    "playoff": "Playoff",
    "playoff_round_1": "Playoff — 1ª ronda",
    "playoff_round_2": "Playoff — 2ª ronda",
}


@register.filter
def phase_es(value):
    if not value:
        return value
    return _PHASE_TRANSLATIONS.get(value.lower(), value.replace("_", " ").title())
