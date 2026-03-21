#!/usr/bin/env python3
"""
MEGA BUY AI - ML Model Retraining Script v2.0
With filter-based features and hyperparameter optimization
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv('/home/assyin/MEGA-BUY-BOT/python/.env')

from supabase import create_client
import lightgbm as lgb
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

# =============================================================================
# CONFIGURATION
# =============================================================================

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Success threshold: profit >= 5%
SUCCESS_THRESHOLD = 5.0

# =============================================================================
# DATA LOADING
# =============================================================================

def load_data() -> Tuple[List[Dict], List[Dict]]:
    """Load all alerts and outcomes from Supabase"""
    print("Loading data from Supabase...")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Fetch alerts
    all_alerts = []
    page_size = 1000
    offset = 0
    while True:
        response = supabase.table('alerts').select('*').range(offset, offset + page_size - 1).execute()
        if not response.data:
            break
        all_alerts.extend(response.data)
        if len(response.data) < page_size:
            break
        offset += page_size

    # Fetch outcomes
    all_outcomes = []
    offset = 0
    while True:
        response = supabase.table('outcomes').select('*').range(offset, offset + page_size - 1).execute()
        if not response.data:
            break
        all_outcomes.extend(response.data)
        if len(response.data) < page_size:
            break
        offset += page_size

    print(f"  Alerts: {len(all_alerts)}")
    print(f"  Outcomes: {len(all_outcomes)}")

    return all_alerts, all_outcomes


def get_max_vol(vol_pct: Optional[Dict]) -> float:
    """Get max volume % from dict"""
    if not vol_pct or not isinstance(vol_pct, dict):
        return 0.0
    values = [float(v) for v in vol_pct.values() if v is not None]
    return max(values) if values else 0.0


def get_max_move(moves: Optional[Dict]) -> float:
    """Get max move from dict"""
    if not moves or not isinstance(moves, dict):
        return 0.0
    values = [float(v) for v in moves.values() if v is not None]
    return max(values) if values else 0.0


def prepare_features(alerts: List[Dict], outcomes: List[Dict]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Prepare feature matrix and labels from alerts and outcomes
    """
    print("\nPreparing features...")

    # Create outcome lookup
    outcome_map = {o['alert_id']: o for o in outcomes}

    # Feature names (ordered)
    feature_names = [
        # Basic alert features
        'scanner_score', 'nb_timeframes', 'puissance', 'condition_count',
        # 4H indicators
        'rsi_4h', 'di_plus_4h', 'di_minus_4h', 'adx_4h', 'dmi_diff_4h',
        # Binary conditions
        'rsi_check', 'dmi_check', 'ast_check', 'choch', 'zone',
        'lazy', 'vol', 'st', 'pp', 'ec',
        # Moves
        'di_plus_move_max', 'di_minus_move_max', 'rsi_move_max', 'adx_move_max',
        # Volume
        'vol_pct_max',
        # Timing
        'hour_of_day', 'day_of_week', 'is_weekend',
        # === NEW FILTER-BASED FEATURES ===
        'di_minus_ge_22', 'di_plus_le_25', 'di_plus_le_20',
        'adx_ge_35', 'adx_ge_21', 'vol_ge_100', 'vol_ge_150',
        'filter_max_wr', 'filter_balanced', 'filter_big_winners',
        'dmi_ratio_4h', 'vol_category', 'adx_category',
        # Derived
        'momentum_score', 'dmi_bullish', 'strong_trend',
    ]

    X_list = []
    y_list = []
    skipped = 0

    for alert in alerts:
        # Get outcome
        outcome = outcome_map.get(alert['id'])
        if not outcome or outcome.get('max_profit_pct') is None:
            skipped += 1
            continue

        # Label: 1 if profit >= 5%, 0 otherwise
        profit = outcome['max_profit_pct']
        label = 1 if profit >= SUCCESS_THRESHOLD else 0

        # Extract features
        try:
            features = extract_features_v2(alert)
            X_list.append([features.get(name, 0.0) for name in feature_names])
            y_list.append(label)
        except Exception as e:
            print(f"  Error processing alert {alert.get('id')}: {e}")
            skipped += 1
            continue

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)

    print(f"  Total samples: {len(X)}")
    print(f"  Skipped: {skipped}")
    print(f"  Positive (success): {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"  Negative (failure): {len(y) - y.sum()} ({(1-y.mean())*100:.1f}%)")

    return X, y, feature_names


def extract_features_v2(alert: Dict) -> Dict[str, float]:
    """
    Extract all features including new filter-based features
    """
    features = {}

    # === Basic alert features ===
    features['scanner_score'] = float(alert.get('scanner_score') or 0)
    features['nb_timeframes'] = float(alert.get('nb_timeframes') or 1)
    features['puissance'] = float(alert.get('puissance') or 0)

    # Condition count
    conditions = ['rsi_check', 'dmi_check', 'ast_check', 'choch', 'zone',
                  'lazy', 'vol', 'st', 'pp', 'ec']
    features['condition_count'] = sum(1 for c in conditions if alert.get(c))

    # === 4H indicators ===
    features['rsi_4h'] = float(alert.get('rsi') or 50)
    features['di_plus_4h'] = float(alert.get('di_plus_4h') or 0)
    features['di_minus_4h'] = float(alert.get('di_minus_4h') or 0)
    features['adx_4h'] = float(alert.get('adx_4h') or 0)
    features['dmi_diff_4h'] = features['di_plus_4h'] - features['di_minus_4h']

    # === Binary conditions ===
    for cond in conditions:
        features[cond] = 1.0 if alert.get(cond) else 0.0

    # === Moves ===
    features['di_plus_move_max'] = get_max_move(alert.get('di_plus_moves'))
    features['di_minus_move_max'] = get_max_move(alert.get('di_minus_moves'))
    features['rsi_move_max'] = get_max_move(alert.get('rsi_moves'))
    features['adx_move_max'] = get_max_move(alert.get('adx_moves'))

    # === Volume ===
    features['vol_pct_max'] = get_max_vol(alert.get('vol_pct'))

    # === Timing ===
    timestamp = alert.get('alert_timestamp')
    if timestamp:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
            features['hour_of_day'] = float(dt.hour)
            features['day_of_week'] = float(dt.weekday())
            features['is_weekend'] = 1.0 if dt.weekday() >= 5 else 0.0
        except:
            features['hour_of_day'] = 12.0
            features['day_of_week'] = 2.0
            features['is_weekend'] = 0.0
    else:
        features['hour_of_day'] = 12.0
        features['day_of_week'] = 2.0
        features['is_weekend'] = 0.0

    # === NEW FILTER-BASED FEATURES ===
    di_plus = features['di_plus_4h']
    di_minus = features['di_minus_4h']
    adx = features['adx_4h']
    vol_max = features['vol_pct_max']
    pp = features['pp']
    ec = features['ec']

    # Binary threshold features
    features['di_minus_ge_22'] = 1.0 if di_minus >= 22 else 0.0
    features['di_plus_le_25'] = 1.0 if di_plus <= 25 else 0.0
    features['di_plus_le_20'] = 1.0 if di_plus <= 20 else 0.0
    features['adx_ge_35'] = 1.0 if adx >= 35 else 0.0
    features['adx_ge_21'] = 1.0 if adx >= 21 else 0.0
    features['vol_ge_100'] = 1.0 if vol_max >= 100 else 0.0
    features['vol_ge_150'] = 1.0 if vol_max >= 150 else 0.0

    # Composite filter passes
    features['filter_max_wr'] = 1.0 if (
        pp == 1.0 and ec == 1.0 and
        di_minus >= 22 and di_plus <= 25 and
        adx >= 35 and vol_max >= 100
    ) else 0.0

    features['filter_balanced'] = 1.0 if (
        pp == 1.0 and ec == 1.0 and
        di_minus >= 22 and di_plus <= 20 and
        adx >= 21 and vol_max >= 100
    ) else 0.0

    features['filter_big_winners'] = 1.0 if (
        pp == 1.0 and ec == 1.0 and
        di_minus >= 22 and di_plus <= 25 and
        adx >= 21 and vol_max >= 100
    ) else 0.0

    # Derived ratios
    features['dmi_ratio_4h'] = di_plus / di_minus if di_minus > 0 else 10.0

    # Volume category
    if vol_max < 100:
        features['vol_category'] = 0.0
    elif vol_max < 150:
        features['vol_category'] = 1.0
    elif vol_max < 200:
        features['vol_category'] = 2.0
    else:
        features['vol_category'] = 3.0

    # ADX category
    if adx < 20:
        features['adx_category'] = 0.0
    elif adx < 30:
        features['adx_category'] = 1.0
    elif adx < 50:
        features['adx_category'] = 2.0
    else:
        features['adx_category'] = 3.0

    # Derived scores
    features['momentum_score'] = (
        features['di_plus_move_max'] +
        features['rsi_move_max'] +
        features['condition_count'] * 2
    ) / 10
    features['dmi_bullish'] = 1.0 if features['dmi_diff_4h'] > 0 else 0.0
    features['strong_trend'] = 1.0 if adx > 25 else 0.0

    return features


# =============================================================================
# HYPERPARAMETER OPTIMIZATION
# =============================================================================

def optimize_hyperparameters(X: np.ndarray, y: np.ndarray, n_trials: int = 50) -> Dict:
    """
    Optimize LightGBM hyperparameters using Optuna
    """
    print("\nOptimizing hyperparameters...")

    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
    except ImportError:
        print("  Optuna not installed, using default parameters")
        return get_default_params()

    def objective(trial):
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'verbosity': -1,
            'n_estimators': trial.suggest_int('n_estimators', 100, 500),
            'num_leaves': trial.suggest_int('num_leaves', 15, 63),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
            'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
            'bagging_freq': trial.suggest_int('bagging_freq', 1, 10),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            'class_weight': 'balanced',
        }

        # Cross-validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        model = lgb.LGBMClassifier(**params)

        scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc', n_jobs=-1)
        return scores.mean()

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    print(f"\n  Best AUC: {study.best_value:.4f}")
    print(f"  Best params: {study.best_params}")

    # Return best params with defaults
    best_params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'verbosity': -1,
        'class_weight': 'balanced',
        **study.best_params
    }

    return best_params


def get_default_params() -> Dict:
    """Get default LightGBM parameters"""
    return {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'n_estimators': 200,
        'class_weight': 'balanced',
        'verbosity': -1,
    }


# =============================================================================
# MODEL TRAINING
# =============================================================================

def train_model(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: List[str],
    params: Dict,
    test_size: float = 0.2
) -> Tuple[lgb.LGBMClassifier, Dict]:
    """
    Train the final model with given parameters
    """
    print("\nTraining final model...")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    print(f"  Train: {len(X_train)} samples")
    print(f"  Test: {len(X_test)} samples")

    # Train model
    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        eval_metric='auc',
    )

    # Predictions
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Metrics
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1': f1_score(y_test, y_pred, zero_division=0),
        'auc': roc_auc_score(y_test, y_prob),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
    }

    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')
    metrics['cv_auc_mean'] = cv_scores.mean()
    metrics['cv_auc_std'] = cv_scores.std()

    print(f"\n  Test Metrics:")
    print(f"    Accuracy: {metrics['accuracy']:.2%}")
    print(f"    Precision: {metrics['precision']:.2%}")
    print(f"    Recall: {metrics['recall']:.2%}")
    print(f"    F1: {metrics['f1']:.2%}")
    print(f"    AUC: {metrics['auc']:.4f}")
    print(f"    CV AUC: {metrics['cv_auc_mean']:.4f} ± {metrics['cv_auc_std']:.4f}")

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print(f"\n  Confusion Matrix:")
    print(f"    TN: {cm[0,0]}, FP: {cm[0,1]}")
    print(f"    FN: {cm[1,0]}, TP: {cm[1,1]}")

    return model, metrics


def analyze_feature_importance(model: lgb.LGBMClassifier, feature_names: List[str]) -> pd.DataFrame:
    """
    Analyze and display feature importance
    """
    print("\nFeature Importance (Top 20):")

    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    for i, row in importance_df.head(20).iterrows():
        bar = '█' * int(row['importance'] / importance_df['importance'].max() * 30)
        print(f"  {row['feature']:25s} {bar} {row['importance']:.0f}")

    return importance_df


# =============================================================================
# THRESHOLD CALIBRATION
# =============================================================================

def calibrate_thresholds(
    model: lgb.LGBMClassifier,
    X: np.ndarray,
    y: np.ndarray,
    target_precision: float = 0.75
) -> Dict[str, float]:
    """
    Calibrate decision thresholds based on desired precision
    """
    print(f"\nCalibrating thresholds for target precision {target_precision:.0%}...")

    # Get probabilities
    y_prob = model.predict_proba(X)[:, 1]

    # Find threshold for target precision
    thresholds_to_try = np.arange(0.3, 0.8, 0.01)
    best_trade_threshold = 0.5
    best_watch_threshold = 0.35

    for thresh in thresholds_to_try:
        y_pred = (y_prob >= thresh).astype(int)
        if y_pred.sum() == 0:
            continue
        precision = precision_score(y, y_pred, zero_division=0)
        if precision >= target_precision:
            best_trade_threshold = thresh
            break

    # Calculate metrics at best threshold
    y_pred = (y_prob >= best_trade_threshold).astype(int)
    precision = precision_score(y, y_pred, zero_division=0)
    recall = recall_score(y, y_pred, zero_division=0)
    trades = y_pred.sum()

    print(f"  TRADE threshold: {best_trade_threshold:.2f}")
    print(f"    Precision: {precision:.2%}")
    print(f"    Recall: {recall:.2%}")
    print(f"    Trades selected: {trades}/{len(y)} ({trades/len(y)*100:.1f}%)")

    # Watch threshold (lower)
    best_watch_threshold = best_trade_threshold - 0.15

    return {
        'trade': best_trade_threshold,
        'watch': best_watch_threshold,
        'skip': 0.0
    }


# =============================================================================
# SAVE MODEL
# =============================================================================

def save_model(
    model: lgb.LGBMClassifier,
    feature_names: List[str],
    metrics: Dict,
    thresholds: Dict,
    params: Dict
) -> str:
    """
    Save the trained model with metadata
    """
    import pickle

    # Get version from training_metadata.json
    metadata_path = MODEL_DIR / "training_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        version_parts = metadata.get('model_version', '2.0.0').split('.')
        new_version = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"
    else:
        new_version = "3.0.0"

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_path = MODEL_DIR / f"model_{new_version}_{timestamp}.pkl"

    # Save model
    data = {
        'model': model,
        'feature_names': feature_names,
        'version': new_version,
        'trained_at': datetime.now(),
        'metrics': metrics,
        'thresholds': thresholds,
        'params': params,
    }

    with open(model_path, 'wb') as f:
        pickle.dump(data, f)

    # Save metadata JSON
    meta_path = str(model_path).replace('.pkl', '_meta.json')
    with open(meta_path, 'w') as f:
        json.dump({
            'version': new_version,
            'trained_at': str(datetime.now()),
            'metrics': metrics,
            'thresholds': thresholds,
            'params': {k: str(v) for k, v in params.items()},
            'feature_names': feature_names,
        }, f, indent=2)

    # Update global metadata
    with open(metadata_path, 'w') as f:
        json.dump({
            'last_trained_at': datetime.now().isoformat(),
            'last_trained_outcomes_count': metrics.get('train_samples', 0) + metrics.get('test_samples', 0),
            'model_version': new_version,
            'total_retrains': metadata.get('total_retrains', 0) + 1 if metadata_path.exists() else 1,
            'last_auc': metrics.get('auc', 0),
            'last_cv_auc': metrics.get('cv_auc_mean', 0),
            'thresholds': thresholds,
        }, f, indent=2)

    print(f"\n✅ Model saved: {model_path}")
    print(f"   Version: {new_version}")

    return str(model_path)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("MEGA BUY AI - ML Model Retraining v2.0")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")

    # 1. Load data
    alerts, outcomes = load_data()

    # 2. Prepare features
    X, y, feature_names = prepare_features(alerts, outcomes)

    if len(X) < 100:
        print("ERROR: Not enough samples for training")
        return

    # 3. Optimize hyperparameters
    try:
        params = optimize_hyperparameters(X, y, n_trials=30)
    except Exception as e:
        print(f"Optimization failed: {e}, using defaults")
        params = get_default_params()

    # 4. Train model
    model, metrics = train_model(X, y, feature_names, params)

    # 5. Analyze feature importance
    importance_df = analyze_feature_importance(model, feature_names)

    # 6. Calibrate thresholds
    thresholds = calibrate_thresholds(model, X, y, target_precision=0.73)

    # 7. Save model
    model_path = save_model(model, feature_names, metrics, thresholds, params)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Model: {model_path}")
    print(f"  AUC: {metrics['auc']:.4f}")
    print(f"  CV AUC: {metrics['cv_auc_mean']:.4f}")
    print(f"  Thresholds: TRADE >= {thresholds['trade']:.2f}, WATCH >= {thresholds['watch']:.2f}")
    print(f"  Finished at: {datetime.now()}")

    return model_path


if __name__ == "__main__":
    main()
