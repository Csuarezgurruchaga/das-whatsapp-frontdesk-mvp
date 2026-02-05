import fcntl
import importlib.util
import os
import pathlib
import pty
import subprocess
import sys
import time
import unittest


def _load_wrapper_module():
    path = pathlib.Path(__file__).resolve().parents[1] / "codex-interview-wrapper.py"
    spec = importlib.util.spec_from_file_location("codex_interview_wrapper_script", str(path))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


WRAP = _load_wrapper_module()


SAMPLE = """
Voy a seguir spec-interview (solo preguntas + spec docs después). Responde en UNA sola línea con pares separados por comas, por ejemplo: Q0=A, Q1=C, Q2=E: ...

## Ronda 1 (Q0–Q9)

Q0 — Spec slug (nombre de la carpeta)
A) voice-bot
B) voice-bot-mvp
C) voice-bot-soporte
D) voice-bot-ventas
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q1 — Objetivo principal del bot
A) Soporte al cliente (FAQ + resolver incidencias)
B) Ventas / calificación de leads
C) Reservas / agenda (citas, confirmaciones)
D) Recepción / enrutamiento (derivar a área/persona)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q2 — Canal de voz
A) Llamadas telefónicas (PSTN: número real, inbound/outbound)
B) Web (widget en navegador con micrófono)
C) App móvil (voz dentro de tu app)
D) Asíncrono (audios/voice notes; no “conversación en vivo”)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q3 — Idiomas
A) Solo español
B) Español + inglés (bilingüe)
C) Multilenguaje (varios)
D) Español pero con región/acento específico como requisito
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q4 — Requisito de latencia (sensación de “tiempo real”)
A) Muy baja (conversación natural, interrupciones posibles)
B) Media (pausas aceptables de 2–4s por turno)
C) No importa (puede tardar)
D) Depende del canal (teléfono vs web vs app)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q5 — Calidad de voz (TTS)
A) “Humana/premium” (marca/tono importa)
B) “Buena suficiente” (prioridad costo/robustez)
C) Debe clonar voz / voice persona específica
D) Debe soportar emociones/estilos (más expresiva)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q6 — Enfoque de construcción
A) Plataforma gestionada (más rápido, menos control)
B) Construcción custom (más control, más ingeniería)
C) Híbrido (empezar gestionado → migrar a custom)
D) Solo prototipo/demo primero (sin producción)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q7 — Tipo de “cerebro” conversacional
A) LLM libre + herramientas (tool-calling)
B) Flujos guiados (script/árbol) + fallback a LLM
C) 100% flujos guiados (sin LLM)
D) LLM pero con “guardrails” estrictos (respuestas limitadas)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q8 — Acciones e integraciones (MVP)
A) Solo responder y recopilar datos (sin integraciones)
B) 1 integración vía webhook (tu backend hace el resto)
C) Integración con calendario (crear/editar citas)
D) Integración con CRM/tickets (crear/actualizar)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples

Q9 — Sensibilidad de datos / compliance
A) Baja (sin datos sensibles; logs OK)
B) Media (PII: nombres, teléfonos; cuidado con retención)
C) Alta (salud/finanzas/menores; controles fuertes)
D) No se puede guardar audio/transcripciones (o casi nada)
E) Other: <texto>
F) Not sure / decide later
G) Explain options, H) Compare, I) Recommend, J) Show examples
""".strip()

SAMPLE_PAREN = """
Uso el skill spec-interview.

Ronda 1 (8 preguntas)

Q1) Caso de uso principal del voice agent (demo)
A) Soporte/FAQ (responde preguntas)
B) Agendamiento (consulta disponibilidad y agenda)
C) Toma de pedidos/lead intake (captura datos y confirma)
D) Entrevista guiada (hace preguntas y genera resumen)
E) Other: <texto>
F) Not sure / decide later
G) Explain options (A–D) / H) Compare / I) Recommend / J) Show examples

Q2) Canal de voz (elegí UNO para la demo)
A) Web (micrófono en navegador)
B) App móvil (micrófono)
C) Llamadas telefónicas (PSTN via Twilio u otro)
D) WhatsApp/Telegram voice notes
E) Other: <texto>
F) Not sure / decide later
G/H/I/J
""".strip()

SAMPLE_MARKER = """
› Q0 — Spec slug
A) voice-agent-mvp
B) voice-agent
G) Explain options, H) Compare, I) Recommend, J) Show examples

• Q1 — Idioma
A) Español
B) Inglés
G/H/I/J
""".strip()

SAMPLE_MARKER_OPTIONS = """
Q0 — Foo
› A) alpha
• B) beta
│ G) Explain options, H) Compare, I) Recommend, J) Show examples
""".strip()

SAMPLE_BULLETS = """
Necesito primero el slug del spec (kebab-case) para crear docs/specs/<slug>/.

Elige uno:

- A) voice-agent-mvp (Recommended)
- B) voice-agent
- C) voice-agent-web
- D) Otro
- E) Other: <texto>
- F) Not sure / decide later

Responde en una sola línea con este formato:
Q0=A (o Q0=E: mi-slug)
""".strip()

SAMPLE_Q_ONLY = """
• Q0 — Explicación de opciones

Texto de ayuda sin opciones formales.
""".strip()

SAMPLE_BULLET_PAREN = """
Q0 — Explicación de opciones
- A (tiempo real <100 ms): útil cuando la experiencia tiene que sentirse instantánea.
- B (latencia <300 ms): buen balance para conversaciones naturales.
""".strip()

SAMPLE_INCOMPLETE_HEADER = """
Q0 — Foo
Please resend the round answers (format reminder: Q0=A, Q1=B)
""".strip()

SAMPLE_WRAPPED_OPTION_CONTINUATION = """
Q6 — Priorización visual en el nuevo tablero
A) Mantener semáforo en tarea principal + subtareas por estado — Qué es: color de urgencia + flujo Kanban; Cuándo usar: si querés
continuidad visual entre tablero y subtareas, manteniendo el detalle operativo.
B) Quitar semáforo y usar solo estados Kanban — Qué es: un único eje de seguimiento.
""".strip()


class TestParseBatch(unittest.TestCase):
    def test_parse_batch_extracts_questions_and_inline_options(self):
        lines = [ln.rstrip() for ln in SAMPLE.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=400)
        self.assertIsNotNone(batch)
        self.assertEqual(len(batch.questions), 10)
        q0 = batch.questions[0]
        self.assertEqual(q0.qid, "Q0")
        letters = {o.letter for o in q0.options}
        self.assertIn("A", letters)
        self.assertIn("B", letters)
        self.assertIn("G", letters)
        self.assertIn("H", letters)
        self.assertIn("I", letters)
        self.assertIn("J", letters)

    def test_parse_batch_supports_qn_paren_and_slash_meta(self):
        lines = [ln.rstrip() for ln in SAMPLE_PAREN.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=200)
        self.assertIsNotNone(batch)
        self.assertEqual(len(batch.questions), 2)
        q1 = batch.questions[0]
        self.assertEqual(q1.qid, "Q1")
        letters = {o.letter for o in q1.options}
        self.assertIn("A", letters)
        self.assertIn("B", letters)
        self.assertIn("G", letters)
        self.assertIn("H", letters)
        self.assertIn("I", letters)
        self.assertIn("J", letters)
        q2 = batch.questions[1]
        letters2 = {o.letter for o in q2.options}
        self.assertIn("A", letters2)
        self.assertIn("B", letters2)
        self.assertIn("G", letters2)
        self.assertIn("H", letters2)
        self.assertIn("I", letters2)
        self.assertIn("J", letters2)

    def test_parse_batch_supports_bulleted_options_and_q_ref(self):
        lines = [ln.rstrip() for ln in SAMPLE_BULLETS.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=200)
        self.assertIsNotNone(batch)
        self.assertEqual(len(batch.questions), 1)
        q0 = batch.questions[0]
        self.assertEqual(q0.qid, "Q0")
        letters = {o.letter for o in q0.options}
        self.assertIn("A", letters)
        self.assertIn("B", letters)
        self.assertIn("E", letters)
        self.assertIn("F", letters)

    def test_parse_batch_can_disable_q_ref_fallback(self):
        lines = [ln.rstrip() for ln in SAMPLE_BULLETS.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=200, allow_qref_fallback=False)
        self.assertIsNone(batch)

    def test_parse_batch_supports_leading_ui_markers(self):
        lines = [ln.rstrip() for ln in SAMPLE_MARKER.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=200)
        self.assertIsNotNone(batch)
        self.assertEqual(len(batch.questions), 2)
        self.assertEqual(batch.questions[0].qid, "Q0")
        self.assertEqual(batch.questions[1].qid, "Q1")

    def test_parse_batch_rejects_headers_without_ab_options(self):
        lines = [ln.rstrip() for ln in SAMPLE_INCOMPLETE_HEADER.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=200)
        self.assertIsNone(batch)

    def test_parse_batch_supports_ui_markers_in_option_lines(self):
        lines = [ln.rstrip() for ln in SAMPLE_MARKER_OPTIONS.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=200)
        self.assertIsNotNone(batch)
        self.assertEqual(len(batch.questions), 1)
        q0 = batch.questions[0]
        letters = {o.letter for o in q0.options}
        self.assertIn("A", letters)
        self.assertIn("B", letters)
        self.assertIn("G", letters)

    def test_parse_batch_merges_wrapped_option_continuations(self):
        lines = [ln.rstrip() for ln in SAMPLE_WRAPPED_OPTION_CONTINUATION.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=50)
        self.assertIsNotNone(batch)
        q6 = batch.questions[0]
        opt_a = next(o for o in q6.options if o.letter == "A")
        self.assertIn("continuidad visual entre tablero y subtareas", opt_a.label)

    def test_parse_batch_rejects_qn_without_options(self):
        lines = [ln.rstrip() for ln in SAMPLE_Q_ONLY.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=50)
        self.assertIsNone(batch)

    def test_parse_batch_supports_bullet_paren_options(self):
        lines = [ln.rstrip() for ln in SAMPLE_BULLET_PAREN.splitlines()]
        batch = WRAP.parse_batch(lines, max_lookback=50)
        self.assertIsNotNone(batch)
        q0 = batch.questions[0]
        letters = {o.letter for o in q0.options}
        self.assertIn("A", letters)
        self.assertIn("B", letters)

    def test_format_answer_line(self):
        self.assertEqual(WRAP.format_answer_line(["Q0=A", "Q1=E: foo"]), "Q0=A, Q1=E: foo")

    def test_resend_prompt_regex(self):
        self.assertIsNotNone(
            WRAP.RESEND_PROMPT_RE.search(
                "Please resend the round answers (format reminder: Q0=A, Q1=B)"
            )
        )
        self.assertIsNotNone(
            WRAP.RESEND_PROMPT_RE.search("format reminder: Q12=A, Q13=B")
        )

class TestBatchCompletenessGating(unittest.TestCase):
    def test_gate_rejects_single_question_even_if_settled(self):
        lines = [
            "Q20 — Foo",
            "A) a",
            "B) b",
            "Responde en UNA sola línea con pares separados por comas, por ejemplo: Q20=A",
        ]
        ok, reason = WRAP._batch_completeness_gate(lines, quiet_for=10.0, settle_sec=0.35)
        self.assertFalse(ok)
        self.assertIn("headers", reason)

    def test_gate_accepts_two_questions_with_instruction(self):
        lines = [
            "## Ronda 3 (Q14–Q20)",
            "Q14 — Uno",
            "A) a",
            "B) b",
            "Q15 — Dos",
            "A) a",
            "B) b",
            "Responde en UNA sola línea con pares separados por comas, por ejemplo: Q14=A, Q15=B",
        ]
        ok, _reason = WRAP._batch_completeness_gate(lines, quiet_for=0.4, settle_sec=0.35)
        self.assertTrue(ok)

    def test_gate_waits_longer_when_instruction_missing(self):
        lines = [
            "Q0 — Uno",
            "A) a",
            "B) b",
            "Q1 — Dos",
            "A) a",
            "B) b",
        ]
        ok1, _reason1 = WRAP._batch_completeness_gate(lines, quiet_for=0.4, settle_sec=0.35)
        self.assertFalse(ok1)
        ok2, _reason2 = WRAP._batch_completeness_gate(lines, quiet_for=2.0, settle_sec=0.35)
        self.assertTrue(ok2)


class TestRoundBuffer(unittest.TestCase):
    def test_round_buffer_prefers_captured_round_over_truncated_recent(self):
        rb = WRAP.RoundBuffer(max_lines=200)
        stream_lines = [
            "## Ronda 1 (Q0–Q2)",
            "Q0 — Uno",
            "A) a",
            "B) b",
            "Q1 — Dos",
            "A) a",
            "B) b",
            "Q2 — Tres",
            "A) a",
            "B) b",
            "Responde en UNA sola línea con pares separados por comas, por ejemplo: Q0=A, Q1=B, Q2=C",
        ]
        for ln in stream_lines:
            rb.push_line(ln)

        # Even if the global recent buffer only retained the tail, the round buffer
        # should keep early questions once it has started capturing.
        recent = stream_lines[-3:]
        preferred = rb.preferred_lines(recent)
        self.assertGreaterEqual(len(preferred), len(recent))
        self.assertTrue(any("Q0 —" in ln for ln in preferred))


class TestReadCodexUntilResend(unittest.TestCase):
    def _spawn_delayed_output_child(self, slave_fd: int) -> subprocess.Popen:
        # Emulates a "slow" assistant: the PTY will echo user input immediately (ECHO),
        # but actual output arrives later in two chunks with a gap > default settle_sec.
        code = r"""
import sys
import time

def w(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.flush()

while True:
    line = sys.stdin.readline()
    if not line:
        break
    # Sleep longer than the wrapper's typical settle_sec to reproduce early-return.
    time.sleep(0.45)
    w("help: " + line.strip() + "\n")
    time.sleep(0.45)
    w("Please resend the round answers (format reminder: Q1=A, Q2=B)\n")
"""
        return subprocess.Popen(
            [sys.executable, "-u", "-c", code],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            start_new_session=True,
        )

    def _spawn_noisy_meta_child(self, slave_fd: int) -> subprocess.Popen:
        # Emulates a renderer that repaints status lines using CR + ANSI escapes
        # before printing the actual meta/help response and resend prompt.
        code = r"""
import sys
import time

def w(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.flush()

while True:
    line = sys.stdin.readline()
    if not line:
        break
    # status repaint noise + ANSI (cursor hide/show) + carriage-return rewrites
    w("\x1b[?25lWorking...\r")
    time.sleep(0.12)
    w("Working... 60%\r")
    time.sleep(0.12)
    w("\x1b[?25h")
    # actual help response in multiple lines
    w("helper: option I usually optimizes for speed.\n")
    time.sleep(0.2)
    w("helper: choose A if you need reliability first.\n")
    time.sleep(0.2)
    w("Please resend the round answers (format reminder: Q1=A, Q2=B)\n")
"""
        return subprocess.Popen(
            [sys.executable, "-u", "-c", code],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            start_new_session=True,
        )

    def _spawn_meta_router_child(self, slave_fd: int) -> subprocess.Popen:
        # Echoes which meta line was received, then asks to resend round answers.
        code = r"""
import sys
import time

def w(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.flush()

while True:
    line = sys.stdin.readline()
    if not line:
        break
    cmd = line.strip()
    w("meta handled: " + cmd + "\n")
    time.sleep(0.1)
    w("Please resend the round answers (format reminder: Q1=A, Q2=B)\n")
"""
        return subprocess.Popen(
            [sys.executable, "-u", "-c", code],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            start_new_session=True,
        )

    @staticmethod
    def _read_available_nonblocking(fd: int) -> bytes:
        # Best-effort: read whatever is immediately available without blocking.
        orig_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        try:
            fcntl.fcntl(fd, fcntl.F_SETFL, orig_flags | os.O_NONBLOCK)
            try:
                return os.read(fd, 4096)
            except BlockingIOError:
                return b""
        finally:
            fcntl.fcntl(fd, fcntl.F_SETFL, orig_flags)

    def test_meta_read_does_not_return_on_echo_only(self):
        master_fd, slave_fd = pty.openpty()
        proc = self._spawn_delayed_output_child(slave_fd)
        os.close(slave_fd)
        try:
            meta_line = "Q1=I"

            # Reproduce the user flow: send the same meta request twice.
            for _ in range(2):
                WRAP._send_enter(master_fd, meta_line)
                lines, _raw = WRAP._read_codex_until_resend(
                    master_fd,
                    settle_sec=0.35,
                    max_sec=3.0,
                    debug=False,
                    require_resend=False,
                    ignore_line_prefix=meta_line,
                    quiet_after_sec=1.0,
                )
                self.assertTrue(any("help:" in ln for ln in lines), lines)
                self.assertTrue(
                    any("format reminder" in ln.lower() for ln in lines),
                    lines,
                )

                # If the reader returns too early, the delayed chunks would still be pending.
                time.sleep(0.2)
                pending = self._read_available_nonblocking(master_fd)
                self.assertEqual(pending, b"")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
            try:
                os.close(master_fd)
            except Exception:
                pass

    def test_meta_read_tolerates_ansi_and_repaints(self):
        master_fd, slave_fd = pty.openpty()
        proc = self._spawn_noisy_meta_child(slave_fd)
        os.close(slave_fd)
        try:
            meta_line = "Q1=I"
            WRAP._send_enter(master_fd, meta_line)
            lines, raw = WRAP._read_codex_until_resend(
                master_fd,
                settle_sec=0.35,
                max_sec=3.0,
                debug=False,
                require_resend=False,
                ignore_line_prefix=meta_line,
                quiet_after_sec=1.0,
            )
            joined = "\n".join(lines).lower()
            self.assertIn("helper: option i", joined)
            self.assertIn("helper: choose a", joined)
            self.assertIn("format reminder", joined)
            # Ensure the prompt echo is not considered effective content.
            self.assertFalse(any(ln.strip().startswith(meta_line) for ln in lines), lines)
            # Raw output can still contain ANSI; cleaned lines above must not depend on it.
            self.assertIn("Working", raw)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
            try:
                os.close(master_fd)
            except Exception:
                pass

    def test_meta_options_g_h_i_j_roundtrip(self):
        master_fd, slave_fd = pty.openpty()
        proc = self._spawn_meta_router_child(slave_fd)
        os.close(slave_fd)
        try:
            meta_lines = [
                WRAP.build_pair("Q1", "G"),
                WRAP.build_pair("Q1", "H", "A vs C"),
                WRAP.build_pair("Q1", "I"),
                WRAP.build_pair("Q1", "J"),
            ]
            for meta_line in meta_lines:
                WRAP._send_enter(master_fd, meta_line)
                lines, _raw = WRAP._read_codex_until_resend(
                    master_fd,
                    settle_sec=0.35,
                    max_sec=3.0,
                    debug=False,
                    require_resend=False,
                    ignore_line_prefix=meta_line,
                    quiet_after_sec=1.0,
                )
                joined = "\n".join(lines)
                self.assertIn(f"meta handled: {meta_line}", joined)
                self.assertIn("format reminder", joined.lower())
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
            try:
                os.close(master_fd)
            except Exception:
                pass

class TestReopenShortcut(unittest.TestCase):
    def test_consume_reopen_shortcut_when_reopen_available(self):
        requested, remaining = WRAP._consume_reopen_shortcut(
            b"\x0fhello\r", can_reopen=True
        )
        self.assertTrue(requested)
        self.assertEqual(remaining, b"hello\r")

    def test_consume_reopen_shortcut_ignored_when_reopen_not_available(self):
        requested, remaining = WRAP._consume_reopen_shortcut(
            b"\x0fhello\r", can_reopen=False
        )
        self.assertFalse(requested)
        self.assertEqual(remaining, b"\x0fhello\r")


if __name__ == "__main__":
    unittest.main()
