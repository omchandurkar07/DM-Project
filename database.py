"""SQLite/MySQL connections, schemas, and shared query helpers."""

import re
import sqlite3

from config import (
    DATABASE_BACKEND,
    DATABASE_PATH,
    MYSQL_AUTO_CREATE_DATABASE,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
    STOCKS,
)


def get_connection():
    """Return a connection for the configured database backend."""
    if DATABASE_BACKEND == 'mysql':
        import mysql.connector

        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset='utf8mb4',
            use_unicode=True,
        )
    if DATABASE_BACKEND != 'sqlite':
        raise ValueError("DATABASE_BACKEND must be 'sqlite' or 'mysql'")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_cursor(connection):
    """Return a dictionary cursor where the backend supports it."""
    if DATABASE_BACKEND == 'mysql':
        return connection.cursor(dictionary=True)
    return connection.cursor()


def execute_sql(cursor, query, params=()):
    """Execute shared qmark-parameterized SQL for either supported backend."""
    if DATABASE_BACKEND == 'mysql':
        query = query.replace('?', '%s')
    return cursor.execute(query, params)


def _init_mysql_db():
    """Create the configured MySQL database, tables, indexes, and constraints."""
    import mysql.connector

    if not re.fullmatch(r'[A-Za-z0-9_]+', MYSQL_DATABASE):
        raise ValueError('MYSQL_DATABASE may contain only letters, numbers, and underscores')

    if MYSQL_AUTO_CREATE_DATABASE:
        server = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            charset='utf8mb4',
            use_unicode=True,
        )
        try:
            cursor = server.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            server.commit()
        finally:
            server.close()

    conn = get_connection()
    cursor = conn.cursor()
    statements = [
        '''CREATE TABLE IF NOT EXISTS companies (
            symbol VARCHAR(20) PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            sector VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
        '''CREATE TABLE IF NOT EXISTS stocks (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            company VARCHAR(20) NOT NULL,
            date DATE NOT NULL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            ma20 DOUBLE,
            ma50 DOUBLE,
            rsi DOUBLE,
            macd DOUBLE,
            `signal` DOUBLE,
            CONSTRAINT uq_stocks_company_date UNIQUE (company, date),
            CONSTRAINT fk_stocks_company FOREIGN KEY (company) REFERENCES companies(symbol),
            CONSTRAINT chk_stocks_ohlc CHECK (
                (high IS NULL OR low IS NULL OR high >= low) AND
                (open IS NULL OR open >= 0) AND (high IS NULL OR high >= 0) AND
                (low IS NULL OR low >= 0) AND (close IS NULL OR close >= 0) AND
                (volume IS NULL OR volume >= 0)
            ),
            CONSTRAINT chk_stocks_rsi CHECK (rsi IS NULL OR rsi BETWEEN 0 AND 100),
            INDEX idx_stocks_date_company (date, company)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
        '''CREATE TABLE IF NOT EXISTS market_quotes (
            company VARCHAR(20) PRIMARY KEY,
            date DATE NOT NULL,
            price DOUBLE NOT NULL,
            `change` DOUBLE NOT NULL,
            change_pct DOUBLE NOT NULL,
            high DOUBLE,
            low DOUBLE,
            volume BIGINT,
            source VARCHAR(40) NOT NULL,
            refreshed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_market_quotes_company FOREIGN KEY (company) REFERENCES companies(symbol),
            CONSTRAINT chk_market_quote_values CHECK (
                price > 0 AND (high IS NULL OR high >= 0) AND
                (low IS NULL OR low >= 0) AND (high IS NULL OR low IS NULL OR high >= low) AND
                (volume IS NULL OR volume >= 0)
            )
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
        '''CREATE TABLE IF NOT EXISTS predictions (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            company VARCHAR(20) NOT NULL,
            prediction VARCHAR(10) NOT NULL,
            probability DOUBLE,
            predicted_price DOUBLE,
            current_price DOUBLE,
            algorithm_used VARCHAR(50) DEFAULT 'RandomForest',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_predictions_company FOREIGN KEY (company) REFERENCES companies(symbol),
            CONSTRAINT chk_prediction_direction CHECK (prediction IN ('UP', 'DOWN')),
            CONSTRAINT chk_prediction_probability CHECK (probability IS NULL OR probability BETWEEN 0 AND 1),
            CONSTRAINT chk_prediction_prices CHECK (
                (predicted_price IS NULL OR predicted_price >= 0) AND
                (current_price IS NULL OR current_price >= 0)
            ),
            INDEX idx_predictions_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
        '''CREATE TABLE IF NOT EXISTS graph_edges (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            company_a VARCHAR(20) NOT NULL,
            company_b VARCHAR(20) NOT NULL,
            weight DOUBLE NOT NULL,
            edge_type VARCHAR(50),
            CONSTRAINT uq_graph_edge UNIQUE (company_a, company_b),
            CONSTRAINT fk_graph_company_a FOREIGN KEY (company_a) REFERENCES companies(symbol),
            CONSTRAINT fk_graph_company_b FOREIGN KEY (company_b) REFERENCES companies(symbol),
            CONSTRAINT chk_graph_distinct_companies CHECK (company_a <> company_b),
            CONSTRAINT chk_graph_weight CHECK (weight BETWEEN -1 AND 1)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
    ]
    try:
        for statement in statements:
            cursor.execute(statement)
        cursor.executemany(
            '''INSERT INTO companies (symbol, name, sector) VALUES (%s, %s, %s)
               ON DUPLICATE KEY UPDATE name=VALUES(name), sector=VALUES(sector)''',
            [(key, info['name'], info['sector']) for key, info in STOCKS.items()],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def init_db():
    """Create all application tables for the configured backend."""
    if DATABASE_BACKEND == 'mysql':
        _init_mysql_db()
        print(f"[DB] MySQL schema initialized ({MYSQL_DATABASE}).")
        return
    if DATABASE_BACKEND != 'sqlite':
        raise ValueError("DATABASE_BACKEND must be 'sqlite' or 'mysql'")

    conn = get_connection()
    cursor = conn.cursor()
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_quotes (
            company VARCHAR(20) PRIMARY KEY,
            date DATE NOT NULL,
            price FLOAT NOT NULL,
            change FLOAT NOT NULL,
            change_pct FLOAT NOT NULL,
            high FLOAT,
            low FLOAT,
            volume BIGINT,
            source VARCHAR(40) NOT NULL,
            refreshed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company VARCHAR(20) NOT NULL,
            prediction VARCHAR(10),
            probability FLOAT,
            predicted_price FLOAT,
            current_price FLOAT,
            algorithm_used VARCHAR(50) DEFAULT 'RandomForest',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS graph_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_a VARCHAR(20),
            company_b VARCHAR(20),
            weight FLOAT,
            edge_type VARCHAR(50),
            UNIQUE(company_a, company_b)
        )
    ''')
    conn.commit()
    conn.close()
    print("[DB] SQLite tables initialized.")


def execute_query(query, params=()):
    """Execute a write query."""
    conn = get_connection()
    try:
        cursor = get_cursor(conn)
        execute_sql(cursor, query, params)
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(query, params=()):
    """Fetch all rows as a list of dictionaries."""
    conn = get_connection()
    try:
        cursor = get_cursor(conn)
        execute_sql(cursor, query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def fetch_one(query, params=()):
    """Fetch a single row as a dictionary."""
    conn = get_connection()
    try:
        cursor = get_cursor(conn)
        execute_sql(cursor, query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def save_market_quotes(quotes, source='Yahoo Finance'):
    """Insert or update externally fetched daily quotes."""
    conn = get_connection()
    try:
        cursor = get_cursor(conn)
        if DATABASE_BACKEND == 'mysql':
            query = '''
                INSERT INTO market_quotes
                    (company, date, price, `change`, change_pct, high, low, volume, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    date=VALUES(date), price=VALUES(price), `change`=VALUES(`change`),
                    change_pct=VALUES(change_pct), high=VALUES(high), low=VALUES(low),
                    volume=VALUES(volume), source=VALUES(source), refreshed_at=CURRENT_TIMESTAMP
            '''
            params = [
                (company, quote['date'], quote['price'], quote['change'],
                 quote['change_pct'], quote['high'], quote['low'], quote['volume'],
                 quote.get('source', source))
                for company, quote in quotes.items()
            ]
            cursor.executemany(query, params)
        else:
            cursor.executemany('''
                INSERT INTO market_quotes
                    (company, date, price, change, change_pct, high, low, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company) DO UPDATE SET
                    date=excluded.date, price=excluded.price, change=excluded.change,
                    change_pct=excluded.change_pct, high=excluded.high, low=excluded.low,
                    volume=excluded.volume, source=excluded.source,
                    refreshed_at=CURRENT_TIMESTAMP
            ''', [
                (company, quote['date'], quote['price'], quote['change'],
                 quote['change_pct'], quote['high'], quote['low'], quote['volume'],
                 quote.get('source', source))
                for company, quote in quotes.items()
            ])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
