// PM2 Ecosystem — MEGA BUY BOT
// All services auto-start and auto-restart on crash/reboot

module.exports = {
  apps: [
    // 1. Scanner Bot — detects MEGA BUY signals on 400+ pairs
    {
      name: "mega-scanner",
      cwd: "/home/assyin/MEGA-BUY-BOT/python",
      script: "/home/assyin/MEGA-BUY-BOT/python/venv/bin/python",
      args: "mega_buy_bot.py",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 10000,    // 10s between restarts
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },

    // 2. Entry Agent — monitors Golden Box entries
    {
      name: "mega-entry-agent",
      cwd: "/home/assyin/MEGA-BUY-BOT/python",
      script: "/home/assyin/MEGA-BUY-BOT/python/venv/bin/python",
      args: "mega_buy_entry_agent_v2.py --auto",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 10000,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },

    // 3. OpenClaw — AI Trading Assistant (port 8002)
    {
      name: "mega-openclaw",
      cwd: "/home/assyin/MEGA-BUY-BOT/mega-buy-ai",
      script: "/usr/bin/python3",
      args: "-u -m openclaw.main",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 15000,    // 15s between restarts (heavier service)
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },

    // 4. Backtest API (port 9001)
    {
      name: "mega-backtest",
      cwd: "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/backtest",
      script: "/usr/bin/python3",
      args: "-u -m api.main",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 10000,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },

    // 5. Simulation API (port 8001)
    {
      name: "mega-simulation",
      cwd: "/home/assyin/MEGA-BUY-BOT/mega-buy-ai",
      script: "/usr/bin/python3",
      args: "-u -m simulation.api.server",
      autorestart: true,
      max_restarts: 50,
      restart_delay: 10000,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },

    // 6. Dashboard (port 9000) — launched by openclaw internally, not by PM2
  ],
};
