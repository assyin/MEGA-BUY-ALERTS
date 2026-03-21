#!/usr/bin/env python3
"""
Command Line Interface for the Simulation System.

Usage:
    python -m simulation.cli start      # Start simulation
    python -m simulation.cli stop       # Stop simulation
    python -m simulation.cli status     # Get status
    python -m simulation.cli reset      # Reset simulation
    python -m simulation.cli server     # Start API server
"""

import asyncio
import argparse
import sys
import json

from .main import SimulationOrchestrator, run_simulation
from .config.settings import get_settings, load_config
from .data.database import Database
from .utils.logger import init_logging, get_logger


def cmd_start(args):
    """Start the simulation."""
    print("Starting simulation...")
    asyncio.run(run_simulation())


def cmd_status(args):
    """Get simulation status."""
    settings = get_settings()
    db = Database(settings.global_config.database_path)

    state = db.get_simulation_state()
    stats = db.get_stats()

    print("\n=== SIMULATION STATUS ===")
    print(f"Status: {state.get('status', 'UNKNOWN')}")
    print(f"Started: {state.get('started_at', 'N/A')}")
    print(f"Stopped: {state.get('stopped_at', 'N/A')}")

    print("\n=== DATABASE STATS ===")
    print(f"Alerts: {stats.get('alerts', 0)}")
    print(f"Portfolios: {stats.get('portfolios', 0)}")
    print(f"Open Positions: {stats.get('positions_open', 0)}")
    print(f"Closed Positions: {stats.get('positions_closed', 0)}")
    print(f"V5 Watchlist: {stats.get('watchlist', 0)}")

    # Portfolio summaries
    portfolios = db.get_all_portfolios()
    if portfolios:
        print("\n=== PORTFOLIOS ===")
        print(f"{'Name':<20} {'Balance':>12} {'Trades':>8} {'WR':>8}")
        print("-" * 50)
        for p in portfolios:
            name = p.get('name', p.get('id', 'Unknown'))
            balance = p.get('current_balance', 0)
            trades = p.get('total_trades', 0)
            winners = p.get('winners', 0)
            wr = (winners / trades * 100) if trades > 0 else 0
            print(f"{name:<20} ${balance:>10.2f} {trades:>8} {wr:>7.1f}%")


def cmd_reset(args):
    """Reset the simulation."""
    if not args.force:
        confirm = input("Are you sure you want to reset? This will delete all data. (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    settings = get_settings()
    db = Database(settings.global_config.database_path)

    state = db.get_simulation_state()
    if state.get('status') == 'RUNNING':
        print("Error: Cannot reset while simulation is running.")
        print("Stop the simulation first with: python -m simulation.cli stop")
        return

    db.clear_all_data()
    print("Simulation reset complete.")


def cmd_server(args):
    """Start the API server."""
    try:
        from .api.server import run_server
        print(f"Starting API server on {args.host}:{args.port}...")
        run_server(args.host, args.port)
    except ImportError as e:
        print(f"Error: {e}")
        print("Install required packages: pip install fastapi uvicorn")


def cmd_config(args):
    """Show or edit configuration."""
    settings = get_settings()

    if args.show:
        print(json.dumps(settings.to_dict(), indent=2))
    else:
        print("Configuration file:", settings.global_config.database_path)
        print("\nPortfolios:")
        for pid, pconfig in settings.portfolios.items():
            status = "enabled" if pconfig.enabled else "disabled"
            print(f"  - {pconfig.name} ({pid}): ${pconfig.initial_balance} [{status}]")


def cmd_portfolios(args):
    """Show portfolio details."""
    settings = get_settings()
    db = Database(settings.global_config.database_path)

    portfolios = db.get_all_portfolios()

    print("\n=== PORTFOLIO DETAILS ===\n")

    for p in portfolios:
        name = p.get('name', p.get('id', 'Unknown'))
        ptype = p.get('type', 'unknown')
        enabled = "Yes" if p.get('enabled', True) else "No"
        initial = p.get('initial_balance', 0)
        current = p.get('current_balance', 0)
        pnl = current - initial
        pnl_pct = (pnl / initial * 100) if initial > 0 else 0

        trades = p.get('total_trades', 0)
        winners = p.get('winners', 0)
        losers = p.get('losers', 0)
        wr = (winners / trades * 100) if trades > 0 else 0

        profit = p.get('total_profit', 0)
        loss = abs(p.get('total_loss', 0))
        pf = (profit / loss) if loss > 0 else 0

        print(f"{name}")
        print(f"  Type: {ptype} | Enabled: {enabled}")
        print(f"  Balance: ${current:.2f} (initial: ${initial:.2f})")
        print(f"  P&L: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
        print(f"  Trades: {trades} (W: {winners}, L: {losers})")
        print(f"  Win Rate: {wr:.1f}% | Profit Factor: {pf:.2f}")
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MEGA BUY Live Simulation System CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start the simulation")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get simulation status")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset the simulation")
    reset_parser.add_argument("-f", "--force", action="store_true", help="Skip confirmation")

    # Server command
    server_parser = subparsers.add_parser("server", help="Start API server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=8001, help="Port to listen on")

    # Config command
    config_parser = subparsers.add_parser("config", help="Show configuration")
    config_parser.add_argument("--show", action="store_true", help="Show full config as JSON")

    # Portfolios command
    portfolios_parser = subparsers.add_parser("portfolios", help="Show portfolio details")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "start": cmd_start,
        "status": cmd_status,
        "reset": cmd_reset,
        "server": cmd_server,
        "config": cmd_config,
        "portfolios": cmd_portfolios,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
