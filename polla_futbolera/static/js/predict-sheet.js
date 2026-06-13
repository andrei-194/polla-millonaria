/* predict-sheet.js — Bottom Sheet de pronósticos
 * Vanilla JS · Progressive enhancement · Sin dependencias
 * Si JS está desactivado, los <a href> funcionan normalmente.
 */
(function () {
  'use strict';

  var overlay     = document.getElementById('predict-overlay');
  var sheet       = document.getElementById('predict-sheet');
  var form        = document.getElementById('predict-sheet-form');
  var body        = document.getElementById('predict-sheet-body');
  var matchEl     = document.getElementById('predict-sheet-match');
  var questionEl  = document.getElementById('predict-sheet-question');
  var submitBtn   = document.getElementById('predict-sheet-submit');
  var submitLabel = document.getElementById('predict-sheet-submit-label');
  var closeBtn    = document.getElementById('predict-sheet-close');
  var csrfInput   = document.getElementById('csrf-token-value');

  // Guardián: si el drawer no existe en el DOM, salir silenciosamente (otras páginas)
  if (!overlay || !sheet || !form) return;

  var currentEventoId = null;
  var currentUrl      = null;
  var currentTipo     = null;

  // ── Helpers de renderizado ────────────────────────────────

  function esc(str) {
    // Escapar HTML para evitar XSS al insertar strings del servidor en innerHTML
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function teamCrest(logo, name, size) {
    size = size || 'sm';
    if (logo) {
      return '<img src="' + esc(logo) + '" alt="' + esc(name) + '" class="team-crest team-crest--' + size + '">';
    }
    return '<div class="team-crest team-crest--' + size + ' team-crest--fallback">' + esc(name.slice(0, 3).toUpperCase()) + '</div>';
  }

  function renderMatchMini(home, away, homeLogo, awayLogo) {
    return teamCrest(homeLogo, home)
      + '<span style="font-size:var(--text-xs);color:var(--text-secondary);">' + esc(home) + '</span>'
      + '<span style="color:var(--text-muted);font-size:var(--text-xs);padding:0 2px;">vs</span>'
      + '<span style="font-size:var(--text-xs);color:var(--text-secondary);">' + esc(away) + '</span>'
      + teamCrest(awayLogo, away);
  }

  function choiceIcon(tipo, choice, home, away, homeLogo, awayLogo) {
    if (tipo === 'WINNER') {
      if (choice === 'H') return teamCrest(homeLogo, home);
      if (choice === 'A') return teamCrest(awayLogo, away);
      if (choice === 'D') return '<i class="bi bi-dash-circle" style="font-size:26px;color:var(--text-secondary);"></i>';
    }
    var icons = {
      yes:   'bi-check2-circle',
      no:    'bi-x-circle',
      over:  'bi-graph-up-arrow',
      under: 'bi-graph-down-arrow',
    };
    var colors = {
      'bi-check2-circle': 'var(--green)',
      'bi-x-circle':      'var(--danger)',
      'bi-graph-up-arrow':'var(--green)',
      'bi-graph-down-arrow':'var(--danger)',
    };
    var ic = icons[choice] || 'bi-circle';
    return '<i class="bi ' + ic + '" style="font-size:24px;color:' + (colors[ic] || 'var(--text-muted)') + ';"></i>';
  }

  function choiceLabel(tipo, choice, home, away) {
    if (tipo === 'WINNER') {
      if (choice === 'H') return esc(home) + ' gana';
      if (choice === 'D') return 'Empate';
      if (choice === 'A') return esc(away) + ' gana';
    }
    var labels = {
      yes:   'Sí, ambos anotan',
      no:    'No, alguno se queda en 0',
      over:  'Más de 2.5 goles',
      under: 'Menos de 2.5 goles',
    };
    return labels[choice] || esc(choice);
  }

  function renderChoicesForm(tipo, choices, prono, home, away, homeLogo, awayLogo) {
    var html = '<div class="predict-choices">';
    choices.forEach(function (choice) {
      var selected = choice === prono;
      html += '<label class="predict-choice' + (selected ? ' predict-choice--selected' : '') + '" data-value="' + esc(choice) + '">'
        + '<input type="radio" name="valor" value="' + esc(choice) + '"' + (selected ? ' checked' : '') + ' required style="display:none;">'
        + '<span class="predict-choice__icon">' + choiceIcon(tipo, choice, home, away, homeLogo, awayLogo) + '</span>'
        + '<span class="predict-choice__label">' + choiceLabel(tipo, choice, home, away) + '</span>'
        + '<span class="predict-choice__check"><i class="bi bi-check-circle-fill"></i></span>'
        + '</label>';
    });
    html += '</div>';
    return html;
  }

  function renderScoreForm(prono, home, away, homeLogo, awayLogo) {
    var homeVal = '', awayVal = '';
    if (prono && prono.indexOf('-') !== -1) {
      var parts = prono.split('-');
      homeVal = parts[0] || '';
      awayVal = parts[1] || '';
    }
    return '<div class="predict-score-row">'
      + teamCrest(homeLogo, home)
      + '<input type="number" name="sheet_home" id="sheet-score-home" min="0" max="20" inputmode="numeric" class="predict-score-input" value="' + esc(homeVal) + '" required>'
      + '<span class="predict-score-sep">—</span>'
      + '<input type="number" name="sheet_away" id="sheet-score-away" min="0" max="20" inputmode="numeric" class="predict-score-input" value="' + esc(awayVal) + '" required>'
      + teamCrest(awayLogo, away)
      + '</div>';
  }

  // ── Abrir drawer ──────────────────────────────────────────

  function openSheet(btn) {
    var tipo      = btn.dataset.tipo      || '';
    var choices   = btn.dataset.choices   ? btn.dataset.choices.split(',') : [];
    var prono     = btn.dataset.prono     || '';
    var home      = btn.dataset.home      || '';
    var away      = btn.dataset.away      || '';
    var homeLogo  = btn.dataset.homeLogo  || '';
    var awayLogo  = btn.dataset.awayLogo  || '';
    var descripcion = btn.dataset.descripcion || btn.dataset.tipoNombre || '';

    currentEventoId = btn.dataset.eventoId;
    currentUrl      = btn.href;
    currentTipo     = tipo;

    // Limpiar feedback anterior
    clearSheetMessages();

    matchEl.innerHTML   = renderMatchMini(home, away, homeLogo, awayLogo);
    questionEl.textContent = descripcion;

    if (tipo === 'SCORE') {
      body.innerHTML = renderScoreForm(prono, home, away, homeLogo, awayLogo);
      submitBtn.disabled = false;
      // Foco en el primer input numérico tras la animación
      requestAnimationFrame(function () {
        var first = body.querySelector('input[type=number]');
        if (first) first.focus();
      });
    } else {
      body.innerHTML = renderChoicesForm(tipo, choices, prono, home, away, homeLogo, awayLogo);
      // Deshabilitar submit si no hay selección previa
      submitBtn.disabled = !prono;
      // Re-activar choices
      body.querySelectorAll('.predict-choice').forEach(function (card) {
        card.addEventListener('click', function () {
          body.querySelectorAll('.predict-choice').forEach(function (c) {
            c.classList.remove('predict-choice--selected');
          });
          this.classList.add('predict-choice--selected');
          this.querySelector('input[type=radio]').checked = true;
          submitBtn.disabled = false;
        });
      });
    }

    submitLabel.textContent = prono ? 'Actualizar jugada' : 'Guardar jugada';

    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    // Foco al botón de cierre para accesibilidad
    requestAnimationFrame(function () { closeBtn.focus(); });
  }

  // ── Cerrar drawer ─────────────────────────────────────────

  function closeSheet() {
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    sheet.classList.remove('predict-sheet--loading');
    submitBtn.disabled = false;
    currentEventoId = null;
    currentUrl      = null;
    currentTipo     = null;
  }

  // ── Feedback inline ───────────────────────────────────────

  function clearSheetMessages() {
    var existing = sheet.querySelectorAll('.predict-sheet__toast, .predict-sheet__error');
    existing.forEach(function (el) { el.remove(); });
  }

  function showSheetToast(msg) {
    clearSheetMessages();
    var el = document.createElement('div');
    el.className = 'predict-sheet__toast';
    el.innerHTML = '<i class="bi bi-check-circle-fill"></i> ' + esc(msg);
    form.insertBefore(el, form.firstChild);
  }

  function showSheetError(msg) {
    clearSheetMessages();
    var el = document.createElement('div');
    el.className = 'predict-sheet__error';
    el.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> ' + esc(msg);
    form.insertBefore(el, form.firstChild);
  }

  // ── Actualizar ev-row tras éxito ──────────────────────────

  function updateEvRow(eventoId, valor, valorDisplay) {
    var row = document.getElementById('ev-row-' + eventoId);
    if (!row) return;

    row.classList.remove('ev-row--abierto');
    row.classList.add('ev-row--editando');

    // Actualizar el pick display
    var pickEl = document.getElementById('ev-pick-' + eventoId);
    if (!pickEl) {
      // El ev-row era --abierto: el span de deadline existe, reemplazarlo
      var deadlineEl = row.querySelector('.ev-row__deadline');
      pickEl = document.createElement('span');
      pickEl.className = 'ev-row__my-pick';
      pickEl.id = 'ev-pick-' + eventoId;
      if (deadlineEl) {
        deadlineEl.replaceWith(pickEl);
      } else {
        var leftEl = row.querySelector('.ev-row__left');
        if (leftEl) leftEl.appendChild(pickEl);
      }
    }
    // Usar textContent para el valor del usuario (XSS safe), icono es literal HTML fijo
    pickEl.innerHTML = '<i class="bi bi-pencil-fill" style="font-size:9px;"></i> ';
    pickEl.appendChild(document.createTextNode(valorDisplay));

    // Cambiar el botón de "Jugar" (btn-primary) a "Editar" (btn-ghost)
    var btn = row.querySelector('.js-predict-btn');
    if (btn) {
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-ghost');
      btn.dataset.prono = valor;
      btn.innerHTML = '<i class="bi bi-pencil"></i> Editar';
    }
  }

  // ── Envío AJAX ────────────────────────────────────────────

  function submitPrediction(valor) {
    var csrf = csrfInput ? csrfInput.value : '';
    var url  = currentUrl;
    var evId = currentEventoId;

    sheet.classList.add('predict-sheet--loading');
    submitBtn.disabled = true;

    fetch(url, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrf,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: 'valor=' + encodeURIComponent(valor),
    })
    .then(function (res) {
      return res.json().then(function (data) {
        data._httpStatus = res.status;
        return data;
      });
    })
    .then(function (data) {
      sheet.classList.remove('predict-sheet--loading');

      if (data.ok) {
        showSheetToast('¡Jugada guardada!');
        updateEvRow(evId, data.valor, data.valor_display);
        setTimeout(closeSheet, 700);

      } else if (data.error === 'cerrado') {
        // El evento se cerró mientras el drawer estaba abierto
        var row = document.getElementById('ev-row-' + evId);
        if (row) {
          row.classList.remove('ev-row--abierto', 'ev-row--editando');
          row.classList.add('ev-row--cerrado');
          var btn = row.querySelector('.js-predict-btn');
          if (btn) {
            var badge = document.createElement('span');
            badge.className = 'ev-row__closed-badge';
            badge.textContent = 'Cerrado';
            btn.replaceWith(badge);
          }
        }
        showSheetError(data.mensaje || 'El plazo de pronóstico cerró.');
        setTimeout(closeSheet, 2500);

      } else {
        // Error de validación: mostrar mensaje y re-habilitar submit
        showSheetError(data.mensaje || 'Ocurrió un error. Intenta de nuevo.');
        submitBtn.disabled = false;
      }
    })
    .catch(function () {
      // Sin conexión: fallback al submit tradicional
      sheet.classList.remove('predict-sheet--loading');
      showSheetError('Sin conexión. Guardando de forma clásica…');
      setTimeout(function () {
        form.removeAttribute('novalidate');
        form.submit();
      }, 900);
    });
  }

  // ── Handler submit ────────────────────────────────────────

  form.addEventListener('submit', function (e) {
    e.preventDefault();

    var valor;
    if (currentTipo === 'SCORE') {
      var homeInput = form.querySelector('input[name="sheet_home"]');
      var awayInput = form.querySelector('input[name="sheet_away"]');
      if (!homeInput || !awayInput || homeInput.value === '' || awayInput.value === '') {
        showSheetError('Ingresa el marcador completo.');
        return;
      }
      var h = parseInt(homeInput.value, 10);
      var a = parseInt(awayInput.value, 10);
      if (isNaN(h) || isNaN(a) || h < 0 || a < 0 || h > 20 || a > 20) {
        showSheetError('El marcador debe ser entre 0 y 20.');
        return;
      }
      valor = h + '-' + a;
    } else {
      var radio = form.querySelector('input[name="valor"]:checked');
      if (!radio) {
        showSheetError('Selecciona una opción.');
        return;
      }
      valor = radio.value;
    }

    submitPrediction(valor);
  });

  // ── Listeners de apertura ─────────────────────────────────

  document.querySelectorAll('.js-predict-btn').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      openSheet(this);
    });
  });

  // ── Listeners de cierre ───────────────────────────────────

  closeBtn.addEventListener('click', closeSheet);

  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeSheet();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && overlay.classList.contains('is-open')) {
      closeSheet();
    }
  });

  // Swipe-to-close en touch
  var touchStartY = 0;
  sheet.addEventListener('touchstart', function (e) {
    touchStartY = e.touches[0].clientY;
  }, { passive: true });
  sheet.addEventListener('touchend', function (e) {
    if (e.changedTouches[0].clientY - touchStartY > 80) closeSheet();
  }, { passive: true });

}());
