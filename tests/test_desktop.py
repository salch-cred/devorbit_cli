"""Tests for the desktop application server."""
import threading
import time
import unittest

import requests
import uvicorn

from acli.desktop.server import app, _build_engine


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _build_engine(mock=True, headless=True)
        cls.config = uvicorn.Config(app, host="127.0.0.1", port=18799, log_level="warning")
        cls.server = uvicorn.Server(cls.config)
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True

    def test_status(self):
        r = requests.get("http://127.0.0.1:18799/api/status", timeout=10)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["mock"])
        self.assertEqual(data["provider"], "nvidia")

    def test_dashboard(self):
        r = requests.get("http://127.0.0.1:18799/api/dashboard", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn("primary_model", r.json())

    def test_tools(self):
        r = requests.get("http://127.0.0.1:18799/api/tools", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertGreater(r.json()["count"], 50)

    def test_models(self):
        r = requests.get("http://127.0.0.1:18799/api/models", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.json()["chain"]), 1)

    def test_settings_get_and_set(self):
        r = requests.get("http://127.0.0.1:18799/api/settings", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn("models", r.json())

        r = requests.post("http://127.0.0.1:18799/api/settings", json={"path": "models.temperature", "value": "0.7"}, timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

    def test_files(self):
        r = requests.get("http://127.0.0.1:18799/api/files", timeout=10)
        self.assertEqual(r.status_code, 200)

    def test_html_served(self):
        r = requests.get("http://127.0.0.1:18799/", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn("DevOrbit", r.text)

    def test_chat_reset(self):
        r = requests.post("http://127.0.0.1:18799/api/chat/reset", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])


if __name__ == "__main__":
    unittest.main()
