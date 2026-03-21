'use client';

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface PortfolioSummary {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  balance: number;
  return_pct: number;
  pnl_usd: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
  open_positions: number;
  max_drawdown_pct: number;
  live_only?: boolean;  // V5 is live-only, not used in backtest
}

interface Position {
  id: string;
  portfolio_id: string;
  portfolio_name?: string;
  portfolio_type?: string;
  alert_id?: string;
  pair: string;
  timeframes?: string;
  entry_price: number;
  entry_timestamp?: string;
  current_price: number;
  highest_price?: number;
  lowest_price?: number;
  current_pnl_pct: number;
  current_pnl_usd: number;
  allocated_capital: number;
  initial_sl?: number;
  current_sl?: number;
  be_activated: boolean;
  be_activation_price?: number;
  trailing_activated: boolean;
  trailing_activation_price?: number;
  trailing_sl?: number;
  status: string;
  mode: 'LIVE' | 'BACKTEST';
  last_sync?: string;
  // Closed trade fields
  exit_price?: number;
  exit_timestamp?: string;
  exit_reason?: string;
  final_pnl_pct?: number;
  final_pnl_usd?: number;
  // Calculated fields from API
  duration_hours?: number;
  distance_to_sl_pct?: number;
  drawdown_from_high_pct?: number;
  max_runup_pct?: number;
  // Alert data
  alert?: {
    id: string;
    pair: string;
    price: number;
    alert_timestamp: string;
    timeframes: string;
    scanner_score: number;
    p_success: number;
    pp: number;
    ec: number;
    di_plus_4h: number;
    di_minus_4h: number;
    adx_4h: number;
    vol_pct_max: number;
  };
}

interface WatchlistEntry {
  id: string;
  pair: string;
  conditions_met: number;
  hours_elapsed: number;
  hours_remaining: number;
  status: string;
  conditions: Record<string, boolean>;
}

interface GlobalStats {
  total_initial: number;
  total_balance: number;
  total_pnl: number;
  total_return_pct: number;
  total_open_positions: number;
  total_trades: number;
}

interface ModeData {
  emoji: string;
  active: boolean;
  alerts_captured?: number;
  progress?: {
    processed: number;
    total: number;
    progress_pct: number;
  };
  global: GlobalStats;
  portfolios: PortfolioSummary[];
}

interface SimulationOverview {
  running: boolean;
  timestamp: string;
  live: ModeData;
  backtest: ModeData;
  watchlist_stats: {
    watching: number;
    entry: number;
    expired: number;
    rejected?: number;
    total: number;
  };
}

interface ExitStrategyConfig {
  sl_pct: number;
  be_activation_pct: number;
  be_sl_pct: number;
  trailing_activation_pct: number;
  trailing_distance_pct: number;
}

interface GlobalConfigData {
  mode: 'LIVE' | 'BACKTEST';
  alert_polling_interval_sec: number;
  price_polling_interval_sec: number;
  database_path: string;
  backtest_db_path: string;
  log_level: string;
  alerts_api_url: string;
  binance_api_url: string;
  backtest_days: number;
  backtest_speed: number;
}

interface PortfolioConfigData {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  initial_balance: number;
  position_size_pct: number;
  max_concurrent_trades: number;
  threshold?: number;
  filter_conditions?: {
    pp: boolean;
    ec: boolean;
    di_minus_min: number;
    di_plus_max: number;
    adx_min: number;
    vol_min: number;
  };
}

interface SimulationConfig {
  version: string;
  global: GlobalConfigData;
  exit_strategy: ExitStrategyConfig;
  portfolios: Record<string, PortfolioConfigData>;
}

// API Base URL
const API_BASE = 'http://localhost:8001';

// Helper functions
const formatCurrency = (value: number) => {
  const sign = value >= 0 ? '' : '-';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
};

const formatPercent = (value: number) => {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
};

export default function SimulationPage() {
  const [overview, setOverview] = useState<SimulationOverview | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[]>([]);
  const [config, setConfig] = useState<SimulationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'positions' | 'closed' | 'watchlist' | 'config'>('overview');
  const [closedTrades, setClosedTrades] = useState<Position[]>([]);
  const [closedFilter, setClosedFilter] = useState<'all' | 'live' | 'backtest'>('all');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [loadingPosition, setLoadingPosition] = useState(false);
  const [positionFilter, setPositionFilter] = useState<'all' | 'live' | 'backtest'>('all');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'flat' | 'grouped'>('grouped');

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [overviewRes, positionsRes, closedRes, watchlistRes] = await Promise.all([
        fetch(`${API_BASE}/api/overview`),
        fetch(`${API_BASE}/api/positions?status=open`),
        fetch(`${API_BASE}/api/positions?status=closed`),
        fetch(`${API_BASE}/api/watchlist?active_only=true`),
      ]);

      if (overviewRes.ok) {
        setOverview(await overviewRes.json());
      }
      if (positionsRes.ok) {
        setPositions(await positionsRes.json());
      }
      if (closedRes.ok) {
        setClosedTrades(await closedRes.json());
      }
      if (watchlistRes.ok) {
        setWatchlist(await watchlistRes.json());
      }

      setError(null);
    } catch (err) {
      setError('Failed to connect to simulation API. Make sure the server is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch config
  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/config`);
      if (res.ok) {
        setConfig(await res.json());
      }
    } catch (err) {
      console.error('Failed to fetch config:', err);
    }
  }, []);

  useEffect(() => {
    fetchData();
    fetchConfig();
    const interval = setInterval(fetchData, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [fetchData, fetchConfig]);

  // Control functions
  const startSimulation = async () => {
    try {
      await fetch(`${API_BASE}/api/simulation/start`, { method: 'POST' });
      fetchData();
    } catch (err) {
      setError('Failed to start simulation');
    }
  };

  const stopSimulation = async () => {
    try {
      await fetch(`${API_BASE}/api/simulation/stop`, { method: 'POST' });
      fetchData();
    } catch (err) {
      setError('Failed to stop simulation');
    }
  };

  const resetSimulation = async () => {
    if (!confirm('Are you sure you want to reset the simulation? All data will be lost.')) {
      return;
    }
    try {
      await fetch(`${API_BASE}/api/simulation/reset`, { method: 'POST' });
      fetchData();
      fetchConfig();
      setSaveMessage('Simulation reset successfully');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      setError('Failed to reset simulation');
    }
  };

  const startBacktest = async () => {
    const days = config?.global?.backtest_days || 7;
    const speed = config?.global?.backtest_speed || 0;
    try {
      await fetch(`${API_BASE}/api/backtest/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days, speed })
      });
      fetchData();
      setSaveMessage(`🟠 Backtest started (${days} days)`);
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      setError('Failed to start backtest');
    }
  };

  const stopBacktest = async () => {
    try {
      await fetch(`${API_BASE}/api/backtest/stop`, { method: 'POST' });
      fetchData();
      setSaveMessage('🟠 Backtest stopped');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err) {
      setError('Failed to stop backtest');
    }
  };

  // Toggle group expansion
  const toggleGroup = (groupKey: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupKey)) {
        newSet.delete(groupKey);
      } else {
        newSet.add(groupKey);
      }
      return newSet;
    });
  };

  // Expand/collapse all groups
  const toggleAllGroups = (expand: boolean, groupKeys: string[]) => {
    if (expand) {
      setExpandedGroups(new Set(groupKeys));
    } else {
      setExpandedGroups(new Set());
    }
  };

  // Group positions by date and portfolio
  const groupPositions = (positionsList: Position[]) => {
    const groups: Record<string, Record<string, Position[]>> = {};

    positionsList.forEach(pos => {
      const date = pos.entry_timestamp
        ? new Date(pos.entry_timestamp).toLocaleDateString('fr-FR', {
            weekday: 'short',
            day: '2-digit',
            month: 'short',
            year: 'numeric'
          })
        : 'Unknown Date';

      const portfolioKey = pos.portfolio_name || pos.portfolio_id;

      if (!groups[date]) {
        groups[date] = {};
      }
      if (!groups[date][portfolioKey]) {
        groups[date][portfolioKey] = [];
      }
      groups[date][portfolioKey].push(pos);
    });

    // Sort by date (newest first)
    const sortedDates = Object.keys(groups).sort((a, b) => {
      if (a === 'Unknown Date') return 1;
      if (b === 'Unknown Date') return -1;
      const dateA = new Date(groups[a][Object.keys(groups[a])[0]][0]?.entry_timestamp || 0);
      const dateB = new Date(groups[b][Object.keys(groups[b])[0]][0]?.entry_timestamp || 0);
      return dateB.getTime() - dateA.getTime();
    });

    return { groups, sortedDates };
  };

  // Load position details
  const loadPositionDetails = async (positionId: string) => {
    setLoadingPosition(true);
    try {
      const res = await fetch(`${API_BASE}/api/positions/${positionId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedPosition(data);
      }
    } catch (err) {
      console.error('Failed to load position details:', err);
    } finally {
      setLoadingPosition(false);
    }
  };

  // Save config
  const saveConfig = async () => {
    if (!config) return;

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/api/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (res.ok) {
        setSaveMessage('Configuration saved! Restart simulation to apply changes.');
        setTimeout(() => setSaveMessage(null), 5000);
      } else {
        throw new Error('Failed to save');
      }
    } catch (err) {
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  // Update exit strategy
  const updateExitStrategy = (key: keyof ExitStrategyConfig, value: number) => {
    if (!config) return;
    setConfig({
      ...config,
      exit_strategy: { ...config.exit_strategy, [key]: value }
    });
  };

  // Update global config
  const updateGlobalConfig = (key: keyof GlobalConfigData, value: number | string) => {
    if (!config) return;
    setConfig({
      ...config,
      global: { ...config.global, [key]: value }
    });
  };

  // Update portfolio
  const updatePortfolio = (portfolioId: string, key: string, value: any) => {
    if (!config) return;
    setConfig({
      ...config,
      portfolios: {
        ...config.portfolios,
        [portfolioId]: { ...config.portfolios[portfolioId], [key]: value }
      }
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-6 flex items-center justify-center">
        <div className="text-xl">Loading simulation data...</div>
      </div>
    );
  }

  if (error && !overview) {
    return (
      <div className="min-h-screen bg-gray-900 text-white p-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold mb-6">Live Simulation</h1>
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4">
            <p className="text-red-300">{error}</p>
            <p className="text-gray-400 mt-2 text-sm">
              Start the simulation API server with:
              <code className="bg-gray-800 px-2 py-1 ml-2 rounded">
                ./simulation/start.sh
              </code>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">Simulation Dashboard</h1>
            </div>
            <div className="flex items-center gap-4 mt-2">
              {/* LIVE Status */}
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${
                overview?.live?.active
                  ? 'bg-green-500/20 text-green-400 border border-green-500'
                  : 'bg-gray-700 text-gray-400 border border-gray-600'
              }`}>
                <span className={overview?.live?.active ? 'animate-pulse' : ''}>🟢</span>
                LIVE {overview?.live?.active ? '(Running)' : '(Stopped)'}
                {overview?.live?.alerts_captured !== undefined && (
                  <span className="ml-1 text-xs">• {overview.live.alerts_captured} alerts</span>
                )}
              </div>
              {/* BACKTEST Status */}
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${
                overview?.backtest?.active
                  ? 'bg-orange-500/20 text-orange-400 border border-orange-500'
                  : 'bg-gray-700 text-gray-400 border border-gray-600'
              }`}>
                <span className={overview?.backtest?.active ? 'animate-pulse' : ''}>🟠</span>
                BACKTEST {overview?.backtest?.active ? `(${overview.backtest.progress?.progress_pct?.toFixed(0)}%)` : overview?.backtest?.progress?.progress_pct === 100 ? '(Done)' : '(Idle)'}
              </div>
            </div>
            <p className="text-gray-500 text-sm mt-1">
              Last update: {overview?.timestamp ? new Date(overview.timestamp).toLocaleTimeString() : 'N/A'}
            </p>
          </div>
          <div className="flex flex-col gap-2">
            {/* LIVE Controls */}
            <div className="flex gap-2">
              {overview?.running ? (
                <button
                  onClick={stopSimulation}
                  className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded font-medium flex items-center gap-2"
                >
                  <span>■</span> Stop LIVE
                </button>
              ) : (
                <button
                  onClick={startSimulation}
                  className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded font-medium flex items-center gap-2"
                >
                  <span>▶</span> Start LIVE
                </button>
              )}
              <button
                onClick={resetSimulation}
                className="bg-gray-600 hover:bg-gray-700 px-4 py-2 rounded font-medium"
                disabled={overview?.running}
              >
                Reset
              </button>
            </div>
            {/* BACKTEST Controls */}
            <div className="flex gap-2">
              {overview?.backtest?.active ? (
                <button
                  onClick={stopBacktest}
                  className="bg-orange-600 hover:bg-orange-700 px-4 py-2 rounded font-medium flex items-center gap-2"
                >
                  <span>■</span> Stop Backtest
                </button>
              ) : (
                <button
                  onClick={startBacktest}
                  className="bg-orange-500 hover:bg-orange-600 px-4 py-2 rounded font-medium flex items-center gap-2"
                >
                  <span>▶</span> Run Backtest ({config?.global?.backtest_days || 7} days)
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Save Message */}
        {saveMessage && (
          <div className="mb-4 p-3 bg-green-900/50 border border-green-500 rounded-lg text-green-300">
            {saveMessage}
          </div>
        )}

        {/* Global Stats - LIVE */}
        {overview?.live && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <span className="text-2xl">{overview.live.emoji}</span>
              LIVE Mode
              {overview.live.alerts_captured !== undefined && (
                <span className="text-sm text-gray-400 ml-2">
                  ({overview.live.alerts_captured} alerts captured)
                </span>
              )}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <div className="bg-gray-800 rounded-lg p-4 border-l-4 border-green-500">
                <div className="text-gray-400 text-sm">Balance</div>
                <div className="text-2xl font-bold">{formatCurrency(overview.live.global.total_balance)}</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">P&L</div>
                <div className={`text-2xl font-bold ${overview.live.global.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(overview.live.global.total_pnl)}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Return</div>
                <div className={`text-2xl font-bold ${overview.live.global.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercent(overview.live.global.total_return_pct)}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Positions</div>
                <div className="text-2xl font-bold">{overview.live.global.total_open_positions}</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Trades</div>
                <div className="text-2xl font-bold">{overview.live.global.total_trades}</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">V5 Watching</div>
                <div className="text-2xl font-bold">{overview.watchlist_stats?.watching || 0}</div>
              </div>
            </div>
          </div>
        )}

        {/* Global Stats - BACKTEST */}
        {overview?.backtest && overview.backtest.global.total_open_positions > 0 && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
              <span className="text-2xl">{overview.backtest.emoji}</span>
              BACKTEST Mode
              {overview.backtest.progress && (
                <span className="text-sm text-gray-400 ml-2">
                  ({overview.backtest.progress.processed}/{overview.backtest.progress.total} - {overview.backtest.progress.progress_pct.toFixed(0)}%)
                </span>
              )}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
              <div className="bg-gray-800 rounded-lg p-4 border-l-4 border-orange-500">
                <div className="text-gray-400 text-sm">Balance</div>
                <div className="text-2xl font-bold">{formatCurrency(overview.backtest.global.total_balance)}</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">P&L</div>
                <div className={`text-2xl font-bold ${overview.backtest.global.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatCurrency(overview.backtest.global.total_pnl)}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Return</div>
                <div className={`text-2xl font-bold ${overview.backtest.global.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercent(overview.backtest.global.total_return_pct)}
                </div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Positions</div>
                <div className="text-2xl font-bold">{overview.backtest.global.total_open_positions}</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Trades</div>
                <div className="text-2xl font-bold">{overview.backtest.global.total_trades}</div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-700">
          {['overview', 'positions', 'closed', 'watchlist', 'config'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`px-4 py-2 font-medium capitalize ${
                activeTab === tab
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'overview' && overview && (
          <div className="space-y-6">
            {/* LIVE Portfolio Table */}
            {overview.live?.portfolios && overview.live.portfolios.length > 0 && (
              <div className="bg-gray-800 rounded-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
                  <span className="text-xl">{overview.live.emoji}</span>
                  <h2 className="text-lg font-semibold">LIVE Portfolios</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-4 py-3 text-left">Portfolio</th>
                        <th className="px-4 py-3 text-right">Balance</th>
                        <th className="px-4 py-3 text-right">Return</th>
                        <th className="px-4 py-3 text-right">Win Rate</th>
                        <th className="px-4 py-3 text-right">P.F.</th>
                        <th className="px-4 py-3 text-right">Trades</th>
                        <th className="px-4 py-3 text-right">Open</th>
                        <th className="px-4 py-3 text-right">Max DD</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.live.portfolios.map((p) => (
                        <tr key={p.id} className="border-t border-gray-700 hover:bg-gray-700/50">
                          <td className="px-4 py-3">
                            <div className="font-medium">{p.name}</div>
                            <div className="text-xs text-gray-400">{p.type}</div>
                          </td>
                          <td className="px-4 py-3 text-right">{formatCurrency(p.balance)}</td>
                          <td className={`px-4 py-3 text-right ${p.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatPercent(p.return_pct)}
                          </td>
                          <td className="px-4 py-3 text-right">{p.win_rate.toFixed(1)}%</td>
                          <td className="px-4 py-3 text-right">{p.profit_factor.toFixed(2)}</td>
                          <td className="px-4 py-3 text-right">{p.total_trades}</td>
                          <td className="px-4 py-3 text-right">{p.open_positions}</td>
                          <td className="px-4 py-3 text-right text-red-400">-{p.max_drawdown_pct.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* BACKTEST Portfolio Table */}
            {overview.backtest?.portfolios && overview.backtest.portfolios.length > 0 && (
              <div className="bg-gray-800 rounded-lg overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-700 flex items-center gap-2">
                  <span className="text-xl">{overview.backtest.emoji}</span>
                  <h2 className="text-lg font-semibold">BACKTEST Portfolios</h2>
                  {overview.backtest.progress && (
                    <span className="text-sm text-gray-400 ml-2">
                      ({overview.backtest.progress.processed}/{overview.backtest.progress.total})
                    </span>
                  )}
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-4 py-3 text-left">Portfolio</th>
                        <th className="px-4 py-3 text-right">Balance</th>
                        <th className="px-4 py-3 text-right">Return</th>
                        <th className="px-4 py-3 text-right">Win Rate</th>
                        <th className="px-4 py-3 text-right">P.F.</th>
                        <th className="px-4 py-3 text-right">Trades</th>
                        <th className="px-4 py-3 text-right">Open</th>
                        <th className="px-4 py-3 text-right">Max DD</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.backtest.portfolios.map((p) => (
                        <tr key={p.id} className={`border-t border-gray-700 hover:bg-gray-700/50 ${p.live_only ? 'opacity-50' : ''}`}>
                          <td className="px-4 py-3">
                            <div className="font-medium">{p.name}</div>
                            <div className="text-xs text-gray-400">
                              {p.type}
                              {p.live_only && <span className="ml-2 text-yellow-500">(Live only)</span>}
                            </div>
                          </td>
                          {p.live_only ? (
                            <td colSpan={7} className="px-4 py-3 text-center text-gray-500 italic">
                              N/A - V5 requires real-time monitoring
                            </td>
                          ) : (
                            <>
                              <td className="px-4 py-3 text-right">{formatCurrency(p.balance)}</td>
                              <td className={`px-4 py-3 text-right ${p.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {formatPercent(p.return_pct)}
                              </td>
                              <td className="px-4 py-3 text-right">{p.win_rate.toFixed(1)}%</td>
                              <td className="px-4 py-3 text-right">{p.profit_factor.toFixed(2)}</td>
                              <td className="px-4 py-3 text-right">{p.total_trades}</td>
                              <td className="px-4 py-3 text-right">{p.open_positions}</td>
                              <td className="px-4 py-3 text-right text-red-400">-{p.max_drawdown_pct.toFixed(1)}%</td>
                            </>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'positions' && (() => {
          const livePositions = positions.filter(p => p.mode === 'LIVE');
          const backtestPositions = positions.filter(p => p.mode === 'BACKTEST');
          const filteredPositions = positionFilter === 'all' ? positions
            : positionFilter === 'live' ? livePositions
            : backtestPositions;

          const { groups, sortedDates } = groupPositions(filteredPositions);
          const allGroupKeys = sortedDates.flatMap(date =>
            Object.keys(groups[date]).map(portfolio => `${date}__${portfolio}`)
          );

          return (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-700">
              <div className="flex justify-between items-center flex-wrap gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Open Positions ({filteredPositions.length})</h2>
                  <p className="text-xs text-gray-400">Click on a position to see full details</p>
                </div>
                <div className="flex items-center gap-3">
                  {/* View mode toggle */}
                  <div className="flex gap-1 bg-gray-700 rounded-lg p-1">
                    <button
                      onClick={() => setViewMode('grouped')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        viewMode === 'grouped'
                          ? 'bg-purple-600 text-white'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      📁 Groupé
                    </button>
                    <button
                      onClick={() => setViewMode('flat')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        viewMode === 'flat'
                          ? 'bg-purple-600 text-white'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      📋 Liste
                    </button>
                  </div>
                  {/* Filter tabs */}
                  <div className="flex gap-1 bg-gray-700 rounded-lg p-1">
                    <button
                      onClick={() => setPositionFilter('all')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        positionFilter === 'all'
                          ? 'bg-gray-600 text-white'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      All ({positions.length})
                    </button>
                    <button
                      onClick={() => setPositionFilter('live')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        positionFilter === 'live'
                          ? 'bg-green-600 text-white'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      🟢 LIVE ({livePositions.length})
                    </button>
                    <button
                      onClick={() => setPositionFilter('backtest')}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        positionFilter === 'backtest'
                          ? 'bg-orange-600 text-white'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      🟠 BT ({backtestPositions.length})
                    </button>
                  </div>
                </div>
              </div>
              {/* Expand/Collapse all buttons for grouped view */}
              {viewMode === 'grouped' && filteredPositions.length > 0 && (
                <div className="flex gap-2 mt-3">
                  <button
                    onClick={() => toggleAllGroups(true, allGroupKeys)}
                    className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
                  >
                    ➕ Tout déplier
                  </button>
                  <button
                    onClick={() => toggleAllGroups(false, allGroupKeys)}
                    className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
                  >
                    ➖ Tout replier
                  </button>
                </div>
              )}
            </div>
            {filteredPositions.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                {positionFilter === 'all' ? 'No open positions' :
                 positionFilter === 'live' ? 'No LIVE positions' : 'No BACKTEST positions'}
              </div>
            ) : viewMode === 'grouped' ? (
              /* Grouped view */
              <div className="divide-y divide-gray-700">
                {sortedDates.map(date => {
                  const datePositions = Object.values(groups[date]).flat();
                  const datePnl = datePositions.reduce((sum, p) => sum + p.current_pnl_pct, 0);

                  return (
                    <div key={date} className="bg-gray-800">
                      {/* Date Header */}
                      <div className="px-4 py-3 bg-gray-750 border-b border-gray-700 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-lg">📅</span>
                          <span className="font-semibold text-white">{date}</span>
                          <span className="text-sm text-gray-400">({datePositions.length} positions)</span>
                        </div>
                        <span className={`text-sm font-medium ${datePnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {datePnl >= 0 ? '+' : ''}{datePnl.toFixed(2)}% total
                        </span>
                      </div>

                      {/* Portfolios within date */}
                      <div className="divide-y divide-gray-700/50">
                        {Object.entries(groups[date]).map(([portfolioName, portfolioPositions]) => {
                          const groupKey = `${date}__${portfolioName}`;
                          const isExpanded = expandedGroups.has(groupKey);
                          const portfolioPnl = portfolioPositions.reduce((sum, p) => sum + p.current_pnl_pct, 0);
                          const avgPnl = portfolioPnl / portfolioPositions.length;
                          const portfolioMode = portfolioPositions[0]?.mode;

                          return (
                            <div key={groupKey}>
                              {/* Portfolio Header (clickable) */}
                              <div
                                onClick={() => toggleGroup(groupKey)}
                                className="px-6 py-3 bg-gray-700/30 hover:bg-gray-700/50 cursor-pointer flex items-center justify-between transition-colors"
                              >
                                <div className="flex items-center gap-3">
                                  <span className={`transform transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                                    ▶
                                  </span>
                                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                    portfolioMode === 'LIVE'
                                      ? 'bg-green-500/20 text-green-400'
                                      : 'bg-orange-500/20 text-orange-400'
                                  }`}>
                                    {portfolioMode === 'LIVE' ? '🟢' : '🟠'}
                                  </span>
                                  <span className="font-medium text-gray-200">{portfolioName}</span>
                                  <span className="text-sm text-gray-400">
                                    ({portfolioPositions.length} pos)
                                  </span>
                                </div>
                                <div className="flex items-center gap-4">
                                  <span className={`text-sm font-medium ${avgPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    Avg: {avgPnl >= 0 ? '+' : ''}{avgPnl.toFixed(2)}%
                                  </span>
                                  <span className={`text-sm font-medium ${portfolioPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    Total: {portfolioPnl >= 0 ? '+' : ''}{portfolioPnl.toFixed(2)}%
                                  </span>
                                </div>
                              </div>

                              {/* Positions table (collapsible) */}
                              {isExpanded && (
                                <div className="bg-gray-800/50">
                                  <table className="w-full">
                                    <thead className="bg-gray-700/50 text-xs">
                                      <tr>
                                        <th className="px-4 py-2 text-left">Pair</th>
                                        <th className="px-4 py-2 text-center">TF</th>
                                        <th className="px-4 py-2 text-left">Time</th>
                                        <th className="px-4 py-2 text-right">Entry</th>
                                        <th className="px-4 py-2 text-right">Current</th>
                                        <th className="px-4 py-2 text-right">P&L</th>
                                        <th className="px-4 py-2 text-right">Alloc</th>
                                        <th className="px-4 py-2 text-center">Sync</th>
                                        <th className="px-4 py-2 text-center">Status</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {portfolioPositions.map(pos => (
                                        <tr
                                          key={pos.id}
                                          className="border-t border-gray-700/30 hover:bg-gray-700/30 cursor-pointer text-sm"
                                          onClick={() => loadPositionDetails(pos.id)}
                                        >
                                          <td className="px-4 py-2 font-medium">{pos.pair}</td>
                                          <td className="px-4 py-2 text-center">
                                            {pos.timeframes ? (
                                              <span className="text-xs px-2 py-0.5 bg-purple-600/30 text-purple-300 rounded">
                                                {typeof pos.timeframes === 'string'
                                                  ? pos.timeframes.replace(/[\[\]"]/g, '').replace(/,/g, ' ')
                                                  : Array.isArray(pos.timeframes)
                                                    ? pos.timeframes.join(' ')
                                                    : 'N/A'}
                                              </span>
                                            ) : (
                                              <span className="text-xs text-gray-500">-</span>
                                            )}
                                          </td>
                                          <td className="px-4 py-2 text-gray-400 text-xs">
                                            {pos.entry_timestamp
                                              ? new Date(pos.entry_timestamp).toLocaleTimeString()
                                              : 'N/A'}
                                          </td>
                                          <td className="px-4 py-2 text-right">${pos.entry_price.toFixed(4)}</td>
                                          <td className="px-4 py-2 text-right">${pos.current_price.toFixed(4)}</td>
                                          <td className={`px-4 py-2 text-right font-medium ${pos.current_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {formatPercent(pos.current_pnl_pct)}
                                          </td>
                                          <td className="px-4 py-2 text-right text-gray-400">
                                            {formatCurrency(pos.allocated_capital)}
                                          </td>
                                          <td className="px-4 py-2 text-center">
                                            {pos.last_sync ? (
                                              <span className="text-xs text-cyan-400" title={new Date(pos.last_sync).toLocaleString()}>
                                                {new Date(pos.last_sync).toLocaleTimeString()}
                                              </span>
                                            ) : (
                                              <span className="text-xs text-gray-500">-</span>
                                            )}
                                          </td>
                                          <td className="px-4 py-2 text-center">
                                            {pos.trailing_activated ? (
                                              <span className="px-2 py-0.5 bg-yellow-600 rounded text-xs">TRAIL</span>
                                            ) : pos.be_activated ? (
                                              <span className="px-2 py-0.5 bg-green-600 rounded text-xs">BE</span>
                                            ) : (
                                              <span className="px-2 py-0.5 bg-blue-600 rounded text-xs">OPEN</span>
                                            )}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* Flat list view */
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-700">
                    <tr>
                      <th className="px-4 py-3 text-left">Mode</th>
                      <th className="px-4 py-3 text-left">Portfolio</th>
                      <th className="px-4 py-3 text-left">Pair</th>
                      <th className="px-4 py-3 text-center">TF</th>
                      <th className="px-4 py-3 text-left">Entry Time</th>
                      <th className="px-4 py-3 text-right">Entry Price</th>
                      <th className="px-4 py-3 text-right">Current</th>
                      <th className="px-4 py-3 text-right">P&L</th>
                      <th className="px-4 py-3 text-right">Allocation</th>
                      <th className="px-4 py-3 text-center">Last Sync</th>
                      <th className="px-4 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPositions.map((pos) => (
                      <tr
                        key={pos.id}
                        className="border-t border-gray-700 hover:bg-gray-700/50 cursor-pointer"
                        onClick={() => loadPositionDetails(pos.id)}
                      >
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            pos.mode === 'LIVE'
                              ? 'bg-green-500/20 text-green-400'
                              : 'bg-orange-500/20 text-orange-400'
                          }`}>
                            {pos.mode === 'LIVE' ? '🟢 LIVE' : '🟠 BT'}
                          </span>
                        </td>
                        <td className="px-4 py-3">{pos.portfolio_name || pos.portfolio_id}</td>
                        <td className="px-4 py-3 font-medium">{pos.pair}</td>
                        <td className="px-4 py-3 text-center">
                          {pos.timeframes ? (
                            <span className="text-xs px-2 py-1 bg-purple-600/30 text-purple-300 rounded">
                              {typeof pos.timeframes === 'string'
                                ? pos.timeframes.replace(/[\[\]"]/g, '').replace(/,/g, ' ')
                                : Array.isArray(pos.timeframes)
                                  ? pos.timeframes.join(' ')
                                  : 'N/A'}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-300">
                          {pos.entry_timestamp ? (
                            <>
                              <div>{new Date(pos.entry_timestamp).toLocaleDateString()}</div>
                              <div className="text-xs text-gray-500">{new Date(pos.entry_timestamp).toLocaleTimeString()}</div>
                            </>
                          ) : 'N/A'}
                        </td>
                        <td className="px-4 py-3 text-right">${pos.entry_price.toFixed(4)}</td>
                        <td className="px-4 py-3 text-right">${pos.current_price.toFixed(4)}</td>
                        <td className={`px-4 py-3 text-right ${pos.current_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {formatPercent(pos.current_pnl_pct)}
                        </td>
                        <td className="px-4 py-3 text-right">{formatCurrency(pos.allocated_capital)}</td>
                        <td className="px-4 py-3 text-center">
                          {pos.last_sync ? (
                            <span className="text-xs text-cyan-400" title={new Date(pos.last_sync).toLocaleString()}>
                              {new Date(pos.last_sync).toLocaleTimeString()}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {pos.trailing_activated ? (
                            <span className="px-2 py-1 bg-yellow-600 rounded text-xs">TRAILING</span>
                          ) : pos.be_activated ? (
                            <span className="px-2 py-1 bg-green-600 rounded text-xs">BE</span>
                          ) : (
                            <span className="px-2 py-1 bg-blue-600 rounded text-xs">OPEN</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          );
        })()}

        {/* Position Details Modal */}
        {selectedPosition && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
            <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              {/* Modal Header */}
              <div className="sticky top-0 bg-gray-800 px-6 py-4 border-b border-gray-700 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded text-sm font-medium ${
                    selectedPosition.mode === 'LIVE'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-orange-500/20 text-orange-400'
                  }`}>
                    {selectedPosition.mode === 'LIVE' ? '🟢 LIVE' : '🟠 BACKTEST'}
                  </span>
                  <h2 className="text-xl font-bold">{selectedPosition.pair}</h2>
                  <span className="text-gray-400">•</span>
                  <span className="text-gray-400">{selectedPosition.portfolio_name || selectedPosition.portfolio_id}</span>
                </div>
                <button
                  onClick={() => setSelectedPosition(null)}
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ✕
                </button>
              </div>

              {loadingPosition ? (
                <div className="p-8 text-center text-gray-400">Loading...</div>
              ) : (
                <div className="p-6 space-y-6">
                  {/* P&L Summary */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-gray-700 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Current P&L</div>
                      <div className={`text-2xl font-bold ${selectedPosition.current_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercent(selectedPosition.current_pnl_pct)}
                      </div>
                      <div className={`text-sm ${selectedPosition.current_pnl_usd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(selectedPosition.current_pnl_usd)}
                      </div>
                    </div>
                    <div className="bg-gray-700 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Max Run-up</div>
                      <div className="text-2xl font-bold text-green-400">
                        {selectedPosition.max_runup_pct !== undefined ? formatPercent(selectedPosition.max_runup_pct) : 'N/A'}
                      </div>
                    </div>
                    <div className="bg-gray-700 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Drawdown from High</div>
                      <div className="text-2xl font-bold text-red-400">
                        {selectedPosition.drawdown_from_high_pct !== undefined ? `-${selectedPosition.drawdown_from_high_pct.toFixed(2)}%` : 'N/A'}
                      </div>
                    </div>
                    <div className="bg-gray-700 rounded-lg p-4">
                      <div className="text-gray-400 text-sm">Duration</div>
                      <div className="text-2xl font-bold">
                        {selectedPosition.duration_hours !== undefined ? `${selectedPosition.duration_hours.toFixed(1)}h` : 'N/A'}
                      </div>
                    </div>
                  </div>

                  {/* Entry & Price Section */}
                  <div className="bg-gray-700 rounded-lg p-4">
                    <h3 className="text-lg font-semibold mb-4 text-blue-400">Entry & Price</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-gray-400">Entry Price</div>
                        <div className="font-medium">${selectedPosition.entry_price.toFixed(6)}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Current Price</div>
                        <div className="font-medium">${selectedPosition.current_price.toFixed(6)}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Highest Price</div>
                        <div className="font-medium text-green-400">${selectedPosition.highest_price?.toFixed(6) || 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Lowest Price</div>
                        <div className="font-medium text-red-400">${selectedPosition.lowest_price?.toFixed(6) || 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Entry Time</div>
                        <div className="font-medium">{selectedPosition.entry_timestamp ? new Date(selectedPosition.entry_timestamp).toLocaleString() : 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Allocated Capital</div>
                        <div className="font-medium">{formatCurrency(selectedPosition.allocated_capital)}</div>
                      </div>
                    </div>
                  </div>

                  {/* Stop Loss Section */}
                  <div className="bg-gray-700 rounded-lg p-4">
                    <h3 className="text-lg font-semibold mb-4 text-red-400">Stop Loss Management</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-gray-400">Initial SL</div>
                        <div className="font-medium">${selectedPosition.initial_sl?.toFixed(6) || 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Current SL</div>
                        <div className="font-medium text-red-400">${selectedPosition.current_sl?.toFixed(6) || 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Distance to SL</div>
                        <div className="font-medium">
                          {selectedPosition.distance_to_sl_pct !== undefined ? `${selectedPosition.distance_to_sl_pct.toFixed(2)}%` : 'N/A'}
                        </div>
                      </div>
                      <div>
                        <div className="text-gray-400">Trailing SL</div>
                        <div className="font-medium">{selectedPosition.trailing_sl ? `$${selectedPosition.trailing_sl.toFixed(6)}` : 'Not active'}</div>
                      </div>
                    </div>
                    <div className="mt-4 flex gap-4">
                      <div className={`px-3 py-2 rounded text-sm ${selectedPosition.be_activated ? 'bg-green-600' : 'bg-gray-600'}`}>
                        Break-Even: {selectedPosition.be_activated ? `✓ Activated @ $${selectedPosition.be_activation_price?.toFixed(4)}` : 'Not activated'}
                      </div>
                      <div className={`px-3 py-2 rounded text-sm ${selectedPosition.trailing_activated ? 'bg-yellow-600' : 'bg-gray-600'}`}>
                        Trailing: {selectedPosition.trailing_activated ? `✓ Activated @ $${selectedPosition.trailing_activation_price?.toFixed(4)}` : 'Not activated'}
                      </div>
                    </div>
                  </div>

                  {/* Alert Data Section */}
                  {selectedPosition.alert && (
                    <div className="bg-gray-700 rounded-lg p-4">
                      <h3 className="text-lg font-semibold mb-4 text-purple-400">Alert Data</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div>
                          <div className="text-gray-400">Alert Time</div>
                          <div className="font-medium">{new Date(selectedPosition.alert.alert_timestamp).toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-gray-400">Scanner Score</div>
                          <div className="font-medium">{selectedPosition.alert.scanner_score}/10</div>
                        </div>
                        <div>
                          <div className="text-gray-400">p_success</div>
                          <div className="font-medium">{(selectedPosition.alert.p_success * 100).toFixed(1)}%</div>
                        </div>
                        <div>
                          <div className="text-gray-400">Timeframes</div>
                          <div className="font-medium">{selectedPosition.alert.timeframes}</div>
                        </div>
                        <div>
                          <div className="text-gray-400">DI+ (4H)</div>
                          <div className="font-medium">{selectedPosition.alert.di_plus_4h?.toFixed(1) || 'N/A'}</div>
                        </div>
                        <div>
                          <div className="text-gray-400">DI- (4H)</div>
                          <div className="font-medium">{selectedPosition.alert.di_minus_4h?.toFixed(1) || 'N/A'}</div>
                        </div>
                        <div>
                          <div className="text-gray-400">ADX (4H)</div>
                          <div className="font-medium">{selectedPosition.alert.adx_4h?.toFixed(1) || 'N/A'}</div>
                        </div>
                        <div>
                          <div className="text-gray-400">Volume %</div>
                          <div className="font-medium">{selectedPosition.alert.vol_pct_max?.toFixed(1) || 'N/A'}%</div>
                        </div>
                      </div>
                      <div className="mt-3 flex gap-2">
                        <span className={`px-2 py-1 rounded text-xs ${selectedPosition.alert.pp ? 'bg-green-600' : 'bg-gray-600'}`}>
                          PP: {selectedPosition.alert.pp ? 'True' : 'False'}
                        </span>
                        <span className={`px-2 py-1 rounded text-xs ${selectedPosition.alert.ec ? 'bg-green-600' : 'bg-gray-600'}`}>
                          EC: {selectedPosition.alert.ec ? 'True' : 'False'}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* IDs Section */}
                  <div className="bg-gray-700 rounded-lg p-4">
                    <h3 className="text-lg font-semibold mb-4 text-gray-400">Technical IDs</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm font-mono">
                      <div>
                        <div className="text-gray-400">Position ID</div>
                        <div className="text-xs break-all">{selectedPosition.id}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Alert ID</div>
                        <div className="text-xs break-all">{selectedPosition.alert_id || 'N/A'}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Portfolio ID</div>
                        <div className="text-xs break-all">{selectedPosition.portfolio_id}</div>
                      </div>
                      <div>
                        <div className="text-gray-400">Portfolio Type</div>
                        <div className="text-xs">{selectedPosition.portfolio_type || 'N/A'}</div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Closed Trades Tab */}
        {activeTab === 'closed' && (() => {
          const liveClosed = closedTrades.filter(p => p.mode === 'LIVE');
          const backtestClosed = closedTrades.filter(p => p.mode === 'BACKTEST');
          const filteredClosed = closedFilter === 'all' ? closedTrades
            : closedFilter === 'live' ? liveClosed
            : backtestClosed;

          // Calculate stats
          const winners = filteredClosed.filter(p => (p.final_pnl_pct || 0) > 0);
          const losers = filteredClosed.filter(p => (p.final_pnl_pct || 0) < 0);
          const totalPnl = filteredClosed.reduce((sum, p) => sum + (p.final_pnl_usd || 0), 0);
          const avgPnl = filteredClosed.length > 0
            ? filteredClosed.reduce((sum, p) => sum + (p.final_pnl_pct || 0), 0) / filteredClosed.length
            : 0;

          return (
            <div className="space-y-4">
              {/* Filter buttons */}
              <div className="flex items-center gap-4">
                <div className="flex gap-2">
                  <button
                    onClick={() => setClosedFilter('all')}
                    className={`px-3 py-1 rounded ${closedFilter === 'all' ? 'bg-blue-600' : 'bg-gray-700'}`}
                  >
                    All ({closedTrades.length})
                  </button>
                  <button
                    onClick={() => setClosedFilter('live')}
                    className={`px-3 py-1 rounded ${closedFilter === 'live' ? 'bg-green-600' : 'bg-gray-700'}`}
                  >
                    🟢 LIVE ({liveClosed.length})
                  </button>
                  <button
                    onClick={() => setClosedFilter('backtest')}
                    className={`px-3 py-1 rounded ${closedFilter === 'backtest' ? 'bg-orange-600' : 'bg-gray-700'}`}
                  >
                    🟠 BT ({backtestClosed.length})
                  </button>
                </div>

                {/* Stats Summary */}
                <div className="flex gap-4 ml-auto text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-green-400">✓ {winners.length} wins</span>
                    <span className="text-gray-500">|</span>
                    <span className="text-red-400">✗ {losers.length} losses</span>
                  </div>
                  <div className={`font-medium ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Total: {totalPnl >= 0 ? '+' : ''}{totalPnl.toFixed(2)} USD
                  </div>
                  <div className={`font-medium ${avgPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    Avg: {avgPnl >= 0 ? '+' : ''}{avgPnl.toFixed(2)}%
                  </div>
                </div>
              </div>

              {/* Closed Trades Table */}
              <div className="bg-gray-800 rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-3 py-2 text-left">Mode</th>
                        <th className="px-3 py-2 text-left">Portfolio</th>
                        <th className="px-3 py-2 text-left">Pair</th>
                        <th className="px-3 py-2 text-right">Entry</th>
                        <th className="px-3 py-2 text-right">Exit</th>
                        <th className="px-3 py-2 text-right">P&L %</th>
                        <th className="px-3 py-2 text-right">P&L USD</th>
                        <th className="px-3 py-2 text-center">Reason</th>
                        <th className="px-3 py-2 text-right">Duration</th>
                        <th className="px-3 py-2 text-right">Exit Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredClosed.length === 0 ? (
                        <tr>
                          <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                            No closed trades yet
                          </td>
                        </tr>
                      ) : (
                        filteredClosed.map((trade) => {
                          const entryTime = trade.entry_timestamp ? new Date(trade.entry_timestamp) : null;
                          const exitTime = trade.exit_timestamp ? new Date(trade.exit_timestamp) : null;
                          const duration = entryTime && exitTime
                            ? Math.round((exitTime.getTime() - entryTime.getTime()) / (1000 * 60 * 60))
                            : null;
                          const pnlPct = trade.final_pnl_pct || 0;
                          const pnlUsd = trade.final_pnl_usd || 0;

                          return (
                            <tr key={trade.id} className="border-t border-gray-700 hover:bg-gray-700/50">
                              <td className="px-3 py-2">
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                  trade.mode === 'LIVE' ? 'bg-green-500/20 text-green-400' : 'bg-orange-500/20 text-orange-400'
                                }`}>
                                  {trade.mode === 'LIVE' ? '🟢' : '🟠'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-sm">{trade.portfolio_name || trade.portfolio_id}</td>
                              <td className="px-3 py-2 font-medium">{trade.pair}</td>
                              <td className="px-3 py-2 text-right text-sm">${trade.entry_price?.toFixed(4)}</td>
                              <td className="px-3 py-2 text-right text-sm">${trade.exit_price?.toFixed(4)}</td>
                              <td className={`px-3 py-2 text-right font-medium ${pnlPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(2)}%
                              </td>
                              <td className={`px-3 py-2 text-right font-medium ${pnlUsd >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {pnlUsd >= 0 ? '+' : ''}{pnlUsd.toFixed(2)}
                              </td>
                              <td className="px-3 py-2 text-center">
                                <span className={`px-2 py-0.5 rounded text-xs ${
                                  trade.exit_reason === 'STOP_LOSS' ? 'bg-red-500/20 text-red-400' :
                                  trade.exit_reason === 'TAKE_PROFIT' ? 'bg-green-500/20 text-green-400' :
                                  trade.exit_reason === 'TRAILING_STOP' ? 'bg-yellow-500/20 text-yellow-400' :
                                  'bg-gray-500/20 text-gray-400'
                                }`}>
                                  {trade.exit_reason || 'N/A'}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-right text-sm text-gray-400">
                                {duration !== null ? `${duration}h` : '-'}
                              </td>
                              <td className="px-3 py-2 text-right text-sm text-gray-400">
                                {exitTime ? exitTime.toLocaleString() : '-'}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          );
        })()}

        {activeTab === 'watchlist' && (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-700">
              <h2 className="text-lg font-semibold">V5 Watchlist ({watchlist.length} watching)</h2>
            </div>
            {watchlist.length === 0 ? (
              <div className="p-8 text-center text-gray-400">No alerts in watchlist</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-700">
                    <tr>
                      <th className="px-4 py-3 text-left">Pair</th>
                      <th className="px-4 py-3 text-center">Conditions</th>
                      <th className="px-4 py-3 text-right">Elapsed</th>
                      <th className="px-4 py-3 text-right">Remaining</th>
                      <th className="px-4 py-3 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watchlist.map((entry) => (
                      <tr key={entry.id} className="border-t border-gray-700 hover:bg-gray-700/50">
                        <td className="px-4 py-3 font-medium">{entry.pair}</td>
                        <td className="px-4 py-3">
                          <div className="flex justify-center gap-1">
                            {Object.entries(entry.conditions).map(([key, value]) => (
                              <span
                                key={key}
                                className={`w-6 h-6 rounded text-xs flex items-center justify-center ${
                                  value ? 'bg-green-600' : 'bg-gray-600'
                                }`}
                                title={key}
                              >
                                {value ? '✓' : ''}
                              </span>
                            ))}
                          </div>
                          <div className="text-xs text-center text-gray-400 mt-1">
                            {entry.conditions_met}/6
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right">{entry.hours_elapsed.toFixed(1)}h</td>
                        <td className="px-4 py-3 text-right">{entry.hours_remaining.toFixed(1)}h</td>
                        <td className="px-4 py-3 text-center">
                          <span className="px-2 py-1 bg-purple-600 rounded text-xs">
                            {entry.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'config' && config && (
          <div className="space-y-6">
            {/* Exit Strategy */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                Exit Strategy
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Stop Loss (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.exit_strategy.sl_pct}
                    onChange={(e) => updateExitStrategy('sl_pct', parseFloat(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">Initial SL: -{config.exit_strategy.sl_pct}%</p>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">BE Activation (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.exit_strategy.be_activation_pct}
                    onChange={(e) => updateExitStrategy('be_activation_pct', parseFloat(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">Activate at +{config.exit_strategy.be_activation_pct}%</p>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">BE SL (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.exit_strategy.be_sl_pct}
                    onChange={(e) => updateExitStrategy('be_sl_pct', parseFloat(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">New SL: +{config.exit_strategy.be_sl_pct}%</p>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Trailing Activation (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.exit_strategy.trailing_activation_pct}
                    onChange={(e) => updateExitStrategy('trailing_activation_pct', parseFloat(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">Activate at +{config.exit_strategy.trailing_activation_pct}%</p>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Trailing Distance (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={config.exit_strategy.trailing_distance_pct}
                    onChange={(e) => updateExitStrategy('trailing_distance_pct', parseFloat(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">Trail: -{config.exit_strategy.trailing_distance_pct}% from high</p>
                </div>
              </div>
            </div>

            {/* Simulation Mode */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-purple-500 rounded-full"></span>
                Simulation Mode
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div
                  onClick={() => updateGlobalConfig('mode', 'LIVE')}
                  className={`p-4 rounded-lg cursor-pointer border-2 transition-all ${
                    config.global.mode === 'LIVE'
                      ? 'border-green-500 bg-green-500/10'
                      : 'border-gray-600 bg-gray-700 hover:border-gray-500'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">🟢</span>
                    <span className="text-xl font-bold">LIVE Mode</span>
                  </div>
                  <p className="text-gray-400 text-sm">
                    Real-time alerts from Supabase. Trades labeled as 🟢 LIVE.
                    Runs continuously capturing new alerts.
                  </p>
                </div>
                <div
                  onClick={() => updateGlobalConfig('mode', 'BACKTEST')}
                  className={`p-4 rounded-lg cursor-pointer border-2 transition-all ${
                    config.global.mode === 'BACKTEST'
                      ? 'border-orange-500 bg-orange-500/10'
                      : 'border-gray-600 bg-gray-700 hover:border-gray-500'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">🟠</span>
                    <span className="text-xl font-bold">BACKTEST Mode</span>
                  </div>
                  <p className="text-gray-400 text-sm">
                    Historical replay from backtest.db. Trades labeled as 🟠 BACKTEST.
                    Replays past alerts for validation.
                  </p>
                </div>
              </div>

              {/* Backtest specific settings */}
              {config.global.mode === 'BACKTEST' && (
                <div className="mt-4 p-4 bg-orange-500/5 border border-orange-500/30 rounded-lg">
                  <h3 className="text-sm font-semibold text-orange-400 mb-3">Backtest Settings</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Days to Replay</label>
                      <input
                        type="number"
                        value={config.global.backtest_days || 7}
                        onChange={(e) => updateGlobalConfig('backtest_days', parseInt(e.target.value))}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      />
                      <p className="text-xs text-gray-500 mt-1">Number of days of historical data</p>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Replay Speed</label>
                      <select
                        value={config.global.backtest_speed || 0}
                        onChange={(e) => updateGlobalConfig('backtest_speed', parseFloat(e.target.value))}
                        className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                      >
                        <option value="0">Instant (no delay)</option>
                        <option value="10">10x faster</option>
                        <option value="1">Real-time (1x)</option>
                        <option value="0.5">Half-speed (0.5x)</option>
                      </select>
                      <p className="text-xs text-gray-500 mt-1">Speed of alert processing</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Global Settings */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-blue-500 rounded-full"></span>
                Global Settings
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Alert Polling (sec)</label>
                  <input
                    type="number"
                    value={config.global.alert_polling_interval_sec}
                    onChange={(e) => updateGlobalConfig('alert_polling_interval_sec', parseInt(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Price Polling (sec)</label>
                  <input
                    type="number"
                    value={config.global.price_polling_interval_sec}
                    onChange={(e) => updateGlobalConfig('price_polling_interval_sec', parseInt(e.target.value))}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Alerts API URL</label>
                  <input
                    type="text"
                    value={config.global.alerts_api_url}
                    onChange={(e) => updateGlobalConfig('alerts_api_url', e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Log Level</label>
                  <select
                    value={config.global.log_level}
                    onChange={(e) => updateGlobalConfig('log_level', e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Portfolios */}
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                Portfolios Configuration
              </h2>
              <div className="space-y-4">
                {Object.entries(config.portfolios).map(([id, portfolio]) => (
                  <div key={id} className="bg-gray-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={portfolio.enabled}
                            onChange={(e) => updatePortfolio(id, 'enabled', e.target.checked)}
                            className="w-4 h-4 rounded"
                          />
                          <span className="font-medium">{portfolio.name}</span>
                        </label>
                        <span className="text-xs px-2 py-1 bg-gray-600 rounded">
                          {portfolio.type}
                        </span>
                      </div>
                      {portfolio.threshold !== undefined && (
                        <span className="text-sm text-gray-400">
                          Threshold: p_success ≥ {portfolio.threshold}
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Initial Balance ($)</label>
                        <input
                          type="number"
                          value={portfolio.initial_balance}
                          onChange={(e) => updatePortfolio(id, 'initial_balance', parseFloat(e.target.value))}
                          className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Position Size (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={portfolio.position_size_pct}
                          onChange={(e) => updatePortfolio(id, 'position_size_pct', parseFloat(e.target.value))}
                          className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-400 mb-1">Max Concurrent Trades</label>
                        <input
                          type="number"
                          value={portfolio.max_concurrent_trades}
                          onChange={(e) => updatePortfolio(id, 'max_concurrent_trades', parseInt(e.target.value))}
                          className="w-full bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white"
                        />
                      </div>
                    </div>
                    {portfolio.filter_conditions && (
                      <div className="mt-3 pt-3 border-t border-gray-600">
                        <p className="text-sm text-gray-400 mb-2">Filter Conditions:</p>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <span className={`px-2 py-1 rounded ${portfolio.filter_conditions.pp ? 'bg-green-600' : 'bg-gray-600'}`}>
                            PP={portfolio.filter_conditions.pp ? 'True' : 'False'}
                          </span>
                          <span className={`px-2 py-1 rounded ${portfolio.filter_conditions.ec ? 'bg-green-600' : 'bg-gray-600'}`}>
                            EC={portfolio.filter_conditions.ec ? 'True' : 'False'}
                          </span>
                          <span className="px-2 py-1 rounded bg-gray-600">
                            DI- ≥ {portfolio.filter_conditions.di_minus_min}
                          </span>
                          <span className="px-2 py-1 rounded bg-gray-600">
                            DI+ ≤ {portfolio.filter_conditions.di_plus_max}
                          </span>
                          <span className="px-2 py-1 rounded bg-gray-600">
                            ADX ≥ {portfolio.filter_conditions.adx_min}
                          </span>
                          <span className="px-2 py-1 rounded bg-gray-600">
                            Vol ≥ {portfolio.filter_conditions.vol_min}%
                          </span>
                        </div>
                      </div>
                    )}
                    {portfolio.type === 'p_success_threshold' && portfolio.threshold !== undefined && (
                      <div className="mt-3 pt-3 border-t border-gray-600">
                        <label className="block text-sm text-gray-400 mb-1">ML Threshold (p_success)</label>
                        <input
                          type="number"
                          step="0.05"
                          min="0"
                          max="1"
                          value={portfolio.threshold}
                          onChange={(e) => updatePortfolio(id, 'threshold', parseFloat(e.target.value))}
                          className="w-32 bg-gray-600 border border-gray-500 rounded px-3 py-2 text-white"
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Save Button */}
            <div className="flex justify-end gap-4">
              <button
                onClick={fetchConfig}
                className="bg-gray-600 hover:bg-gray-700 px-6 py-2 rounded font-medium"
              >
                Reset Changes
              </button>
              <button
                onClick={saveConfig}
                disabled={saving}
                className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded font-medium disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
