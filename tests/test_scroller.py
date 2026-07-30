import unittest
import sys
import os
from rich.panel import Panel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from clicue.scroller import TUIScroller

class TestTUIScroller(unittest.TestCase):
    def setUp(self):
        self.words = [f"word{i}" for i in range(50)]
        self.scroller = TUIScroller(self.words, window_size=20)

    def test_render_panel_initial(self):
        panel = self.scroller.render_panel(0)
        self.assertIsInstance(panel, Panel)
        # It should render the first 20 words
        rendered_text = panel.renderable.plain
        self.assertIn("word0", rendered_text)
        self.assertIn("word19", rendered_text)
        self.assertNotIn("word20", rendered_text)

    def test_render_panel_middle(self):
        panel = self.scroller.render_panel(15)
        rendered_text = panel.renderable.plain
        self.assertIn("word15", rendered_text)
        self.assertIn("word34", rendered_text)
        self.assertNotIn("word14", rendered_text)
        self.assertNotIn("word35", rendered_text)

    def test_render_panel_end(self):
        panel = self.scroller.render_panel(40)
        rendered_text = panel.renderable.plain
        # Only 10 words remain
        self.assertIn("word40", rendered_text)
        self.assertIn("word49", rendered_text)
        
        # Word counts
        word_count = len(rendered_text.split())
        self.assertEqual(word_count, 10)

if __name__ == '__main__':
    unittest.main()
