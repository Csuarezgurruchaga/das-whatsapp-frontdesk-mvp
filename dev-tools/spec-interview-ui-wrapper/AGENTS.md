## Local Development Log

- date: 2026-02-05
- context: `dev-tools/spec-interview-ui-wrapper/scripts/codex-interview-wrapper.py` parser de rondas (Qn/opciones)
- problem: El UI batch mostraba texto basura incrustado en títulos/opciones (ej. `Drafting initial interview questions`, `for shortcuts99% context left`, y fragmentos cortos como `onnss`) por líneas de estado de Codex mezcladas con contenido parseado.
- solution: Se endureció `_strip_inline_chrome` para cortar nuevas variantes de chrome/status y se ajustó `_is_option_continuation_line` para ignorar fragmentos cortos de un solo token que no son continuidad real de opciones.
- notes: Se agregó repro automatizado para la variante observada y se mantuvieron verdes los tests existentes del wrapper.
- proof: `python3 -m unittest -v dev-tools/spec-interview-ui-wrapper/scripts/tests/test_codex_interview_wrapper.py`
