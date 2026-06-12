"""
Elimina los registros Match duplicados del WC2026 creados por re-ejecuciones
del seed después de que sync_wc2026_ids ya había mapeado los external_id.

SOLO OPERA EN LOCAL — no ejecutar en producción hasta validar.

Reglas:
  1. Para cada par (sintético WC2026-XXX + numérico con mismo equipo/fecha):
     - Si el sintético tiene PronosticoEvento → abortar (situación inesperada)
     - Si no → borrar EventoPartido del sintético, borrar Match sintético
  2. Entre variantes de código (WC2026-KSA-URU vs WC2026-KSA-URY):
     - Conservar el que tenga match_date más reciente (ya sincronizado)
     - Si ambos tienen 0 pronós → borrar el "peor" (código más viejo)

Uso:
    python manage.py dedup_wc2026_matches --dry-run
    python manage.py dedup_wc2026_matches
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Elimina duplicados Match sintéticos del WC2026 manteniendo los registros numéricos."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Muestra qué se eliminaría sin aplicar cambios.")

    def handle(self, *args, **options):
        from apps.tournaments.infrastructure.models import Match, Tournament
        from apps.predictions.infrastructure.models import EventoPartido, PronosticoEvento

        dry_run = options["dry_run"]
        prefix = "[DRY-RUN] " if dry_run else ""

        t = Tournament.objects.filter(external_code="WC2026").first()
        if not t:
            self.stdout.write(self.style.ERROR("Torneo WC2026 no encontrado."))
            return

        sinteticos = list(
            Match.objects.filter(tournament=t, external_id__startswith="WC2026")
            .select_related("home_team", "away_team")
        )
        numericos = list(
            Match.objects.filter(tournament=t, external_id__regex=r"^\d+$")
            .select_related("home_team", "away_team")
        )

        self.stdout.write(
            f"\n{prefix}BD: {len(sinteticos)} sintéticos | {len(numericos)} numéricos | "
            f"total {len(sinteticos)+len(numericos)}\n"
        )

        # ── Paso 1: encontrar pares (sintético ↔ numérico mismo partido) ──────
        pares = []
        sinteticos_sin_par = list(sinteticos)

        for n in numericos:
            for s in sinteticos:
                if (s.home_team_id == n.home_team_id and
                        s.away_team_id == n.away_team_id and
                        abs((s.match_date - n.match_date).total_seconds()) < 14400):  # ±4h
                    pares.append((s, n))
                    if s in sinteticos_sin_par:
                        sinteticos_sin_par.remove(s)
                    break

        self.stdout.write(f"  Pares sintético↔numérico: {len(pares)}")
        self.stdout.write(f"  Sintéticos sin par numérico: {len(sinteticos_sin_par)}\n")

        # ── Paso 2: verificar que ningún sintético a borrar tenga pronósticos ──
        a_borrar_sinteticos = [s for s, n in pares]
        ev_con_pronos = (
            EventoPartido.objects
            .filter(partido__in=a_borrar_sinteticos)
            .filter(pronosticos__isnull=False)
            .distinct()
        )
        if ev_con_pronos.exists():
            self.stdout.write(self.style.ERROR(
                "ABORTAR: hay pronósticos en registros sintéticos que se querían borrar. "
                "Revisar manualmente antes de continuar."
            ))
            for ev in ev_con_pronos:
                self.stdout.write(f"  EventoPartido {ev.id} — {ev.partido}")
            return

        # ── Paso 3: eliminar los 57 sintéticos con par numérico ───────────────
        eliminados_ev = 0
        eliminados_match = 0

        self.stdout.write(self.style.SUCCESS(
            f"  {prefix}Eliminando {len(a_borrar_sinteticos)} Match sintéticos "
            f"(y sus EventoPartido) que tienen duplicado numérico..."
        ))

        if not dry_run:
            with transaction.atomic():
                for s in a_borrar_sinteticos:
                    ev_count = EventoPartido.objects.filter(partido=s).count()
                    EventoPartido.objects.filter(partido=s).delete()
                    s.delete()
                    eliminados_ev += ev_count
                    eliminados_match += 1

        # ── Paso 4: detectar duplicados por variante de código dentro de sinteticos_sin_par ──
        self.stdout.write(
            f"\n{prefix}Analizando {len(sinteticos_sin_par)} sintéticos sin par numérico..."
        )

        procesados = set()
        code_dupes_borrar = []

        def _same_team(t1, t2):
            """Compara equipos por nombre normalizado (cubre variantes URY/URU)."""
            import unicodedata
            def norm(s):
                if not s:
                    return ""
                nfkd = unicodedata.normalize("NFKD", s.lower())
                return "".join(c for c in nfkd if not unicodedata.combining(c))
            return norm(t1.name) == norm(t2.name)

        for i, s1 in enumerate(sinteticos_sin_par):
            if id(s1) in procesados:
                continue
            for s2 in sinteticos_sin_par[i+1:]:
                if id(s2) in procesados:
                    continue
                if (s1.home_team and s2.home_team and s1.away_team and s2.away_team and
                        _same_team(s1.home_team, s2.home_team) and
                        _same_team(s1.away_team, s2.away_team) and
                        abs((s1.match_date - s2.match_date).total_seconds()) < 7200):
                    # Son el mismo partido con distinto código de equipo
                    pron1 = PronosticoEvento.objects.filter(evento_partido__partido=s1).count()
                    pron2 = PronosticoEvento.objects.filter(evento_partido__partido=s2).count()
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Variante código: {s1.external_id} (pronos={pron1}) "
                            f"vs {s2.external_id} (pronos={pron2})"
                        )
                    )
                    if pron1 == 0 and pron2 == 0:
                        # Conservar el primero (orden alfabético → el más reciente del seed)
                        code_dupes_borrar.append(s2)
                        procesados.add(id(s2))
                        self.stdout.write(f"    → Conservar {s1.external_id}, borrar {s2.external_id}")
                    elif pron1 > 0 and pron2 == 0:
                        code_dupes_borrar.append(s2)
                        procesados.add(id(s2))
                        self.stdout.write(f"    → Conservar {s1.external_id} (tiene pronos), borrar {s2.external_id}")
                    elif pron2 > 0 and pron1 == 0:
                        code_dupes_borrar.append(s1)
                        procesados.add(id(s1))
                        self.stdout.write(f"    → Conservar {s2.external_id} (tiene pronos), borrar {s1.external_id}")
                    else:
                        self.stdout.write(self.style.ERROR(
                            f"    CONFLICTO: ambos tienen pronósticos. Revisar manualmente."
                        ))
                    procesados.add(id(s1))

        if code_dupes_borrar:
            self.stdout.write(
                f"\n{prefix}Eliminando {len(code_dupes_borrar)} variantes de código duplicadas..."
            )
            if not dry_run:
                with transaction.atomic():
                    for m in code_dupes_borrar:
                        ev_count = EventoPartido.objects.filter(partido=m).count()
                        EventoPartido.objects.filter(partido=m).delete()
                        m.delete()
                        eliminados_ev += ev_count
                        eliminados_match += 1

        # ── Resumen final ──────────────────────────────────────────────────────
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"  [DRY-RUN] Se eliminarían: "
                f"{len(a_borrar_sinteticos) + len(code_dupes_borrar)} Match + "
                f"sus EventoPartido\n"
                f"  → Ejecuta sin --dry-run para aplicar."
            ))
        else:
            restantes = Match.objects.filter(tournament=t).count()
            self.stdout.write(self.style.SUCCESS(
                f"  Eliminados: {eliminados_match} Match | {eliminados_ev} EventoPartido\n"
                f"  Matches restantes en BD: {restantes}"
            ))
