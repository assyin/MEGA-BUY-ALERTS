# MEGA BUY BOT — Référence des sauvegardes

> Ce fichier liste les sauvegardes complètes du projet et explique comment les restaurer.
> Mis à jour à chaque nouvelle sauvegarde.

---

## 📦 Sauvegarde la plus récente

**`full_20260428_123410/`** — 2026-04-28 13:30 UTC

| Fichier | Taille | Contenu |
|---|---|---|
| `code_and_data.tar.gz` | 690 MB | 43 056 fichiers : code Python + PineScript + dashboard src + scripts/ analytics, configs (`.env`, `google_creds.json`, `golden_boxes.json`), logs, charts OpenClaw, mémoires, reports, audit reports V11B/HTML |
| `databases.tar.gz` | 4.8 MB | Snapshots SQLite compressés |
| `databases/backtest.db` | 62 MB | Snapshot chaud (`sqlite3.backup` API) — `backtest_runs=796`, `alerts=678`, `trades=16` |
| `databases/simulation.db` | 19 MB | Snapshot chaud — `alerts=8303`, `portfolios=13`, `positions=197`, `balance_history=65079`, `ignored_positions=987` |
| `supabase/supabase_tables_20260428_123410.tar.gz` | 6.4 MB | Exports REST NDJSON (gzip) — 42 tables, **23 059 lignes** |
| `supabase/tables/` | 6.6 MB | Mêmes exports en clair (1 fichier `.ndjson.gz` par table) |
| `supabase/tables_manifest.json` | 4 KB | Stats par table (rows / size / elapsed) |
| `MANIFEST.txt` | 4 KB | Inventaire avec sha256 des archives + DB stats + git HEAD |

**Total : ~700 MB** • Intégrité SQLite : `integrity=ok` ✅ • Supabase REST exports : 42/42 tables ✅
**Git HEAD** : `3574ab6` — `feat(openclaw): show PENDING count next to W/L in WR Resolu badge`

### ⚠️ Différence vs backup précédent (2026-04-08)

Cette sauvegarde **n'utilise PAS `pg_dump`** mais des exports REST/NDJSON via le service key. Raison :
- `pg_dump 17.9` était dans `/tmp/pg17/extracted/` (volatile, perdu au reboot)
- Le mot de passe DB Postgres n'est pas dans `.env` (vit dans le dashboard Supabase)

**Conséquence pratique** :
- ✅ Les **données** (rows) sont bien sauvegardées (NDJSON par table)
- ❌ Le **schéma** (CREATE TABLE, indexes, triggers, RLS policies) **N'est PAS** sauvegardé — il faut s'appuyer sur le dump du `2026-04-08` ou les migrations en code pour reconstruire le schéma
- 🔁 Pour restaurer : le schéma doit déjà exister dans la cible, puis `INSERT ON CONFLICT` ou upsert via Supabase client à partir des NDJSON

**Pour la prochaine sauvegarde** : re-télécharger `pg_dump 17.9` et récupérer le password Supabase (dashboard → Project Settings → Database) pour repartir sur un dump complet schéma+data.

### Détails des exports Supabase (NDJSON)

- **Source** : `https://ejpfmquebcmwurdptqxi.supabase.co` (REST `/rest/v1/<table>?select=*`, paginé 1000 rows)
- **Auth** : `SUPABASE_SERVICE_KEY` depuis `python/.env` (service role, bypass RLS)
- **Tables principales** : `alerts` (10 239), `agent_memory` (5 013), `decisions` (2 457), `outcomes` (2 265), `agent_insights` (957), `openclaw_reports` (738), `openclaw_positions` (237), `openclaw_positions_v11b` (211), `openclaw_positions_v11e` (116), `openclaw_positions_v11d` (68), `openclaw_positions_v11c` (49), `openclaw_positions_v11a` (17), legacy V2-V9 positions (581 total), `agent_conversations` (75), `openclaw_engagements` (18), states v2-v11 + base
- **Format** : 1 fichier par table `tables/<name>.ndjson.gz` (1 row JSON par ligne)
- **Vue exclue** : `v_alerts_complete` (vue dérivée, reconstructible)

---

## 📦 Sauvegarde précédente

**`full_20260408_134312/`** — 2026-04-08 13:43 + 14:55 (Supabase ajouté)

| Fichier | Taille | Contenu |
|---|---|---|
| `code_and_data.tar.gz` | 300 MB | 7298 fichiers : code Python + PineScript + dashboard src, configs |
| `databases.tar.gz` | 4.1 MB | Snapshots SQLite compressés |
| `databases/backtest.db` | 62 MB | Snapshot chaud — `backtest_runs=416`, `alerts=1214`, `trades=45` |
| `databases/simulation.db` | 11 MB | Snapshot chaud — `alerts=5063`, `portfolios=13`, `positions=158`, `balance_history=30747`, `ignored_positions=981` |
| `databases/backtest-old-20260226.db` | 0.3 MB | Re-snapshot de l'ancien backup Feb |
| `supabase/supabase_public_20260408_145548.dump` | 3.5 MB | `pg_dump` custom format — schéma `public`, 28 tables, ~15K lignes |
| `supabase/supabase_public_20260408_145548.sql.gz` | 3.5 MB | Même contenu en SQL plain texte (gzip) |
| `supabase/supabase_auth_20260408_145548.dump` | 83 KB | Schéma `auth` (utilisateurs Supabase Auth) |

**Total : ~311 MB** • Reste utile pour récupérer le **schéma SQL** Supabase (DDL).

---

## 🗂️ Historique des sauvegardes (dossier `backups/`)

| Date | Nom | Type |
|---|---|---|
| 2026-04-28 | `full_20260428_123410/` | **Full** (code + data + DBs + Supabase NDJSON) ⭐ actuelle |
| 2026-04-08 | `full_20260408_134312/` | Full (avec `pg_dump` schéma+data) — référence schéma SQL |
| 2026-03-19 | `full_backup_20260319_092938.json` + `alerts_backup_*.json` + `decisions_backup_*.json` + `outcomes_backup_*.json` | JSON exports (Supabase tables) |
| 2026-03-12 | `mega-buy-ai_backup_20260312_103226.tar.gz` | Tarball mega-buy-ai |
| 2026-02-28 | `backup_20260228_082759.tar.gz` | Tarball complet |
| 2026-02-26 | `mega-buy-ai-backup-20260226-153328.tar.gz` + `backtest-20260226-153328.db` | Tarball + DB |

---

## ✅ Ce qui est inclus

- **Code source complet** : `python/`, `mega-buy-ai/`, `pinescript/`, `scripts/`, `dashboard/src/`
- **Configurations** : `python/.env`, `python/google_creds.json`, `python/golden_boxes.json`
- **Données locales** : 
  - `mega-buy-ai/openclaw/data/` (charts, reports, token_usage)
  - `mega-buy-ai/openclaw/memory/`
  - `mega-buy-ai/data/simulation.db` (via snapshot chaud)
  - `mega-buy-ai/backtest/data/backtest.db` (via snapshot chaud)
- **Logs** : `python/logs/`

## 🚫 Ce qui n'est PAS inclus

### Volontairement exclus (reproductibles)
- `node_modules/`, `mega-buy-ai/dashboard/node_modules/` → `npm install`
- `mega-buy-ai/dashboard/.next/` → `npm run build`
- `python/venv/` → `python3 -m venv venv && pip install -r requirements.txt`
- `.git/` → `git clone` du remote
- `**/__pycache__/`, `**/*.pyc`

### Données distantes
- ✅ **Supabase cloud DB** : **MAINTENANT INCLUS** depuis 2026-04-08 14:55 (voir section ci-dessus)
  - Connexion : pooler `aws-1-eu-west-1.pooler.supabase.com:5432`, user `postgres.ejpfmquebcmwurdptqxi`
  - Mot de passe DB : **PAS dans `.env`** — à récupérer depuis https://supabase.com/dashboard/project/ejpfmquebcmwurdptqxi/settings/database
- ❌ **Google Sheets** : accès live via API, pas de copie locale. À exporter via script gspread si besoin d'archive.

---

## 🔧 Comment restaurer

### 1. Restaurer le code et les données
```bash
cd /home/assyin/MEGA-BUY-BOT
tar -xzf backups/full_20260428_123410/code_and_data.tar.gz
```

### 2. Restaurer les bases SQLite
```bash
# IMPORTANT : arrêter d'abord les services qui utilisent les DBs
pm2 stop mega-backtest mega-simulation

cp backups/full_20260428_123410/databases/backtest.db   mega-buy-ai/backtest/data/backtest.db
cp backups/full_20260428_123410/databases/simulation.db mega-buy-ai/data/simulation.db

pm2 restart mega-backtest mega-simulation
```

### 2-bis. Restaurer la base Supabase (NDJSON exports — backup 2026-04-28)

⚠️ Ce backup contient **uniquement les données** (NDJSON par table), pas le schéma SQL. Le schéma doit déjà exister dans la cible — soit il y est déjà, soit utilise le dump SQL du backup `full_20260408_134312/` pour le recréer d'abord.

```bash
# Restaure une table donnée (ex: alerts) via upsert avec le client Supabase
python3 - <<'PY'
import gzip, json, sys
sys.path.insert(0, "mega-buy-ai")
from openclaw.config import get_settings
from supabase import create_client
s = get_settings()
sb = create_client(s.supabase_url, s.supabase_service_key)

table = "alerts"  # à changer selon la table à restaurer
path = f"backups/full_20260428_123410/supabase/tables/{table}.ndjson.gz"
batch = []
with gzip.open(path, "rt", encoding="utf-8") as f:
    for line in f:
        batch.append(json.loads(line))
        if len(batch) >= 500:
            sb.table(table).upsert(batch).execute()
            batch = []
    if batch:
        sb.table(table).upsert(batch).execute()
print(f"Restored {table}")
PY
```

### 2-ter. Restaurer Supabase via `pg_restore` (backup 2026-04-08, conserve schéma+data)

```bash
# Le pg_dump custom format se restaure avec pg_restore (>= 17, Supabase est en pg17)
# Si pas installé : télécharger depuis PGDG (cf. procédure du 08/04)

PGRESTORE=/tmp/pg17/extracted/usr/lib/postgresql/17/bin/pg_restore
PGPASSWORD='<DB_PASSWORD>' "$PGRESTORE" \
  -h aws-1-eu-west-1.pooler.supabase.com -p 5432 \
  -U postgres.ejpfmquebcmwurdptqxi -d postgres \
  --no-owner --no-acl --clean --if-exists \
  backups/full_20260408_134312/supabase/supabase_public_20260408_145548.dump
```

⚠️ **Restauration destructive** : `--clean --if-exists` supprime les tables existantes avant de restaurer.

Pour restaurer dans une **autre base** (ex: instance Supabase locale ou nouvelle), changer juste `-h/-U/-d`.

### 3. Reconstruire les dépendances (si restauration fraîche)
```bash
# Python
cd python && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Dashboard Next.js
cd mega-buy-ai/dashboard && npm install && npm run build
```

### 4. Vérifier l'intégrité d'une DB après restore
```bash
python3 -c "import sqlite3; print(sqlite3.connect('mega-buy-ai/backtest/data/backtest.db').execute('PRAGMA integrity_check').fetchone()[0])"
```

---

## 🆕 Comment créer une nouvelle sauvegarde

Procédure utilisée pour `full_20260428_123410` :

0. **Snapshot Supabase via REST/NDJSON** (fallback quand pg_dump indispo) :
   - Découvre les tables via `GET <SUPABASE_URL>/rest/v1/` → `definitions` du spec OpenAPI
   - Pour chaque table : `sb.table(t).select("*").range(cursor, cursor+999).execute()` paginé jusqu'à épuisement
   - Écrire chaque row en NDJSON dans `tables/<t>.ndjson.gz` (gzip), puis `tar.czf supabase_tables_TS.tar.gz tables/`
   - **Inconvénient** : pas de schéma DDL. Combiner avec un dump SQL (cf. backup 2026-04-08) si possible.

Sinon, procédure complète historique (2026-04-08) :

1. **Snapshot chaud des DBs SQLite** (sûr même si les services tournent — utilise l'API `.backup` de SQLite, pas `cp`) :
   ```python
   import sqlite3
   src = sqlite3.connect("file:mega-buy-ai/backtest/data/backtest.db?mode=ro", uri=True)
   dst = sqlite3.connect("backups/full_TIMESTAMP/databases/backtest.db")
   with dst: src.backup(dst)
   ```

2. **Tar.gz du projet** en excluant les fichiers reproductibles :
   ```bash
   tar --exclude='./node_modules' \
       --exclude='./mega-buy-ai/dashboard/node_modules' \
       --exclude='./mega-buy-ai/dashboard/.next' \
       --exclude='./python/venv' \
       --exclude='./.git' \
       --exclude='./backups' \
       --exclude='**/__pycache__' \
       --exclude='**/*.pyc' \
       --exclude='./mega-buy-ai/backtest/data/backtest.db' \
       --exclude='./mega-buy-ai/data/simulation.db' \
       -czf backups/full_TIMESTAMP/code_and_data.tar.gz .
   ```

3. **Vérifier l'intégrité** des DBs snapshotées avec `PRAGMA integrity_check`.

4. **Mettre à jour ce fichier** (`BACKUP_REFERENCE.md`) avec la nouvelle entrée.

---

## ℹ️ Notes importantes

- **Les DBs SQLite ne doivent JAMAIS être copiées avec `cp`** pendant que les services PM2 tournent — risque de corruption. Toujours utiliser `sqlite3.backup()` ou arrêter les services d'abord.
- **`python/.env` contient des secrets** (Telegram token, Supabase keys, OpenAI key, Anthropic key) — la sauvegarde les inclut. Ne pas pousser cette archive sur un dépôt public.
- **`google_creds.json`** est un service account Google — même règle, secret.
- **Supabase est la source de vérité** pour les alertes/décisions/mémoires. Une sauvegarde locale ne protège PAS contre une perte Supabase. Faire un dump Supabase régulier en parallèle.
