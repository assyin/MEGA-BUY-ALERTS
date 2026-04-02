"""Watchdog — monitors all services and auto-restarts if down.

Checks every 60 seconds:
- Dashboard (port 9000)
- Backtest API (port 9001)
- Simulation API (port 8001)
- Scanner Bot (mega_buy_bot.py)
- Entry Agent (mega_buy_entry_agent_v2.py)

Auto-restarts downed services using subprocess.
"""

import asyncio
import subprocess
import os
import signal
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # MEGA-BUY-BOT
MEGA_BUY_AI = PROJECT_ROOT / "mega-buy-ai"
PYTHON_DIR = PROJECT_ROOT / "python"

# Service definitions
SERVICES = {
    "dashboard": {
        "name": "Dashboard",
        "port": 9000,
        "health_url": None,  # Just check port
        "start_cmd": f"cd {MEGA_BUY_AI / 'dashboard'} && npx next dev --port 9000",
        "log": "/tmp/dashboard.log",
    },
    "backtest_api": {
        "name": "Backtest API",
        "port": 9001,
        "health_url": "http://localhost:9001/api/stats",
        "start_cmd": f"cd {MEGA_BUY_AI / 'backtest'} && python -m uvicorn api.main:app --host 0.0.0.0 --port 9001",
        "log": "/tmp/backtest-api.log",
    },
    "simulation": {
        "name": "Simulation API",
        "port": 8001,
        "health_url": "http://localhost:8001/api/overview",
        "start_cmd": f"cd {MEGA_BUY_AI} && python -m simulation.api.server",
        "log": "/tmp/simulation-api.log",
    },
}

BOT_PROCESSES = {
    "scanner_bot": {
        "name": "Scanner Bot",
        "grep_pattern": "mega_buy_bot.py",
        "start_cmd": f"cd {PYTHON_DIR} && PYTHONUNBUFFERED=1 python -u mega_buy_bot.py",
        "log": "/tmp/scanner-bot.log",
    },
    "entry_agent": {
        "name": "Entry Agent",
        "grep_pattern": "mega_buy_entry_agent",
        "start_cmd": f"cd {PYTHON_DIR} && python mega_buy_entry_agent_v2.py --auto",
        "log": "/tmp/entry-agent.log",
    },
}


class Watchdog:
    """Monitors and auto-restarts services."""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self._running = False
        self._task = None
        self._restart_counts: Dict[str, int] = {}
        self._last_events: List[Dict] = []

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        print(f"🐕 Watchdog started (check every {self.check_interval}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _watch_loop(self):
        while self._running:
            try:
                await self._check_all()
            except Exception as e:
                print(f"⚠️ Watchdog error: {e}")
            await asyncio.sleep(self.check_interval)

    async def _check_all(self):
        """Check all services and bots."""
        # Check port-based services
        for svc_id, svc in SERVICES.items():
            alive = await asyncio.to_thread(self._check_port, svc["port"], svc.get("health_url"))
            if alive:
                # Reset counter if back online
                if self._restart_counts.get(svc_id, 0) > 0:
                    print(f"🐕 {svc['name']} is back online ✅")
                    self._restart_counts[svc_id] = 0
            else:
                print(f"🐕 {svc['name']} (:{svc['port']}) is DOWN — restarting...")
                await asyncio.to_thread(self._restart_service, svc_id, svc)

        # Check process-based bots
        for bot_id, bot in BOT_PROCESSES.items():
            alive = await asyncio.to_thread(self._check_process, bot["grep_pattern"])
            if alive:
                if self._restart_counts.get(bot_id, 0) > 0:
                    print(f"🐕 {bot['name']} is back online ✅")
                    self._restart_counts[bot_id] = 0
            else:
                print(f"🐕 {bot['name']} is DOWN — restarting...")
                await asyncio.to_thread(self._restart_bot, bot_id, bot)

    def _check_port(self, port: int, health_url: str = None) -> bool:
        """Check if a service is responding on a port."""
        if health_url:
            try:
                r = requests.get(health_url, timeout=5)
                return r.status_code == 200
            except Exception:
                return False
        else:
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                return result == 0
            except Exception:
                return False

    def _check_process(self, grep_pattern: str) -> bool:
        """Check if a process is running."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", grep_pattern],
                capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _restart_service(self, svc_id: str, svc: dict):
        """Restart a port-based service."""
        self._restart_counts[svc_id] = self._restart_counts.get(svc_id, 0) + 1
        count = self._restart_counts[svc_id]

        if count > 10:
            print(f"  🚨 {svc['name']} failed {count} times — giving up")
            return

        # Reset counter if service was alive for a while (previous restart worked)
        if count > 1:
            # Still failing, keep counting
            pass

        try:
            log = svc.get("log", "/dev/null")
            cmd = f"bash -c '{svc['start_cmd']} > {log} 2>&1 &'"
            subprocess.Popen(
                ["bash", "-c", f"{svc['start_cmd']} > {log} 2>&1"],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._log_event(svc_id, svc["name"], "restarted", count)
            print(f"  ✅ {svc['name']} restart #{count}")
        except Exception as e:
            print(f"  ❌ {svc['name']} restart failed: {e}")

    def _restart_bot(self, bot_id: str, bot: dict):
        """Restart a bot process."""
        self._restart_counts[bot_id] = self._restart_counts.get(bot_id, 0) + 1
        count = self._restart_counts[bot_id]

        if count > 10:
            print(f"  🚨 {bot['name']} failed {count} times — giving up")
            return

        try:
            log = bot.get("log", "/dev/null")
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            subprocess.Popen(
                ["bash", "-c", f"{bot['start_cmd']} > {log} 2>&1"],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
            self._log_event(bot_id, bot["name"], "restarted", count)
            print(f"  ✅ {bot['name']} restart #{count}")
        except Exception as e:
            print(f"  ❌ {bot['name']} restart failed: {e}")

    def _log_event(self, svc_id: str, name: str, action: str, count: int):
        """Log a watchdog event."""
        self._last_events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": name,
            "action": action,
            "restart_count": count,
        })
        # Keep last 50 events
        if len(self._last_events) > 50:
            self._last_events = self._last_events[-50:]

    def get_status(self) -> dict:
        """Get watchdog status."""
        # Quick check all services
        statuses = {}
        for svc_id, svc in SERVICES.items():
            statuses[svc_id] = {
                "name": svc["name"],
                "port": svc["port"],
                "alive": self._check_port(svc["port"], svc.get("health_url")),
                "restarts": self._restart_counts.get(svc_id, 0),
            }
        for bot_id, bot in BOT_PROCESSES.items():
            statuses[bot_id] = {
                "name": bot["name"],
                "alive": self._check_process(bot["grep_pattern"]),
                "restarts": self._restart_counts.get(bot_id, 0),
            }

        return {
            "watchdog_active": self._running,
            "check_interval": self.check_interval,
            "services": statuses,
            "recent_events": self._last_events[-10:],
        }
