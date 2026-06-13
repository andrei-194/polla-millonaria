"""
Tests para la rama AJAX de pronosticar_evento_view.

Verifica que:
  - POST con X-Requested-With: XMLHttpRequest retorna JSON, no redirect
  - Éxito: 200 + {"ok": true, "valor": ..., "valor_display": ...}
  - Evento cerrado: 409 + {"ok": false, "error": "cerrado"}
  - Valor inválido: 422 + {"ok": false, "error": "invalido"}
  - Sin autenticación: no guarda pronóstico (redirect a login)
  - POST tradicional (sin header AJAX): sigue redirigiendo (flujo original intacto)

Ejecutar:
    docker-compose exec web python manage.py test tests.test_pronosticar_ajax
"""
import json

from django.urls import reverse

from apps.predictions.infrastructure.models import PronosticoEvento
from tests.fixtures.base_tournament import TournamentScenario


AJAX_HEADERS = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


class TestPronosticarAjax(TournamentScenario):

    def setUp(self):
        self._inscribir_todos()
        self.fecha = self._crear_fecha(numero=1)
        # Partido abierto: winner + score con plazo en el futuro
        self.partido = self._crear_partido(self.fecha, suffix="a", status="scheduled")
        self.evento_winner = self._crear_evento(self.partido, self.tipo_winner, abierto=True)
        self.evento_score  = self._crear_evento(self.partido, self.tipo_score,  abierto=True)
        # Partido separado para el evento cerrado (unique constraint: partido+quiniela+tipo)
        self.partido_b = self._crear_partido(self.fecha, suffix="b", status="finished")
        self.evento_cerrado = self._crear_evento(self.partido_b, self.tipo_winner, abierto=False)
        self.jugador = self.jugadores[0]
        self.client.force_login(self.jugador)

    def _url(self, evento_id):
        return reverse(
            "quinielas:pronosticar_evento",
            kwargs={"slug": self.quiniela.slug, "evento_id": evento_id},
        )

    # ── Éxito WINNER ──────────────────────────────────────────

    def test_ajax_winner_exito(self):
        """POST AJAX con valor válido para WINNER retorna JSON ok=True y guarda el pronóstico."""
        resp = self.client.post(
            self._url(self.evento_winner.id),
            {"valor": "H"},
            **AJAX_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["valor"], "H")
        self.assertIn("valor_display", data)
        # Verificar que el pronóstico existe en la DB
        self.assertTrue(
            PronosticoEvento.objects.filter(
                usuario=self.jugador,
                evento_partido=self.evento_winner,
                valor="H",
            ).exists()
        )

    def test_ajax_winner_actualizar(self):
        """POST AJAX puede actualizar un pronóstico existente (update_or_create)."""
        self._pronosticar(self.jugador, self.evento_winner, "H")
        resp = self.client.post(
            self._url(self.evento_winner.id),
            {"valor": "D"},
            **AJAX_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["valor"], "D")
        self.assertEqual(
            PronosticoEvento.objects.get(
                usuario=self.jugador, evento_partido=self.evento_winner
            ).valor,
            "D",
        )

    # ── Éxito SCORE ───────────────────────────────────────────

    def test_ajax_score_exito(self):
        """POST AJAX con valor '2-1' para tipo SCORE retorna JSON ok=True."""
        resp = self.client.post(
            self._url(self.evento_score.id),
            {"valor": "2-1"},
            **AJAX_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["valor"], "2-1")
        self.assertTrue(
            PronosticoEvento.objects.filter(
                usuario=self.jugador,
                evento_partido=self.evento_score,
                valor="2-1",
            ).exists()
        )

    # ── Evento cerrado ────────────────────────────────────────

    def test_ajax_evento_cerrado_retorna_409(self):
        """POST AJAX sobre evento cerrado retorna HTTP 409 con error='cerrado'."""
        resp = self.client.post(
            self._url(self.evento_cerrado.id),
            {"valor": "H"},
            **AJAX_HEADERS,
        )
        self.assertEqual(resp.status_code, 409)
        data = json.loads(resp.content)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "cerrado")
        self.assertIn("mensaje", data)

    # ── Valor inválido ────────────────────────────────────────

    def test_ajax_valor_invalido_retorna_422(self):
        """POST AJAX con valor fuera de choices retorna HTTP 422 con error='invalido'."""
        resp = self.client.post(
            self._url(self.evento_winner.id),
            {"valor": "X"},
            **AJAX_HEADERS,
        )
        self.assertEqual(resp.status_code, 422)
        data = json.loads(resp.content)
        self.assertFalse(data["ok"])
        self.assertEqual(data["error"], "invalido")

    def test_ajax_valor_vacio_retorna_422(self):
        """POST AJAX sin valor retorna HTTP 422."""
        resp = self.client.post(
            self._url(self.evento_winner.id),
            {"valor": ""},
            **AJAX_HEADERS,
        )
        self.assertEqual(resp.status_code, 422)
        data = json.loads(resp.content)
        self.assertFalse(data["ok"])

    # ── Autenticación ─────────────────────────────────────────

    def test_ajax_sin_autenticacion_no_guarda(self):
        """POST AJAX sin sesión activa no debe guardar pronóstico."""
        self.client.logout()
        resp = self.client.post(
            self._url(self.evento_winner.id),
            {"valor": "H"},
            **AJAX_HEADERS,
        )
        # Debe redirigir a login (302) o retornar 403 — nunca 200
        self.assertNotEqual(resp.status_code, 200)
        self.assertFalse(
            PronosticoEvento.objects.filter(evento_partido=self.evento_winner).exists()
        )

    # ── Flujo tradicional intacto ─────────────────────────────

    def test_no_ajax_post_winner_redirige(self):
        """POST tradicional (sin X-Requested-With) sigue redirigiendo — flujo original intacto."""
        resp = self.client.post(
            self._url(self.evento_winner.id),
            {"valor": "A"},
        )
        # Django redirige con HTTP 302
        self.assertEqual(resp.status_code, 302)
        # Verifica que el pronóstico se guardó igualmente
        self.assertTrue(
            PronosticoEvento.objects.filter(
                usuario=self.jugador,
                evento_partido=self.evento_winner,
                valor="A",
            ).exists()
        )

    def test_no_ajax_post_score_redirige(self):
        """POST tradicional para SCORE (home + away separados) sigue funcionando."""
        resp = self.client.post(
            self._url(self.evento_score.id),
            {"home": "3", "away": "0"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            PronosticoEvento.objects.filter(
                usuario=self.jugador,
                evento_partido=self.evento_score,
                valor="3-0",
            ).exists()
        )
