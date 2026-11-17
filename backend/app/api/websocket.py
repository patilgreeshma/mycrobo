"""
CodeSentinel - WebSocket Progress Manager
Real-time scan progress updates to connected clients.
"""

import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ProgressManager:
    """
    Manages WebSocket connections for real-time scan progress updates.
    Clients connect to /ws/scan/{scan_id} to receive live updates.
    """

    def __init__(self):
        # scan_id -> set of connected WebSocket clients
        self._connections: Dict[str, Set[WebSocket]] = {}
        # scan_id -> latest progress data
        self._latest: Dict[str, dict] = {}

    async def connect(self, scan_id: str, websocket: WebSocket):
        """Accept a WebSocket connection and register it for updates."""
        await websocket.accept()
        if scan_id not in self._connections:
            self._connections[scan_id] = set()
        self._connections[scan_id].add(websocket)
        logger.info(f"WebSocket connected for scan {scan_id}")

        # Send latest progress if available
        if scan_id in self._latest:
            try:
                await websocket.send_json(self._latest[scan_id])
            except Exception:
                pass

    async def disconnect(self, scan_id: str, websocket: WebSocket):
        """Remove a disconnected WebSocket client."""
        if scan_id in self._connections:
            self._connections[scan_id].discard(websocket)
            if not self._connections[scan_id]:
                del self._connections[scan_id]
        logger.info(f"WebSocket disconnected for scan {scan_id}")

    async def send_progress(self, scan_id: str, data: dict):
        """
        Broadcast a progress update to all connected clients for a scan.

        Args:
            scan_id: The scan to update
            data: Progress data dict with keys: status, progress, current_step, issues_found
        """
        self._latest[scan_id] = data

        if scan_id not in self._connections:
            return

        dead_connections = set()
        for ws in self._connections[scan_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead_connections.add(ws)

        # Clean up dead connections
        for ws in dead_connections:
            self._connections[scan_id].discard(ws)

    def get_latest(self, scan_id: str) -> dict:
        """Get the latest progress for a scan (for polling fallback)."""
        return self._latest.get(scan_id, {
            "status": "unknown",
            "progress": 0,
            "current_step": "Waiting...",
            "issues_found": 0,
        })

    def cleanup(self, scan_id: str):
        """Remove all data for a completed scan."""
        self._connections.pop(scan_id, None)
        # Keep latest for a while for polling clients
        # self._latest.pop(scan_id, None)


# Global singleton
progress_manager = ProgressManager()
