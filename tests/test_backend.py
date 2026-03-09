import unittest
import json
from PySide6.QtCore import QCoreApplication

from virtscreen.qt_backend import Backend

class TestBackend(unittest.TestCase):
    def setUp(self):
        # Ensure a QCoreApplication exists for QObject signals
        self.app = QCoreApplication.instance() or QCoreApplication([])

    def test_settings_get_set_and_notify(self):
        try:
            backend = Backend(logger=lambda s: None, error_logger=lambda s: None)
        except RuntimeError as e:
            self.skipTest(f"XRandR/x11 not available in test environment: {e}")

        # parse settings JSON
        settings_str = backend.settings
        settings = json.loads(settings_str)
        # flip autostart to ensure change
        orig = settings.get('vnc', {}).get('autostart', False)
        settings['vnc']['autostart'] = not orig
        notified = []
        backend.onSettingsChanged.connect(lambda: notified.append(True))
        backend.settings = json.dumps(settings)
        self.assertTrue(notified, "onSettingsChanged should be emitted when settings are written")

    def test_screens_is_list(self):
        try:
            backend = Backend(logger=lambda s: None, error_logger=lambda s: None)
        except RuntimeError as e:
            self.skipTest(f"XRandR/x11 not available in test environment: {e}")
        screens = backend.screens
        # Should be an iterable/list exposed to QML; ensure Python type is list
        self.assertIsInstance(screens, list)

if __name__ == '__main__':
    unittest.main()
