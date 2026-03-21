"""
Configuration management for the simulation system.
Handles loading, saving, and validating configuration.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, List, Any
from pathlib import Path
from enum import Enum


class SimulationMode(Enum):
    """Simulation mode - determines data source and labeling."""
    LIVE = "LIVE"       # Real-time alerts from Supabase, labels trades as 🟢 LIVE
    BACKTEST = "BACKTEST"  # Historical alerts from backtest.db, labels trades as 🟠 BACKTEST


@dataclass
class ExitStrategyConfig:
    """Exit strategy parameters."""
    sl_pct: float = 5.0
    be_activation_pct: float = 4.0
    be_sl_pct: float = 0.5
    trailing_activation_pct: float = 15.0
    trailing_distance_pct: float = 10.0


@dataclass
class FilterConditions:
    """Empirical filter conditions.

    Default values from LIVE_SIMULATION_SYSTEM_REPORT.md (Max Win Rate):
    - pp=True, ec=True
    - DI- >= 22, DI+ <= 25, ADX >= 35, Vol >= 100%
    """
    pp: bool = True
    ec: bool = True
    di_minus_min: float = 22.0
    di_plus_max: float = 25.0
    adx_min: float = 35.0
    vol_min: float = 100.0


@dataclass
class V5Config:
    """V5 surveillance configuration."""
    max_surveillance_hours: int = 72
    stc_oversold_threshold: float = 0.2
    choch_margin_pct: float = 0.5
    swing_left: int = 5
    swing_right: int = 3
    monitoring_interval_sec: int = 900  # 15 minutes


@dataclass
class PortfolioConfig:
    """Configuration for a single portfolio."""
    id: str
    name: str
    type: str  # "empirical_filter" | "p_success_threshold" | "v5_surveillance"
    enabled: bool = True
    initial_balance: float = 2000.0
    position_size_pct: float = 12.0
    max_concurrent_trades: int = 8
    # Type-specific config
    filter_conditions: Optional[FilterConditions] = None
    threshold: Optional[float] = None
    v5_config: Optional[V5Config] = None


@dataclass
class GlobalConfig:
    """Global simulation parameters."""
    mode: str = "LIVE"  # "LIVE" or "BACKTEST"
    alert_polling_interval_sec: int = 30
    price_polling_interval_sec: int = 15
    database_path: str = "data/simulation.db"
    backtest_db_path: str = "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/backtest/data/backtest.db"
    log_level: str = "INFO"
    alerts_api_url: str = "http://localhost:9000"
    binance_api_url: str = "https://api.binance.com"
    # Backtest replay settings
    backtest_days: int = 7  # Number of days to replay in BACKTEST mode
    backtest_speed: float = 0.0  # 0 = instant, 1.0 = real-time, 10.0 = 10x faster


@dataclass
class Settings:
    """Main settings class containing all configuration."""
    version: str = "1.0"
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    exit_strategy: ExitStrategyConfig = field(default_factory=ExitStrategyConfig)
    portfolios: Dict[str, PortfolioConfig] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default portfolios if empty."""
        if not self.portfolios:
            self.portfolios = self._create_default_portfolios()

    def _create_default_portfolios(self) -> Dict[str, PortfolioConfig]:
        """Create the 7 default portfolios.

        Conditions from LIVE_SIMULATION_SYSTEM_REPORT.md:
        - Max WR: pp=True, ec=True, DI- >= 22, DI+ <= 25, ADX >= 35, Vol >= 100%
        - Équilibré: pp=True, ec=True, DI- >= 22, DI+ <= 20, ADX >= 21, Vol >= 100%
        - Gros Gagnants: pp=True, ec=True, DI- >= 22, DI+ <= 25, ADX >= 21, Vol >= 100%
        """
        return {
            # Empirical Filters (exact conditions from LIVE_SIMULATION_SYSTEM_REPORT.md)
            "max_wr": PortfolioConfig(
                id="max_wr",
                name="Max Win Rate",
                type="empirical_filter",
                filter_conditions=FilterConditions(
                    pp=True, ec=True,
                    di_minus_min=22.0, di_plus_max=25.0,
                    adx_min=35.0, vol_min=100.0
                )
            ),
            "balanced_filter": PortfolioConfig(
                id="balanced_filter",
                name="Équilibré",
                type="empirical_filter",
                filter_conditions=FilterConditions(
                    pp=True, ec=True,
                    di_minus_min=22.0, di_plus_max=20.0,
                    adx_min=21.0, vol_min=100.0
                )
            ),
            "big_winners": PortfolioConfig(
                id="big_winners",
                name="Gros Gagnants",
                type="empirical_filter",
                filter_conditions=FilterConditions(
                    pp=True, ec=True,
                    di_minus_min=22.0, di_plus_max=25.0,
                    adx_min=21.0, vol_min=100.0
                )
            ),
            # ML Thresholds
            "aggressive": PortfolioConfig(
                id="aggressive",
                name="Aggressive",
                type="p_success_threshold",
                threshold=0.30
            ),
            "balanced_ml": PortfolioConfig(
                id="balanced_ml",
                name="Balanced",
                type="p_success_threshold",
                threshold=0.50
            ),
            "conservative": PortfolioConfig(
                id="conservative",
                name="Conservative",
                type="p_success_threshold",
                threshold=0.70
            ),
            # V5 Surveillance
            "backtest_v5": PortfolioConfig(
                id="backtest_v5",
                name="Backtest V5",
                type="v5_surveillance",
                v5_config=V5Config()
            ),
        }

    def get_portfolio(self, portfolio_id: str) -> Optional[PortfolioConfig]:
        """Get a portfolio configuration by ID."""
        return self.portfolios.get(portfolio_id)

    def get_enabled_portfolios(self) -> List[PortfolioConfig]:
        """Get all enabled portfolios."""
        return [p for p in self.portfolios.values() if p.enabled]

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "version": self.version,
            "global": asdict(self.global_config),
            "exit_strategy": asdict(self.exit_strategy),
            "portfolios": {
                pid: self._portfolio_to_dict(p)
                for pid, p in self.portfolios.items()
            }
        }

    def _portfolio_to_dict(self, p: PortfolioConfig) -> Dict[str, Any]:
        """Convert portfolio config to dictionary."""
        result = {
            "id": p.id,
            "name": p.name,
            "type": p.type,
            "enabled": p.enabled,
            "initial_balance": p.initial_balance,
            "position_size_pct": p.position_size_pct,
            "max_concurrent_trades": p.max_concurrent_trades,
        }
        if p.filter_conditions:
            result["filter_conditions"] = asdict(p.filter_conditions)
        if p.threshold is not None:
            result["threshold"] = p.threshold
        if p.v5_config:
            result["v5_config"] = asdict(p.v5_config)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Create settings from dictionary."""
        settings = cls(
            version=data.get("version", "1.0"),
            global_config=GlobalConfig(**data.get("global", {})),
            exit_strategy=ExitStrategyConfig(**data.get("exit_strategy", {})),
            portfolios={}
        )

        # Parse portfolios
        for pid, pdata in data.get("portfolios", {}).items():
            filter_conditions = None
            if "filter_conditions" in pdata:
                filter_conditions = FilterConditions(**pdata["filter_conditions"])

            v5_config = None
            if "v5_config" in pdata:
                v5_config = V5Config(**pdata["v5_config"])

            settings.portfolios[pid] = PortfolioConfig(
                id=pdata.get("id", pid),
                name=pdata.get("name", pid),
                type=pdata.get("type", "empirical_filter"),
                enabled=pdata.get("enabled", True),
                initial_balance=pdata.get("initial_balance", 2000.0),
                position_size_pct=pdata.get("position_size_pct", 12.0),
                max_concurrent_trades=pdata.get("max_concurrent_trades", 8),
                filter_conditions=filter_conditions,
                threshold=pdata.get("threshold"),
                v5_config=v5_config
            )

        return settings


def get_config_path() -> Path:
    """Get the configuration file path."""
    base_dir = Path(__file__).parent.parent
    return base_dir / "config" / "simulation_config.json"


def load_config() -> Settings:
    """Load configuration from file or create default."""
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Settings.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not parse config file: {e}")
            print("Using default configuration.")

    # Create default settings
    settings = Settings()
    save_config(settings)
    return settings


def save_config(settings: Settings) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from file."""
    global _settings
    _settings = load_config()
    return _settings
