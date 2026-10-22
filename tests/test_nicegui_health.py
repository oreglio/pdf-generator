import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from nicegui import Client, app

import nicegui_app  # noqa: F401 — registers the routes under test

ROOT = Path(__file__).resolve().parents[1]


class HealthCheckTests(unittest.TestCase):
    """The container probe runs every 30 s, visitors or not.

    Each page built for it carries an upload route that FastAPI keeps in a
    4096-entry cache, and that route holds the whole page in memory: the
    probe alone grew folio by about 0.25 MB a page, up to 1.6 GB.
    """

    def test_health_route_answers_without_building_a_page(self):
        before = len(Client.instances)
        response = TestClient(app).get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True})
        self.assertEqual(len(Client.instances), before)

    def test_container_probe_uses_the_health_route(self):
        healthcheck = next(line for line in (ROOT / 'Dockerfile.nicegui').read_text().splitlines()
                           if line.lstrip().startswith('CMD python'))
        self.assertIn('/healthz', healthcheck)


if __name__ == '__main__':
    unittest.main()
