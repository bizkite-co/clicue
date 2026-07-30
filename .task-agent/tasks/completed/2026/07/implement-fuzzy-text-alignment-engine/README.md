---
created_at: 2026-07-29T19:06:27.594262-07:00
---

# Implement Fuzzy Text Alignment Engine

Create an alignment engine using rapidfuzz that takes the script words and incoming STT strings, and accurately updates the current reading position.

## Completion Criteria

Given a stream of slightly imperfect STT text, the engine correctly advances the word index in the original script.

## Solution

Implemented Aligner class in src/clicue/aligner.py using rapidfuzz, and added unit tests in tests/test_aligner.py.

---
**Completed in commit:** `8a57b4e`
