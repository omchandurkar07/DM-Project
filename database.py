"""
database.py — SQLite database connection and schema management
"""

import sqlite3
import os
from config import DATABASE_PATH


def get_connection():
    """Return a SQLite connection with row_factory set."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create all tables if they do not already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # ── stocks ────────────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stocks (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            company   VARCHAR(20)  NOT NULL,
            date      DATE         NOT NULL,
            open      FLOAT,
            high      FLOAT,
            low       FLOAT,
            close     FLOAT,
            volume    BIGINT,
            ma20      FLOAT,
            ma50      FLOAT,
            rsi       FLOAT,
            macd      FLOAT,
            signal    FLOAT,
            UNIQUE(company, date)
        )
    ''')

    # ── predictions ───────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            company         VARCHAR(20) NOT NULL,
            prediction      VARCHAR(10),
            probability     FLOAT,
            predicted_price FLOAT,
            current_price   FLOAT,
            algorithm_used  VARCHAR(50) DEFAULT 'RandomForest',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ── graph_edges ───────────────────────────────────────────────────────────
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS graph_edges (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            company_a   VARCHAR(20),
            company_b   VARCHAR(20),
            weight      FLOAT,
            edge_type   VARCHAR(50),
            UNIQUE(company_a, company_b)
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Tables initialized.")


def execute_query(query, params=()):
    """Execute a write query."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id


def fetch_all(query, params=()):
    """Fetch all rows as a list of dicts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def fetch_one(query, params=()):
    """Fetch a single row as dict."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
