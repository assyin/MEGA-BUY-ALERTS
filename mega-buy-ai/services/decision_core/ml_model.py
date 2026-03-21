"""
MEGA BUY AI - ML Decision Core
Modèle LightGBM pour prédiction de succès des alertes
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path

try:
    import lightgbm as lgb
    LIGHTGBM_OK = True
except ImportError:
    LIGHTGBM_OK = False
    print("WARNING: lightgbm not installed. Run: pip install lightgbm")

try:
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    SKLEARN_OK = True
except ImportError:
    SKLEARN_OK = False
    print("WARNING: sklearn not installed. Run: pip install scikit-learn")

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.feature_engineering.features import (
    compute_full_features,
    get_feature_names,
    features_to_vector,
    label_alert_outcome
)

# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_DIR = Path(__file__).parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

DEFAULT_PARAMS = {
    "objective": "binary",
    "metric": "auc",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "n_estimators": 200,
    "early_stopping_rounds": 20,
    "class_weight": "balanced",  # Gère le déséquilibre de classes
    "is_unbalance": True,
}

# Seuils de décision (basés sur l'analyse des données)
# Note: Le ML seul ne différencie pas bien, on utilise des règles combinées
THRESHOLDS = {
    "trade": 0.50,      # p_success >= 50% → TRADE (plus sélectif)
    "watch": 0.35,      # p_success >= 35% → WATCH
    "skip": 0.0,        # sinon → SKIP
}

# Règles métier prioritaires (basées sur analyse empirique)
# - 4H présent = 75% de succès → TRADE
# - 2+ timeframes = 42% de succès → WATCH minimum
# - 1 TF sans 4H = 27% → évaluer avec ML
RULE_WEIGHTS = {
    "has_4h": 0.25,           # +25% si 4H présent
    "multi_tf": 0.10,         # +10% si 2+ timeframes
    "high_score": 0.05,       # +5% si score >= 8
}

# =============================================================================
# FILTER-BASED RULES (empirically validated - March 2026)
# =============================================================================
# Based on analysis of 2076 trades:
# - filter_big_winners (DI-≥22, DI+≤25, ADX≥21, Vol≥100%): 73% WR, keeps 92% big winners
# - filter_balanced (DI-≥22, DI+≤20, ADX≥21, Vol≥100%): 75% WR, keeps 67% big winners
# - filter_max_wr (DI-≥22, DI+≤25, ADX≥35, Vol≥100%): 77% WR, but very selective

FILTER_RULES = {
    # Boost rules (increase p_success)
    "filter_big_winners": {"boost": 0.15, "action": "boost"},   # +15% if passes big winners filter
    "filter_balanced": {"boost": 0.10, "action": "boost"},      # +10% if passes balanced filter
    "filter_max_wr": {"boost": 0.20, "action": "boost"},        # +20% if passes max WR filter

    # Penalty rules (decrease p_success or downgrade)
    "low_di_minus": {"threshold": 16, "penalty": 0.10},         # -10% if DI- < 16
    "high_di_plus": {"threshold": 30, "penalty": 0.05},         # -5% if DI+ > 30
    "no_pp_ec": {"penalty": 0.15},                               # -15% if PP=False OR EC=False
    "low_vol": {"threshold": 100, "penalty": 0.10},             # -10% if Vol < 100%
}


class MegaBuyMLModel:
    """Modèle ML pour prédiction des alertes MEGA BUY"""

    def __init__(self, model_path: str = None):
        """
        Initialise le modèle

        Args:
            model_path: Chemin vers un modèle sauvegardé (optionnel)
        """
        if not LIGHTGBM_OK:
            raise ImportError("lightgbm is required")

        self.model: Optional[lgb.LGBMClassifier] = None
        self.feature_names: List[str] = get_feature_names()
        self.version = "1.0.0"
        self.trained_at: Optional[datetime] = None
        self.metrics: Dict[str, float] = {}

        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str] = None,
        params: Dict = None,
        test_size: float = 0.2
    ) -> Dict[str, float]:
        """
        Entraîne le modèle

        Args:
            X: Features (n_samples, n_features)
            y: Labels (0 ou 1)
            feature_names: Noms des features
            params: Paramètres LightGBM
            test_size: Proportion pour validation

        Returns:
            Dict de métriques
        """
        if feature_names:
            self.feature_names = feature_names

        # Paramètres
        model_params = DEFAULT_PARAMS.copy()
        if params:
            model_params.update(params)

        # Split train/val
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        print(f"Training set: {len(X_train)} samples")
        print(f"Validation set: {len(X_val)} samples")
        print(f"Positive ratio: {y.mean():.2%}")

        # Créer le modèle
        self.model = lgb.LGBMClassifier(**model_params)

        # Entraîner avec early stopping
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            eval_metric="auc",
        )

        # Prédictions sur validation
        y_pred = self.model.predict(X_val)
        y_prob = self.model.predict_proba(X_val)[:, 1]

        # Métriques
        self.metrics = {
            "accuracy": accuracy_score(y_val, y_pred),
            "precision": precision_score(y_val, y_pred, zero_division=0),
            "recall": recall_score(y_val, y_pred, zero_division=0),
            "f1": f1_score(y_val, y_pred, zero_division=0),
            "auc": roc_auc_score(y_val, y_prob),
            "train_samples": len(X_train),
            "val_samples": len(X_val),
        }

        self.trained_at = datetime.now()

        print(f"\nTraining complete!")
        print(f"  Accuracy: {self.metrics['accuracy']:.2%}")
        print(f"  Precision: {self.metrics['precision']:.2%}")
        print(f"  Recall: {self.metrics['recall']:.2%}")
        print(f"  F1: {self.metrics['f1']:.2%}")
        print(f"  AUC: {self.metrics['auc']:.2%}")

        return self.metrics

    def predict(self, features: Dict[str, float], alert_data: Dict = None) -> Dict[str, Any]:
        """
        Prédit pour une alerte avec règles métier

        Args:
            features: Dict de features
            alert_data: Dict optionnel avec timeframes, score, etc.

        Returns:
            Dict avec p_success, decision, confidence, etc.
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")

        # Convertir en vecteur
        X = features_to_vector(features, self.feature_names).reshape(1, -1)

        # Prédiction ML de base
        p_ml = float(self.model.predict_proba(X)[0, 1])

        # Appliquer les règles métier (boosters)
        p_success = p_ml
        rules_applied = []

        if alert_data:
            timeframes = alert_data.get("timeframes", [])
            score = alert_data.get("score", 0)

            # Règle 1: 4H présent = très bon signal (+25%)
            if "4h" in timeframes:
                p_success += RULE_WEIGHTS["has_4h"]
                rules_applied.append("has_4h")

            # Règle 2: Multi-timeframes = confirmation (+10%)
            if len(timeframes) >= 2:
                p_success += RULE_WEIGHTS["multi_tf"]
                rules_applied.append("multi_tf")

            # Règle 3: Score élevé (+5%)
            if score >= 8:
                p_success += RULE_WEIGHTS["high_score"]
                rules_applied.append("high_score")

        # Limiter à [0, 1]
        p_success = min(max(p_success, 0), 1)

        # Décision basée sur seuils ajustés
        if p_success >= THRESHOLDS["trade"]:
            decision = "TRADE"
            confidence = (p_success - THRESHOLDS["trade"]) / (1 - THRESHOLDS["trade"])
        elif p_success >= THRESHOLDS["watch"]:
            decision = "WATCH"
            confidence = (p_success - THRESHOLDS["watch"]) / (THRESHOLDS["trade"] - THRESHOLDS["watch"])
        else:
            decision = "SKIP"
            confidence = 1 - (p_success / THRESHOLDS["watch"]) if THRESHOLDS["watch"] > 0 else 1

        confidence = min(max(confidence, 0), 1)

        # Feature importance pour cette prédiction
        importances = self.model.feature_importances_
        top_indices = np.argsort(importances)[-5:][::-1]
        top_features = [
            {
                "name": self.feature_names[i],
                "importance": float(importances[i]),
                "value": float(features.get(self.feature_names[i], 0))
            }
            for i in top_indices
        ]

        return {
            "p_success": p_success,
            "p_ml": p_ml,
            "decision": decision,
            "confidence": confidence,
            "rules_applied": rules_applied,
            "top_features": top_features,
            "model_version": self.version,
        }

    def predict_batch(self, features_list: List[Dict], alerts_data: List[Dict] = None) -> List[Dict]:
        """Prédit pour plusieurs alertes"""
        if alerts_data:
            return [self.predict(f, a) for f, a in zip(features_list, alerts_data)]
        return [self.predict(f) for f in features_list]

    def get_feature_importance(self) -> pd.DataFrame:
        """Retourne l'importance des features"""
        if self.model is None:
            return pd.DataFrame()

        importance = pd.DataFrame({
            "feature": self.feature_names,
            "importance": self.model.feature_importances_
        }).sort_values("importance", ascending=False)

        return importance

    def save(self, path: str = None) -> str:
        """
        Sauvegarde le modèle

        Args:
            path: Chemin de sauvegarde

        Returns:
            Chemin du fichier sauvegardé
        """
        if path is None:
            path = MODEL_DIR / f"model_{self.version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        data = {
            "model": self.model,
            "feature_names": self.feature_names,
            "version": self.version,
            "trained_at": self.trained_at,
            "metrics": self.metrics,
        }

        with open(path, "wb") as f:
            pickle.dump(data, f)

        # Sauvegarder aussi les métadonnées en JSON
        meta_path = str(path).replace(".pkl", "_meta.json")
        with open(meta_path, "w") as f:
            json.dump({
                "version": self.version,
                "trained_at": str(self.trained_at),
                "metrics": self.metrics,
                "feature_names": self.feature_names,
            }, f, indent=2)

        print(f"Model saved to {path}")
        return str(path)

    def load(self, path: str) -> None:
        """
        Charge un modèle sauvegardé

        Args:
            path: Chemin du fichier
        """
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.model = data["model"]
        self.feature_names = data["feature_names"]
        self.version = data["version"]
        self.trained_at = data.get("trained_at")
        self.metrics = data.get("metrics", {})

        print(f"Model loaded from {path}")
        print(f"  Version: {self.version}")
        print(f"  Trained at: {self.trained_at}")


class RulesEngine:
    """Moteur de règles pour garde-fous risk"""

    def __init__(self):
        self.rules = []
        self.boost_rules = []  # Règles qui augmentent p_success
        self.penalty_rules = []  # Règles qui diminuent p_success
        self._init_default_rules()
        self._init_filter_rules()

    def _init_default_rules(self):
        """Initialise les règles par défaut"""
        # Règle: Volatilité trop élevée
        self.add_rule(
            name="high_volatility",
            condition=lambda f: f.get("volatility_24h", 0) > 15,
            action="downgrade",
            reason="Volatilité 24h trop élevée (>15%)"
        )

        # Règle: RSI extrême (surachat)
        self.add_rule(
            name="rsi_overbought",
            condition=lambda f: f.get("rsi_4h", 50) > 80,
            action="warning",
            reason="RSI en zone de surachat (>80)"
        )

        # Règle: Volume trop faible
        self.add_rule(
            name="low_volume",
            condition=lambda f: f.get("volume_ratio", 1) < 0.5,
            action="warning",
            reason="Volume inférieur à 50% de la moyenne"
        )

        # Règle: Score scanner faible
        self.add_rule(
            name="low_score",
            condition=lambda f: f.get("scanner_score", 0) < 6,
            action="skip",
            reason="Score scanner trop faible (<6)"
        )

        # Règle: Pas de conditions DMI
        self.add_rule(
            name="no_dmi",
            condition=lambda f: not f.get("dmi_check", False),
            action="warning",
            reason="Condition DMI non validée"
        )

    def _init_filter_rules(self):
        """Initialise les règles basées sur les filtres empiriques"""
        # === BOOST RULES (augmentent p_success) ===

        # Filter Big Winners: 73% WR, garde 92% des gros gagnants
        self.add_boost_rule(
            name="filter_big_winners",
            condition=lambda f: f.get("filter_big_winners", 0) == 1.0,
            boost=0.15,
            reason="Passe le filtre Big Winners (DI-≥22, DI+≤25, ADX≥21, Vol≥100%)"
        )

        # Filter Balanced: 75% WR
        self.add_boost_rule(
            name="filter_balanced",
            condition=lambda f: f.get("filter_balanced", 0) == 1.0,
            boost=0.10,
            reason="Passe le filtre Balanced (DI-≥22, DI+≤20, ADX≥21, Vol≥100%)"
        )

        # Filter Max WR: 77% WR
        self.add_boost_rule(
            name="filter_max_wr",
            condition=lambda f: f.get("filter_max_wr", 0) == 1.0,
            boost=0.20,
            reason="Passe le filtre Max WR (DI-≥22, DI+≤25, ADX≥35, Vol≥100%)"
        )

        # === PENALTY RULES (diminuent p_success) ===

        # DI- trop faible (< 16) = signal faible
        self.add_penalty_rule(
            name="very_low_di_minus",
            condition=lambda f: f.get("di_minus_4h", 0) < 16,
            penalty=0.10,
            reason="DI- trop faible (<16) - momentum vendeur insuffisant"
        )

        # DI+ trop élevé (> 30) = potentiellement surachat
        self.add_penalty_rule(
            name="high_di_plus",
            condition=lambda f: f.get("di_plus_4h", 0) > 30,
            penalty=0.05,
            reason="DI+ élevé (>30) - risque de surachat"
        )

        # Pas de PP ou EC = signal incomplet
        self.add_penalty_rule(
            name="no_pp_ec",
            condition=lambda f: f.get("pp", 0) != 1.0 or f.get("ec", 0) != 1.0,
            penalty=0.15,
            reason="PP ou EC manquant - signal incomplet"
        )

        # Volume faible (< 100%)
        self.add_penalty_rule(
            name="low_vol_pct",
            condition=lambda f: f.get("vol_pct_max", 0) < 100,
            penalty=0.10,
            reason="Volume < 100% - faible intérêt du marché"
        )

    def add_boost_rule(
        self,
        name: str,
        condition: callable,
        boost: float,
        reason: str
    ):
        """Ajoute une règle de boost (augmente p_success)"""
        self.boost_rules.append({
            "name": name,
            "condition": condition,
            "boost": boost,
            "reason": reason
        })

    def add_penalty_rule(
        self,
        name: str,
        condition: callable,
        penalty: float,
        reason: str
    ):
        """Ajoute une règle de pénalité (diminue p_success)"""
        self.penalty_rules.append({
            "name": name,
            "condition": condition,
            "penalty": penalty,
            "reason": reason
        })

    def add_rule(
        self,
        name: str,
        condition: callable,
        action: str,
        reason: str
    ):
        """
        Ajoute une règle

        Args:
            name: Nom de la règle
            condition: Fonction qui retourne True si la règle est déclenchée
            action: "skip", "downgrade", "warning"
            reason: Raison explicative
        """
        self.rules.append({
            "name": name,
            "condition": condition,
            "action": action,
            "reason": reason
        })

    def apply(self, features: Dict, decision: Dict) -> Dict:
        """
        Applique les règles à une décision

        Args:
            features: Features de l'alerte
            decision: Décision du modèle ML

        Returns:
            Décision modifiée avec règles appliquées
        """
        result = decision.copy()
        triggered = []
        boosts_applied = []
        penalties_applied = []

        # === 1. Apply boost rules first (increase p_success) ===
        p_success = result.get("p_success", 0.5)

        for rule in self.boost_rules:
            try:
                if rule["condition"](features):
                    boosts_applied.append({
                        "name": rule["name"],
                        "boost": rule["boost"],
                        "reason": rule["reason"]
                    })
                    p_success += rule["boost"]
            except Exception as e:
                print(f"Boost rule {rule['name']} error: {e}")

        # === 2. Apply penalty rules (decrease p_success) ===
        for rule in self.penalty_rules:
            try:
                if rule["condition"](features):
                    penalties_applied.append({
                        "name": rule["name"],
                        "penalty": rule["penalty"],
                        "reason": rule["reason"]
                    })
                    p_success -= rule["penalty"]
            except Exception as e:
                print(f"Penalty rule {rule['name']} error: {e}")

        # Clamp p_success to [0, 1]
        p_success = max(0, min(1, p_success))
        result["p_success"] = p_success

        # === 3. Re-calculate decision based on adjusted p_success ===
        if p_success >= THRESHOLDS["trade"]:
            result["decision"] = "TRADE"
            result["confidence"] = (p_success - THRESHOLDS["trade"]) / (1 - THRESHOLDS["trade"])
        elif p_success >= THRESHOLDS["watch"]:
            result["decision"] = "WATCH"
            result["confidence"] = (p_success - THRESHOLDS["watch"]) / (THRESHOLDS["trade"] - THRESHOLDS["watch"])
        else:
            result["decision"] = "SKIP"
            result["confidence"] = 1 - (p_success / THRESHOLDS["watch"]) if THRESHOLDS["watch"] > 0 else 1

        result["confidence"] = max(0, min(1, result["confidence"]))

        # === 4. Apply hard rules (can override decision) ===
        for rule in self.rules:
            try:
                if rule["condition"](features):
                    triggered.append(rule["name"])

                    if rule["action"] == "skip":
                        result["decision"] = "SKIP"
                        result["confidence"] = 0.9
                    elif rule["action"] == "downgrade":
                        if result["decision"] == "TRADE":
                            result["decision"] = "WATCH"
                            result["confidence"] *= 0.8
                        elif result["decision"] == "WATCH":
                            result["decision"] = "SKIP"
                    # "warning" ne change pas la décision
            except Exception as e:
                print(f"Rule {rule['name']} error: {e}")

        # === 5. Store all applied rules for transparency ===
        result["rules_triggered"] = triggered
        result["boosts_applied"] = boosts_applied
        result["penalties_applied"] = penalties_applied
        result["total_boost"] = sum(b["boost"] for b in boosts_applied)
        result["total_penalty"] = sum(p["penalty"] for p in penalties_applied)

        return result


class DecisionCore:
    """Core de décision combinant ML + Rules"""

    def __init__(self, model_path: str = None):
        """
        Initialise le Decision Core

        Args:
            model_path: Chemin vers le modèle ML (optionnel)
        """
        self.ml_model = MegaBuyMLModel(model_path)
        self.rules_engine = RulesEngine()

    def decide(self, alert: Dict, include_market: bool = True) -> Dict:
        """
        Prend une décision pour une alerte

        Args:
            alert: Dictionnaire de l'alerte
            include_market: Inclure les données de marché

        Returns:
            Décision complète
        """
        import time
        start_time = time.time()

        # Calculer les features
        features = compute_full_features(alert, include_market)

        # Prédiction ML avec règles métier
        ml_decision = self.ml_model.predict(features, alert_data=alert)

        # Appliquer les règles supplémentaires
        final_decision = self.rules_engine.apply(features, ml_decision)

        # Calculer les zones d'entrée
        price = alert.get("price", 0)
        if price and price > 0:
            atr_pct = features.get("atr_pct", 2)
            final_decision["entry_zone_low"] = price * (1 - atr_pct / 100)
            final_decision["entry_zone_high"] = price * (1 + atr_pct / 200)
            final_decision["stop_loss"] = price * (1 - atr_pct * 1.5 / 100)
            final_decision["take_profit_1"] = price * (1 + atr_pct / 100)
            final_decision["take_profit_2"] = price * (1 + atr_pct * 2 / 100)
            final_decision["take_profit_3"] = price * (1 + atr_pct * 3 / 100)

        # Temps de traitement
        final_decision["processing_time_ms"] = int((time.time() - start_time) * 1000)
        final_decision["features"] = features

        return final_decision

    def train_model(self, alerts: List[Dict]) -> Dict:
        """
        Entraîne le modèle sur des alertes historiques

        Args:
            alerts: Liste d'alertes avec outcomes

        Returns:
            Métriques d'entraînement
        """
        print(f"Preparing training data from {len(alerts)} alerts...")

        X_list = []
        y_list = []
        feature_names = get_feature_names()

        for alert in alerts:
            # Label
            label = label_alert_outcome(alert)
            if label is None:
                continue

            # Features (sans appels API pour l'entraînement)
            try:
                features = compute_full_features(alert, include_market=False)
                X_list.append(features_to_vector(features, feature_names))
                y_list.append(label)
            except Exception as e:
                print(f"Error processing alert {alert.get('id')}: {e}")
                continue

        if len(X_list) < 50:
            raise ValueError(f"Not enough labeled samples: {len(X_list)}")

        X = np.array(X_list)
        y = np.array(y_list)

        print(f"Training with {len(X)} samples ({y.sum()} positive, {len(y) - y.sum()} negative)")

        metrics = self.ml_model.train(X, y, feature_names)

        # Sauvegarder le modèle
        self.ml_model.save()

        return metrics


# Singleton
_decision_core: Optional[DecisionCore] = None


def find_latest_model() -> Optional[str]:
    """Find the most recent model file in the models directory."""
    models_dir = Path(__file__).parent.parent.parent / "models"
    if not models_dir.exists():
        return None

    model_files = list(models_dir.glob("model_*.pkl"))
    if not model_files:
        return None

    # Sort by modification time (newest first)
    model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return str(model_files[0])


def get_decision_core(model_path: str = None) -> DecisionCore:
    """Retourne l'instance singleton du Decision Core"""
    global _decision_core
    if _decision_core is None:
        # Auto-load latest model if no path provided
        if model_path is None:
            model_path = find_latest_model()
            if model_path:
                print(f"Auto-loading model: {Path(model_path).name}")
        _decision_core = DecisionCore(model_path)
    return _decision_core


def reload_decision_core() -> DecisionCore:
    """Force reload the decision core with the latest model."""
    global _decision_core
    _decision_core = None
    return get_decision_core()
