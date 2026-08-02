import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from clicue.scroller import TUIScroller


class TestTUIScroller(unittest.TestCase):
    def setUp(self):
        self.words = [f"word{i}" for i in range(50)]
        self.scroller = TUIScroller(self.words, window_size=20, past_size=5)

    def test_render_initial(self):
        group_obj = self.scroller.render(0)
        self.assertIsNotNone(group_obj)

    def test_render_middle(self):
        group_obj = self.scroller.render(15)
        self.assertIsNotNone(group_obj)


if __name__ == '__main__':
    unittest.main()
