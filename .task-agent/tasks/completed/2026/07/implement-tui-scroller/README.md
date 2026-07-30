---
created_at: 2026-07-29T19:06:27.643303-07:00
---

# Implement TUI Scroller

Build a terminal UI (e.g. using rich) that displays exactly 20 words from the script and visually updates based on the current word index.

## Completion Criteria

The TUI dynamically renders the rolling window of text and smoothly updates when the index advances.

## Solution

Added rich dependency. Implemented TUIScroller in src/clicue/scroller.py which renders a 20-word rolling window with the current word highlighted. Added unit tests in tests/test_scroller.py.

---
**Completed in commit:** `d1e3f3d`
