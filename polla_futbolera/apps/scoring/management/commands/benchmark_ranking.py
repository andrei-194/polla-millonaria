"""
Management command para medir performance del pipeline de ranking.

Uso:
    python manage.py benchmark_ranking --usuarios 500 --fechas 20 --partidos 8 --limpiar
    python manage.py benchmark_ranking --usuarios 1000 --fechas 38 --partidos 10
    python manage.py benchmark_ranking --usuarios 50 --fechas 8 --partidos 8 --limpiar --verbose
"""
import datetime
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from apps.predictions.infrastructure.models import EventoPartido, PronosticoEvento, TipoEvento
from apps.quinielas.infrastructure.models import Inscripcion, Quiniela
from apps.scoring.application.services import RankingService, ScoringService
from apps.scoring.infrastructure.models import PuntuacionEvento
from apps.tournaments.infrastructure.models import Fecha, Match, Team, Tournament

User = get_user_model()

PREFIJO = "BENCHMARK_"


class Command(BaseCommand):
    help = "Genera datos sintéticos y mide el rendimiento del pipeline de ranking."

    def add_arguments(self, parser):
        parser.add_argument("--usuarios", type=int, default=100)
        parser.add_argument("--fechas", type=int, default=10)
        parser.add_argument("--partidos", type=int, default=8)
        parser.add_argument("--limpiar", action="store_true", default=False)
        parser.add_argument("--verbose", action="store_true", default=False)
        parser.add_argument("--solo-ranking", action="store_true", default=False,
                            help="Salta generación de datos, asume que ya existen.")

    def handle(self, *args, **options):
        n_usuarios = options["usuarios"]
        n_fechas = options["fechas"]
        n_partidos = options["partidos"]
        limpiar = options["limpiar"]
        verbose = options["verbose"]
        solo_ranking = options["solo_ranking"]

        sep = "═" * 62
        self.stdout.write(sep)
        self.stdout.write(
            f"  BENCHMARK RANKING — {n_usuarios} usuarios / {n_fechas} fechas / {n_partidos} partidos"
        )
        self.stdout.write(sep)

        if solo_ranking:
            torneo = Tournament.objects.filter(name__startswith=PREFIJO).first()
            if not torneo:
                self.stderr.write("No se encontró torneo BENCHMARK_*. Ejecutar sin --solo-ranking primero.")
                return
            quiniela = Quiniela.objects.filter(tournament=torneo).first()
            fechas = list(Fecha.objects.filter(torneo=torneo))
        else:
            torneo, quiniela, fechas = self._generar_datos(n_usuarios, n_fechas, n_partidos)

        self._ejecutar_benchmark(quiniela, fechas, n_usuarios, verbose)

        if limpiar:
            self._limpiar(torneo)

    def _generar_datos(self, n_usuarios, n_fechas, n_partidos):
        ts = int(time.time())
        self.stdout.write("  Generando datos...")

        # Torneo con prefijo reconocible
        torneo = Tournament.objects.create(
            name=f"{PREFIJO}{ts}",
            external_code=f"BM{ts}",
            season="BENCH",
            status="active",
        )
        quiniela = Quiniela.objects.create(
            name=f"Quiniela Bench {ts}",
            slug=f"bench-{ts}",
            tournament=torneo,
        )

        # Usuarios sintéticos
        usuarios = User.objects.bulk_create([
            User(username=f"bench_{ts}_{i}", email=f"bench_{ts}_{i}@bench.test")
            for i in range(n_usuarios)
        ])
        for u in usuarios:
            u.set_unusable_password()
        User.objects.bulk_update(usuarios, ["password"])
        self.stdout.write(f"    ✓ {n_usuarios} usuarios creados")

        # Inscribir todos
        Inscripcion.objects.bulk_create([
            Inscripcion(jugador=u, quiniela=quiniela)
            for u in usuarios
        ])

        # Tipos de evento (ya existen por migración)
        tipo_score, _ = TipoEvento.objects.get_or_create(
            codigo="SCORE", defaults={"nombre": "Marcador exacto", "config": {}}
        )
        tipo_winner, _ = TipoEvento.objects.get_or_create(
            codigo="WINNER",
            defaults={"nombre": "Ganador", "config": {"choices": ["H", "D", "A"]}},
        )

        # Equipos reutilizables para el bench
        equipo_a, _ = Team.objects.get_or_create(
            external_code="BENCH_A", defaults={"name": "Bench Home"}
        )
        equipo_b, _ = Team.objects.get_or_create(
            external_code="BENCH_B", defaults={"name": "Bench Away"}
        )

        hoy = datetime.date.today()
        total_eventos = 0
        total_pronosticos = 0
        fechas_creadas = []

        for f_num in range(1, n_fechas + 1):
            fecha = Fecha.objects.create(
                torneo=torneo,
                numero=f_num,
                nombre=f"Fecha {f_num}",
                fecha_inicio=hoy,
                fecha_fin=hoy + datetime.timedelta(days=6),
            )
            fechas_creadas.append(fecha)

            # Partidos de la fecha
            matches = Match.objects.bulk_create([
                Match(
                    tournament=torneo,
                    home_team=equipo_a,
                    away_team=equipo_b,
                    external_id=f"bm-{f_num}-{p}-{int(time.time() * 1000)}",
                    match_date=timezone.now() - datetime.timedelta(hours=2),
                    status="finished",
                    fecha=fecha,
                )
                for p in range(n_partidos)
            ])

            # 2 eventos por partido: SCORE y WINNER
            plazo_pasado = timezone.now() - datetime.timedelta(hours=2)
            eventos = EventoPartido.objects.bulk_create([
                EventoPartido(
                    partido=m,
                    quiniela=quiniela,
                    tipo_evento=tipo,
                    plazo_cierre=plazo_pasado,
                    resultado="2-1" if tipo == tipo_score else "H",
                )
                for m in matches
                for tipo in [tipo_score, tipo_winner]
            ])
            total_eventos += len(eventos)

            # Pronósticos: todos los usuarios pronostican todos los eventos (carga máxima)
            pronosticos_lote = []
            for ev in eventos:
                valor = "2-1" if ev.tipo_evento_id == tipo_score.id else "H"
                for u in usuarios:
                    pronosticos_lote.append(
                        PronosticoEvento(
                            usuario=u,
                            evento_partido=ev,
                            valor=valor,
                        )
                    )
            PronosticoEvento.objects.bulk_create(pronosticos_lote, ignore_conflicts=True)
            total_pronosticos += len(pronosticos_lote)

        self.stdout.write(
            f"    ✓ {n_fechas} fechas, {n_fechas * n_partidos} partidos, {total_eventos} eventos"
        )
        self.stdout.write(f"    ✓ {total_pronosticos:,} pronósticos insertados (bulk)")
        return torneo, quiniela, fechas_creadas

    def _ejecutar_benchmark(self, quiniela, fechas, n_usuarios, verbose):
        scoring_svc = ScoringService()
        ranking_svc = RankingService()

        # Benchmarkear 1 fecha individual
        primera_fecha = fechas[0]

        t0 = time.perf_counter()
        resultado = scoring_svc.calcular_puntos_fecha(quiniela.id, primera_fecha.id)
        t_scoring_1 = time.perf_counter() - t0

        pun_creadas = PuntuacionEvento.objects.filter(
            quiniela=quiniela,
            evento_partido__partido__fecha=primera_fecha,
        ).count()

        self.stdout.write("")
        self.stdout.write(f"  Fase 1: calcular_puntos_fecha (1 fecha × 1 quiniela)")
        self.stdout.write(f"    Eventos procesados: {resultado['ok']}")
        self.stdout.write(f"    Puntuaciones creadas: {pun_creadas:,}")
        self.stdout.write(f"    Tiempo: {t_scoring_1:.3f}s")

        t0 = time.perf_counter()
        ranking_svc.recalcular_ranking_fecha(quiniela.id, primera_fecha.id)
        t_rf = time.perf_counter() - t0

        n_rf = __import__("apps.scoring.infrastructure.models", fromlist=["RankingFecha"]).RankingFecha.objects.filter(
            quiniela=quiniela, fecha=primera_fecha
        ).count()

        self.stdout.write("")
        self.stdout.write(f"  Fase 2: recalcular_ranking_fecha")
        self.stdout.write(f"    Usuarios rankeados: {n_rf}")
        self.stdout.write(f"    Tiempo: {t_rf:.3f}s")

        t0 = time.perf_counter()
        ranking_svc.recalcular_ranking_acumulado(quiniela.id)
        t_ra = time.perf_counter() - t0

        from apps.scoring.infrastructure.models import RankingAcumulado
        n_ra = RankingAcumulado.objects.filter(quiniela=quiniela).count()

        self.stdout.write("")
        self.stdout.write(f"  Fase 3: recalcular_ranking_acumulado")
        self.stdout.write(f"    Usuarios rankeados: {n_ra}")
        self.stdout.write(f"    Tiempo: {t_ra:.3f}s")

        if verbose:
            self._explain_ranking_acumulado(quiniela)

        # Pipeline completo: restantes fechas
        if len(fechas) > 1:
            t_total_scoring = t_scoring_1
            t_total_rf = t_rf
            for fecha in fechas[1:]:
                t0 = time.perf_counter()
                scoring_svc.calcular_puntos_fecha(quiniela.id, fecha.id)
                t_total_scoring += time.perf_counter() - t0

                t0 = time.perf_counter()
                ranking_svc.recalcular_ranking_fecha(quiniela.id, fecha.id)
                t_total_rf += time.perf_counter() - t0

            t0 = time.perf_counter()
            ranking_svc.recalcular_ranking_acumulado(quiniela.id)
            t_total_ra = time.perf_counter() - t0
            t_total = t_total_scoring + t_total_rf + t_total_ra

            self.stdout.write("")
            self.stdout.write(f"  Pipeline completo ({len(fechas)} fechas):")
            self.stdout.write(f"    calcular_puntos (todas las fechas): {t_total_scoring:.1f}s")
            self.stdout.write(f"    recalcular_ranking_fecha (×{len(fechas)}):  {t_total_rf:.2f}s")
            self.stdout.write(f"    recalcular_ranking_acumulado:        {t_total_ra:.2f}s")
            self.stdout.write(f"    TOTAL:                              {t_total:.1f}s")

            if t_total_scoring > 10:
                self.stdout.write("")
                self.stdout.write("  ⚠ ALERTA: calcular_puntos supera 10s. Se recomienda async.")
            elif t_total_scoring > 8:
                self.stdout.write("")
                self.stdout.write("  ⚠ ADVERTENCIA: calcular_puntos supera 8s. Considerar async.")

        self.stdout.write("")
        self.stdout.write("═" * 62)

    def _explain_ranking_acumulado(self, quiniela):
        sql = """
            SELECT "usuario_id",
                   SUM("puntos") AS puntos,
                   COUNT(CASE WHEN "codigo_acierto" = 'EXACT' THEN 1 END) AS exactos_total,
                   COUNT(DISTINCT "evento_partido_id") AS eventos
            FROM   scoring_puntuacion_evento
            WHERE  "quiniela_id" = %s
            GROUP  BY "usuario_id"
            ORDER  BY puntos DESC
        """
        self.stdout.write("")
        self.stdout.write("  EXPLAIN ANALYZE — recalcular_ranking_acumulado:")
        with connection.cursor() as cursor:
            cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}", [quiniela.id])
            for row in cursor.fetchall():
                self.stdout.write(f"    {row[0]}")

    def _limpiar(self, torneo):
        if not torneo.name.startswith(PREFIJO):
            self.stderr.write(f"Torneo '{torneo.name}' no tiene prefijo {PREFIJO!r}. No se borra.")
            return

        # Borrar usuarios bench relacionados a este torneo
        ts = torneo.external_code.replace("BM", "")
        deleted_users, _ = User.objects.filter(username__startswith=f"bench_{ts}_").delete()

        deleted_torneo, breakdown = torneo.delete()
        self.stdout.write(
            f"  Limpieza: {deleted_users} usuarios y {deleted_torneo} objetos del torneo eliminados."
        )
