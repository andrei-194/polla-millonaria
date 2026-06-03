"""
Capa 1 — Inscripción de jugadores

TestInscripcionService   : capa de aplicación (QuinielaService)
TestInscripcionHTTP      : flujo HTTP moderador → inscribir / dar de baja
TestAccesoFechas         : control de acceso jugador inscrito vs no inscrito

Ejecutar:
    docker-compose exec web python manage.py test tests.test_inscripcion
"""
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.quinielas.application.dtos import InscribirJugadorDTO
from apps.quinielas.application.services import QuinielaService
from apps.quinielas.domain.exceptions import JugadorNoInscritoError, JugadorYaInscritoError
from apps.quinielas.infrastructure.models import Inscripcion
from apps.predictions.infrastructure.models import PronosticoEvento

from tests.fixtures.base_tournament import TournamentScenario

User = get_user_model()


class TestInscripcionService(TournamentScenario):
    """Tests de la capa de servicio: QuinielaService.inscribir_jugador / dar_de_baja."""

    def _dto(self, jugador) -> InscribirJugadorDTO:
        return InscribirJugadorDTO(
            jugador_id=jugador.id,
            quiniela_id=self.quiniela.id,
            moderador_id=self.moderador.id,
        )

    # --- Flujo feliz -----------------------------------------------------

    def test_inscribir_jugador_nuevo_queda_activo(self):
        insc = QuinielaService().inscribir_jugador(self._dto(self.jugadores[0]))
        self.assertTrue(insc.activa)
        self.assertEqual(insc.jugador, self.jugadores[0])
        self.assertEqual(insc.quiniela, self.quiniela)

    def test_multiples_jugadores_en_la_misma_quiniela(self):
        svc = QuinielaService()
        for j in self.jugadores:
            svc.inscribir_jugador(self._dto(j))
        count = Inscripcion.objects.filter(quiniela=self.quiniela, activa=True).count()
        self.assertEqual(count, 4)

    # --- Duplicados ------------------------------------------------------

    def test_inscribir_jugador_ya_activo_levanta_error(self):
        svc = QuinielaService()
        svc.inscribir_jugador(self._dto(self.jugadores[0]))
        with self.assertRaises(JugadorYaInscritoError):
            svc.inscribir_jugador(self._dto(self.jugadores[0]))

    def test_no_crea_registro_duplicado_en_bd(self):
        svc = QuinielaService()
        svc.inscribir_jugador(self._dto(self.jugadores[0]))
        try:
            svc.inscribir_jugador(self._dto(self.jugadores[0]))
        except JugadorYaInscritoError:
            pass
        self.assertEqual(
            Inscripcion.objects.filter(
                jugador=self.jugadores[0], quiniela=self.quiniela
            ).count(),
            1,
        )

    # --- Dar de baja ------------------------------------------------------

    def test_dar_de_baja_pone_activa_false(self):
        svc = QuinielaService()
        insc = svc.inscribir_jugador(self._dto(self.jugadores[0]))
        svc.dar_de_baja(insc.id)
        insc.refresh_from_db()
        self.assertFalse(insc.activa)

    def test_dar_de_baja_inexistente_levanta_error(self):
        with self.assertRaises(JugadorNoInscritoError):
            QuinielaService().dar_de_baja(inscripcion_id=99999)

    # --- Reactivación ---------------------------------------------------

    def test_reactivar_jugador_dado_de_baja(self):
        svc = QuinielaService()
        insc = svc.inscribir_jugador(self._dto(self.jugadores[0]))
        svc.dar_de_baja(insc.id)
        insc_nueva = svc.inscribir_jugador(self._dto(self.jugadores[0]))
        self.assertTrue(insc_nueva.activa)

    def test_reactivacion_no_crea_registro_nuevo(self):
        svc = QuinielaService()
        insc = svc.inscribir_jugador(self._dto(self.jugadores[0]))
        svc.dar_de_baja(insc.id)
        svc.inscribir_jugador(self._dto(self.jugadores[0]))
        self.assertEqual(
            Inscripcion.objects.filter(
                jugador=self.jugadores[0], quiniela=self.quiniela
            ).count(),
            1,
        )

    # --- jugador_inscrito ------------------------------------------------

    def test_jugador_inscrito_activo_devuelve_true(self):
        svc = QuinielaService()
        svc.inscribir_jugador(self._dto(self.jugadores[0]))
        self.assertTrue(svc.jugador_inscrito(self.jugadores[0].id, self.quiniela.id))

    def test_jugador_no_inscrito_devuelve_false(self):
        svc = QuinielaService()
        self.assertFalse(svc.jugador_inscrito(self.jugadores[0].id, self.quiniela.id))

    def test_jugador_dado_de_baja_devuelve_false(self):
        svc = QuinielaService()
        insc = svc.inscribir_jugador(self._dto(self.jugadores[0]))
        svc.dar_de_baja(insc.id)
        self.assertFalse(svc.jugador_inscrito(self.jugadores[0].id, self.quiniela.id))


class TestInscripcionHTTP(TournamentScenario):
    """Tests HTTP: el moderador inscribe y da de baja jugadores a través de las vistas."""

    def _url_inscribir(self):
        return reverse(
            "quinielas:moderador_inscribir",
            kwargs={"slug": self.quiniela.slug},
        )

    def _url_dar_baja(self, inscripcion_id: int):
        return reverse(
            "quinielas:moderador_dar_baja",
            kwargs={"slug": self.quiniela.slug, "inscripcion_id": inscripcion_id},
        )

    # --- Moderador inscribe ----------------------------------------------

    def test_moderador_puede_inscribir_jugador(self):
        self.client.login(username="moderador1", password="test1234")
        response = self.client.post(
            self._url_inscribir(),
            data={"jugador": self.jugadores[0].id},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Inscripcion.objects.filter(
                jugador=self.jugadores[0], quiniela=self.quiniela, activa=True
            ).exists()
        )

    def test_moderador_no_puede_inscribir_jugador_duplicado_activo(self):
        Inscripcion.objects.create(jugador=self.jugadores[0], quiniela=self.quiniela, activa=True)
        self.client.login(username="moderador1", password="test1234")
        self.client.post(
            self._url_inscribir(),
            data={"jugador": self.jugadores[0].id},
        )
        # Sigue habiendo solo 1 inscripción (JugadorYaInscritoError → messages.error)
        self.assertEqual(
            Inscripcion.objects.filter(
                jugador=self.jugadores[0], quiniela=self.quiniela
            ).count(),
            1,
        )

    # --- Moderador da de baja -------------------------------------------

    def test_moderador_puede_dar_de_baja(self):
        insc = Inscripcion.objects.create(
            jugador=self.jugadores[0], quiniela=self.quiniela, activa=True
        )
        self.client.login(username="moderador1", password="test1234")
        response = self.client.post(self._url_dar_baja(insc.id))
        self.assertEqual(response.status_code, 302)
        insc.refresh_from_db()
        self.assertFalse(insc.activa)

    # --- Control de acceso al endpoint ----------------------------------

    def test_anonimo_no_puede_inscribir(self):
        response = self.client.post(
            self._url_inscribir(),
            data={"jugador": self.jugadores[0].id},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
        self.assertFalse(
            Inscripcion.objects.filter(
                jugador=self.jugadores[0], quiniela=self.quiniela
            ).exists()
        )

    def test_jugador_no_puede_usar_endpoint_de_moderador(self):
        self.client.login(username="jugador1", password="test1234")
        response = self.client.post(
            self._url_inscribir(),
            data={"jugador": self.jugadores[1].id},
        )
        # moderador_required redirige a quinielas:list
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Inscripcion.objects.filter(
                jugador=self.jugadores[1], quiniela=self.quiniela
            ).exists()
        )


class TestAccesoFechas(TournamentScenario):
    """
    Tests de control de acceso a las vistas de jugador.

    Verifica que:
    - Anónimos son redirigidos al login
    - Jugadores no inscritos reciben 404
    - Jugadores inscritos pueden pronosticar en eventos abiertos
    - Jugadores inscritos no pueden pronosticar en eventos cerrados
    """

    def setUp(self):
        self.fecha = self._crear_fecha(numero=1)

    def _url_fechas(self):
        return reverse("quinielas:fechas_list", kwargs={"slug": self.quiniela.slug})

    # --- Acceso a /fechas/ -----------------------------------------------

    def test_anonimo_redirige_a_login(self):
        response = self.client.get(self._url_fechas())
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_jugador_no_inscrito_ve_404_en_fechas(self):
        self.client.login(username="jugador1", password="test1234")
        response = self.client.get(self._url_fechas())
        self.assertEqual(response.status_code, 404)

    def test_jugador_inscrito_ve_lista_de_fechas(self):
        self._inscribir(self.jugadores[0])
        self.client.login(username="jugador1", password="test1234")
        response = self.client.get(self._url_fechas())
        self.assertEqual(response.status_code, 200)

    # --- Pronosticar evento abierto -------------------------------------

    def test_jugador_inscrito_puede_pronosticar_score_abierto(self):
        self._inscribir(self.jugadores[0])
        partido = self._crear_partido(self.fecha)
        evento = self._crear_evento(partido, self.tipo_score, abierto=True)
        self.client.login(username="jugador1", password="test1234")
        url = reverse(
            "quinielas:pronosticar_evento",
            kwargs={"slug": self.quiniela.slug, "evento_id": evento.id},
        )
        response = self.client.post(url, data={"home": "2", "away": "1"})
        # Redirige tras guardar exitosamente
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            PronosticoEvento.objects.filter(
                usuario=self.jugadores[0], evento_partido=evento, valor="2-1"
            ).exists()
        )

    def test_jugador_puede_actualizar_pronostico_abierto(self):
        self._inscribir(self.jugadores[0])
        partido = self._crear_partido(self.fecha)
        evento = self._crear_evento(partido, self.tipo_score, abierto=True)
        self.client.login(username="jugador1", password="test1234")
        url = reverse(
            "quinielas:pronosticar_evento",
            kwargs={"slug": self.quiniela.slug, "evento_id": evento.id},
        )
        self.client.post(url, data={"home": "1", "away": "0"})
        self.client.post(url, data={"home": "2", "away": "1"})
        # Solo existe 1 pronóstico con el último valor
        pronosticos = PronosticoEvento.objects.filter(
            usuario=self.jugadores[0], evento_partido=evento
        )
        self.assertEqual(pronosticos.count(), 1)
        self.assertEqual(pronosticos.first().valor, "2-1")

    # --- Pronosticar evento cerrado (plazo vencido) ----------------------

    def test_jugador_inscrito_no_puede_pronosticar_evento_cerrado(self):
        self._inscribir(self.jugadores[0])
        partido = self._crear_partido(self.fecha)
        evento = self._crear_evento(partido, self.tipo_score, abierto=False)
        self.client.login(username="jugador1", password="test1234")
        url = reverse(
            "quinielas:pronosticar_evento",
            kwargs={"slug": self.quiniela.slug, "evento_id": evento.id},
        )
        # POST con evento cerrado: la vista re-renderiza el formulario con error (200)
        response = self.client.post(url, data={"home": "2", "away": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            PronosticoEvento.objects.filter(
                usuario=self.jugadores[0], evento_partido=evento
            ).exists()
        )

    def test_jugador_no_inscrito_no_puede_pronosticar(self):
        partido = self._crear_partido(self.fecha)
        evento = self._crear_evento(partido, self.tipo_score, abierto=True)
        self.client.login(username="jugador1", password="test1234")
        url = reverse(
            "quinielas:pronosticar_evento",
            kwargs={"slug": self.quiniela.slug, "evento_id": evento.id},
        )
        response = self.client.post(url, data={"home": "2", "away": "1"})
        self.assertEqual(response.status_code, 404)
