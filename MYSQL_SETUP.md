# MySQL Setup and Data Access

The app supports MySQL 8.0.16+ and SQLite. SQLite remains the default. MySQL tables are created when the app starts with `DATABASE_BACKEND=mysql`.

## 1. Create the database and app user

Start the MySQL service, then connect as a MySQL administrator with MySQL Workbench or the `mysql` command-line client. Run:

```sql
CREATE DATABASE stock_prediction
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'stock_app'@'127.0.0.1' IDENTIFIED BY 'choose_a_strong_password';
GRANT ALL PRIVILEGES ON stock_prediction.* TO 'stock_app'@'127.0.0.1';
```

The app creates and seeds the tables on startup. The configured MySQL user needs table creation permissions inside `stock_prediction`.

## 2. Configure the application

Create a file named `.env` in the same folder as `app.py`. `.env.example` is only a template; editing it alone does not change the app configuration. Copy these settings into `.env`, then set the MySQL password you chose above:

```dotenv
DATABASE_BACKEND=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=stock_app
MYSQL_PASSWORD=choose_a_strong_password
MYSQL_DATABASE=stock_prediction
MYSQL_AUTO_CREATE_DATABASE=false
```

Keep any existing API-key settings in `.env`. Do not commit `.env` or put real keys/passwords in `.env.example`.

## 3. Install and start

From the project folder, activate its virtual environment and install requirements:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

On startup, `database.py` creates these tables and constraints:

- `companies`: ticker primary key and company/sector catalog.
- `stocks`: historical OHLCV and indicators; unique `(company, date)`, company foreign key, valid OHLC/RSI/volume checks, and date index.
- `market_quotes`: latest daily quote per company; company primary/foreign key and positive-price/valid-range checks.
- `predictions`: model outputs; company foreign key, direction/probability/price checks, and created-time index.
- `graph_edges`: correlation links; company foreign keys, unique company pair, distinct-endpoint and weight checks.

## 4. Fetch and store market data

Open the app at `http://127.0.0.1:5000`.

- On the dashboard, click **Refresh quotes** to fetch the latest Yahoo Finance daily bars. Successful quotes are stored in `market_quotes` and shown with their source and market date.
- To populate historical OHLCV rows used by charts and models, open `/admin` and run **Full Pipeline** or **Refresh Data**. The collector tries Alpha Vantage when configured and falls back to Yahoo Finance when that request fails. Those rows are stored in `stocks` using the selected backend.

The latest-quote button uses Yahoo Finance; it does not promise intraday or official exchange prices. Existing SQLite data is not copied automatically. Run the historical data refresh after switching backends to populate MySQL.

## 5. Read data from MySQL

Connect with MySQL Workbench using the host, port, database, username, and password from `.env`, or run `mysql -h 127.0.0.1 -P 3306 -u stock_app -p stock_prediction` and enter the password when prompted. Then query:

```sql
SHOW TABLES;

SELECT symbol, name, sector
FROM companies
ORDER BY symbol;

SELECT company, date, `close`, volume
FROM stocks
WHERE company = 'RELIANCE'
ORDER BY date DESC
LIMIT 10;

SELECT company, date, price, `change`, change_pct, source, refreshed_at
FROM market_quotes
ORDER BY company;

SELECT company, prediction, probability, current_price, predicted_price, created_at
FROM predictions
ORDER BY created_at DESC
LIMIT 20;

SELECT company_a, company_b, weight, edge_type
FROM graph_edges
ORDER BY weight DESC;
```

The Flask API can also read the data: `/api/stock-history/RELIANCE`, `/api/market-ticker`, and `/api/graph-data`.

## Troubleshooting

- If MySQL Workbench shows no rows, confirm `DATABASE_BACKEND=mysql` is in the project `.env` file, not only `.env.example`.
- Stop Flask with `Ctrl+C` and start it again after editing `.env`; the backend is read when Python starts.
- Successful startup should print `[DB] MySQL schema initialized (stock_prediction).` If you see a SQLite initialization message, the app is still using SQLite.
- In Workbench, refresh the schema list and select `stock_prediction` before running `SHOW TABLES;`.
- Once MySQL is active, choose **Refresh Data** or **Full Pipeline** in `/admin` to fetch historical rows. Use **Refresh quotes** on the dashboard to populate `market_quotes`.
- The MySQL user needs permissions on the selected database. Authentication or permission errors appear in the Flask terminal; do not put the password in source code or share it in chat.
