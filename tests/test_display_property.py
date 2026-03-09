import unittest
from PySide6.QtCore import QCoreApplication
from virtscreen.display import Display, DisplayProperty

class TestDisplayProperty(unittest.TestCase):
    def setUp(self):
        # Ensure a QCoreApplication exists for signals
        self.app = QCoreApplication.instance() or QCoreApplication([])

    def test_name_signal_and_property(self):
        d = Display()
        dp = DisplayProperty(d)
        emitted = []
        dp.nameChanged.connect(lambda: emitted.append(True))
        dp.name = "Screen-1"
        self.assertEqual(dp.name, "Screen-1")
        self.assertTrue(emitted)

    def test_connected_signal_and_property(self):
        d = Display()
        dp = DisplayProperty(d)
        emitted = []
        dp.connectedChanged.connect(lambda: emitted.append(True))
        dp.connected = True
        self.assertTrue(dp.connected)
        self.assertTrue(emitted)

if __name__ == '__main__':
    unittest.main()
