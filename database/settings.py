"""SQLite-backed persistence for connection profiles and app settings."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "central_serial.db"


class SettingsStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._create_tables()

    def _create_tables(self):
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                name TEXT PRIMARY KEY,
                protocol TEXT NOT NULL,
                config TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def save_profile(self, name: str, protocol: str, config: dict):
        self._conn.execute(
            "INSERT INTO profiles (name, protocol, config, updated_at) VALUES (?, ?, ?, datetime('now')) "
            "ON CONFLICT(name) DO UPDATE SET protocol=excluded.protocol, config=excluded.config, "
            "updated_at=excluded.updated_at",
            (name, protocol, json.dumps(config)),
        )
        self._conn.commit()

    def load_profile(self, name: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT protocol, config FROM profiles WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        protocol, config_json = row
        return {"protocol": protocol, "config": json.loads(config_json)}

    def list_profiles(self) -> list[str]:
        rows = self._conn.execute("SELECT name FROM profiles ORDER BY name").fetchall()
        return [r[0] for r in rows]

    def delete_profile(self, name: str):
        self._conn.execute("DELETE FROM profiles WHERE name = ?", (name,))
        self._conn.commit()

    def set_setting(self, key: str, value: str):
        self._conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else default

    def close(self):
        self._conn.close()
