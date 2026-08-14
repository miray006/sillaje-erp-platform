import pyodbc
import sqlite3
import os
from datetime import datetime

class BankConfig:
    MSSQL_SERVER = 'localhost'
    MSSQL_DATABASE = 'CORPORATE_BANK_DB'
    MSSQL_DRIVER = 'ODBC Driver 17 for SQL Server'
    MSSQL_CONN_STR = f"DRIVER={{{MSSQL_DRIVER}}};SERVER={MSSQL_SERVER};DATABASE={MSSQL_DATABASE};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=2;"
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'corporate_bank.db')

_CACHED_BANK_ENGINE = None

def get_bank_db_connection():
    global _CACHED_BANK_ENGINE
    if _CACHED_BANK_ENGINE == "SQLITE":
        conn = sqlite3.connect(BankConfig.SQLITE_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn, "SQLITE"
    elif _CACHED_BANK_ENGINE == "MSSQL":
        try:
            conn = pyodbc.connect(BankConfig.MSSQL_CONN_STR, timeout=1)
            return conn, "MSSQL"
        except Exception:
            _CACHED_BANK_ENGINE = "SQLITE"
            conn = sqlite3.connect(BankConfig.SQLITE_PATH, timeout=5)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            return conn, "SQLITE"

    try:
        conn = pyodbc.connect(BankConfig.MSSQL_CONN_STR, timeout=0.2)
        _CACHED_BANK_ENGINE = "MSSQL"
        return conn, "MSSQL"
    except Exception:
        _CACHED_BANK_ENGINE = "SQLITE"
        conn = sqlite3.connect(BankConfig.SQLITE_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn, "SQLITE"

def sync_dealer_limits(cursor):
    """Calculates live used_limit and available_limit for all dealers from active pending DBS transactions."""
    try:
        cursor.execute("SELECT dealer_code, SUM(amount) FROM Bank_DBS_Transactions WHERE status = 'Bekliyor' GROUP BY dealer_code")
        pending_rows = cursor.fetchall()
        pending_map = {}
        for r in pending_rows:
            d_code = r[0]
            sum_amt = float(r[1] or 0)
            pending_map[d_code] = sum_amt

        cursor.execute("SELECT id, dealer_code, dbs_limit FROM Bank_Dealers")
        dealer_rows = cursor.fetchall()
        for d in dealer_rows:
            d_id = d[0]
            d_code = d[1]
            dbs_limit = float(d[2] or 0)
            used = pending_map.get(d_code, 0.0)
            available = max(0.0, dbs_limit - used)
            cursor.execute("UPDATE Bank_Dealers SET used_limit = ?, available_limit = ? WHERE id = ?", (used, available, d_id))
    except Exception as e:
        print("[BANK WARN] sync_dealer_limits error:", e)

def init_bank_db():
    print("[BANKA OPERASYON PLATFORMU DB] Initializing database tables...")
    conn, engine_type = get_bank_db_connection()
    cursor = conn.cursor()

    if engine_type == "MSSQL":
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Bank_DBS_Transactions')
        CREATE TABLE Bank_DBS_Transactions (
            id INT IDENTITY(1,1) PRIMARY KEY,
            dbs_ref NVARCHAR(50) UNIQUE NOT NULL,
            dealer_code NVARCHAR(50) NOT NULL,
            dealer_name NVARCHAR(200) NOT NULL,
            invoice_no NVARCHAR(50) NOT NULL,
            amount DECIMAL(18,2) NOT NULL,
            due_date NVARCHAR(50) NOT NULL,
            status NVARCHAR(50) DEFAULT 'Bekliyor',
            created_at NVARCHAR(50) NOT NULL,
            processed_at NVARCHAR(50) NULL,
            receipt_code NVARCHAR(50) NULL
        )
        """)

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Bank_Dealers')
        CREATE TABLE Bank_Dealers (
            id INT IDENTITY(1,1) PRIMARY KEY,
            dealer_code NVARCHAR(50) UNIQUE NOT NULL,
            dealer_name NVARCHAR(200) NOT NULL,
            tax_no NVARCHAR(50) NOT NULL,
            dbs_limit DECIMAL(18,2) NOT NULL,
            used_limit DECIMAL(18,2) DEFAULT 0,
            available_limit DECIMAL(18,2) NOT NULL
        )
        """)

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Bank_Logs')
        CREATE TABLE Bank_Logs (
            id INT IDENTITY(1,1) PRIMARY KEY,
            action NVARCHAR(100) NOT NULL,
            details NVARCHAR(MAX) NOT NULL,
            created_at NVARCHAR(50) NOT NULL
        )
        """)
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bank_DBS_Transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dbs_ref TEXT UNIQUE NOT NULL,
            dealer_code TEXT UNIQUE NOT NULL,
            dealer_name TEXT NOT NULL,
            invoice_no TEXT NOT NULL,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Bekliyor',
            created_at TEXT NOT NULL,
            processed_at TEXT NULL,
            receipt_code TEXT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bank_Dealers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dealer_code TEXT UNIQUE NOT NULL,
            dealer_name TEXT NOT NULL,
            tax_no TEXT NOT NULL,
            dbs_limit REAL NOT NULL,
            used_limit REAL DEFAULT 0,
            available_limit REAL NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bank_Logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)

    # Update existing reference codes from DBS-REF- to BNK-REF- and DBS logs to BNK
    try:
        cursor.execute("UPDATE Bank_DBS_Transactions SET dbs_ref = REPLACE(dbs_ref, 'DBS-REF-', 'BNK-REF-') WHERE dbs_ref LIKE 'DBS-REF-%'")
        cursor.execute("UPDATE Bank_Logs SET action = REPLACE(action, 'DBS_', 'BNK_') WHERE action LIKE 'DBS_%'")
        cursor.execute("UPDATE Bank_Logs SET details = REPLACE(details, 'DBS ', 'BNK ') WHERE details LIKE '%DBS%'")
    except Exception as e:
        print("[BANK DB WARN] Reference migration warning:", e)

    conn.commit()

    # Seed & Upsert 15 Corporate Bank Dealers without overwriting live used_limit / available_limit
    dealers = [
        ("DLR-001", "Beymen Lüks Kozmetik A.Ş.", "1240592817", 5000000.00),
        ("DLR-002", "Sephora Türkiye Mağazacılık A.Ş.", "7690184201", 3500000.00),
        ("DLR-003", "Harvey Nichols Akasya Boutique", "4520918374", 2500000.00),
        ("DLR-004", "Vakko Perfumery & Beauty", "9102847162", 4000000.00),
        ("DLR-005", "Brandroom Nişantaşı Mağazacılık", "3810294715", 2000000.00),
        ("DLR-006", "Sevil Parfümeri Zinciri", "5520194830", 1500000.00),
        ("DLR-007", "Yargıcı Kozmetik ve Yaşam", "1190284756", 1200000.00),
        ("DLR-008", "Douglas Parfümeri Türkiye", "8829104753", 3000000.00),
        ("DLR-009", "Boyner Büyük Mağazacılık", "1829304857", 6000000.00),
        ("DLR-010", "Watsons Güzellik Mağazaları", "6629104822", 2000000.00),
        ("DLR-011", "Rossmann Kozmetik A.Ş.", "4410928371", 2200000.00),
        ("DLR-012", "Gratis İç ve Dış Ticaret", "9928104736", 2800000.00),
        ("DLR-013", "Atasoy Lüks Parfümeri", "3310492819", 1800000.00),
        ("DLR-014", "İstinye Parfüm Butik", "7719203845", 3200000.00),
        ("DLR-015", "Kanyon Niche Hub", "5540192837", 4500000.00)
    ]

    for d in dealers:
        cursor.execute("SELECT COUNT(*) FROM Bank_Dealers WHERE dealer_code = ?", (d[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO Bank_Dealers (dealer_code, dealer_name, tax_no, dbs_limit, used_limit, available_limit) VALUES (?, ?, ?, ?, 0.0, ?)", (d[0], d[1], d[2], d[3], d[3]))
        else:
            cursor.execute("UPDATE Bank_Dealers SET dealer_name = ?, tax_no = ?, dbs_limit = ? WHERE dealer_code = ?", (d[1], d[2], d[3], d[0]))

    # Seed sample pending receivables if Bank_DBS_Transactions is empty on fresh setup
    cursor.execute("SELECT COUNT(*) FROM Bank_DBS_Transactions")
    if cursor.fetchone()[0] == 0:
        now_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sample_txs = [
            ("BNK-REF-202608131001", "DLR-005", "Brandroom Nişantaşı Mağazacılık", "INV-2026-007", 123399.99, "2026-09-12", "Bekliyor", now_date),
            ("BNK-REF-202608131002", "DLR-004", "Vakko Perfumery & Beauty", "INV-2026-004", 678654.00, "2026-09-24", "Bekliyor", now_date)
        ]
        for tx in sample_txs:
            cursor.execute("""
            INSERT INTO Bank_DBS_Transactions (dbs_ref, dealer_code, dealer_name, invoice_no, amount, due_date, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, tx)
    
    # Seed initial audit logs if Bank_Logs is empty
    cursor.execute("SELECT COUNT(*) FROM Bank_Logs")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sample_logs = [
            ("BNK_SYSTEM_INIT", "Banka Operasyon Platformu altyapı ve veritabanı motoru başlatıldı.", now_str),
            ("BNK_LIMIT_SETUP", "15 Kurumsal Bayi hesabı için toplam 45.200.000,00 TL Doğrudan Borçlandırma Sistemi (DBS) kredi limiti tahsis edildi.", now_str)
        ]
        for lg in sample_logs:
            cursor.execute("INSERT INTO Bank_Logs (action, details, created_at) VALUES (?, ?, ?)", lg)
    
    conn.commit()

    # Recalculate live dealer risk limits based on active pending transactions
    sync_dealer_limits(cursor)
    conn.commit()

    conn.close()
    print("[BANKA OPERASYON PLATFORMU DB] Bank Database initialized successfully with live dynamic dealer limits.")

if __name__ == "__main__":
    init_bank_db()
