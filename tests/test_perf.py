import unittest
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from clicue.perf import PerfLogger, purge_old_logs

class TestPerfTelemetry(unittest.TestCase):
    def test_perf_logger_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "test_session.log"
            logger = PerfLogger(enabled=True, custom_log_path=str(log_path))
            logger.record_stt("test speech", 120.5)
            logger.record_align("test speech", 5, 1.2)
            logger.record_render(2.4)
            logger.close()

            self.assertTrue(log_path.exists())
            content = log_path.read_text(encoding="utf-8")
            self.assertIn("SESSION_START", content)
            self.assertIn("STT_EMISSION", content)
            self.assertIn("ALIGN_MATCH", content)
            self.assertIn("SESSION SUMMARY", content)

if __name__ == '__main__':
    unittest.main()
