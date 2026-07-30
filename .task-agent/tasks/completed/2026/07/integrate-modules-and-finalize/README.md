---
created_at: 2026-07-29T19:06:27.717576-07:00
blocked_by: setup-cli-input-handling, implement-fuzzy-text-alignment-engine, implement-stt-listener-with-vosk, implement-tui-scroller
---

# Integrate Modules and Finalize

Combine the CLI, STT, fuzzy matching, and TUI into a cohesive running application.

## Completion Criteria

The user can run `clicue script.txt`, read the text aloud, and watch the window shift perfectly.

## Solution

Integrated Aligner, STTListener, and TUIScroller in src/clicue/main.py. Mocked STTListener in test_main.py to prevent blocking the test suite.

---
**Completed in commit:** `371f62f`
