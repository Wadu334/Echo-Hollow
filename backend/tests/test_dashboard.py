from __future__ import annotations

import asyncio
import unittest

from fastapi.responses import HTMLResponse

from backend.app.main import index


class DashboardRouteTests(unittest.TestCase):
    def test_index_returns_live_dashboard_html(self) -> None:
        response = asyncio.run(index())

        self.assertIsInstance(response, HTMLResponse)
        body = response.body.decode("utf-8")
        self.assertIn("Echo Hollow World Server", body)
        self.assertIn("/ws/world/demo_world_001", body)
        self.assertIn("move_player", body)
        self.assertIn("Agent Tools", body)
        self.assertIn("share_claim", body)
        self.assertIn("Agent Trace", body)
        self.assertIn("world json", body)


if __name__ == "__main__":
    unittest.main()
