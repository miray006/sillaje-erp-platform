import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sillaje-luxury-erp-secret-2026')
    PORT = 5000
    ERP_PORT = 5000
    BANK_PORT = 5001
    SEND_FILE_MAX_AGE_DEFAULT = 0
    TEMPLATES_AUTO_RELOAD = True
    
    # MSSQL Connection Configuration
    MSSQL_SERVER = 'localhost'
    MSSQL_DATABASE = 'SILLAJE_ERP_DB'
    MSSQL_DRIVER = 'ODBC Driver 17 for SQL Server'
    
    # Primary Connection String (MSSQL via pyodbc with Windows Authentication)
    MSSQL_CONN_STR = f"DRIVER={{{MSSQL_DRIVER}}};SERVER={MSSQL_SERVER};DATABASE={MSSQL_DATABASE};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=2;"
    PYODBC_CONN_STR = MSSQL_CONN_STR
    
    # SQLite Fallback Path
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'sillaje_erp.db')
    
    # Integration Endpoints (Supports local & cloud environment variables)
    BANK_API_URL = os.environ.get('BANK_API_URL', f"http://127.0.0.1:{BANK_PORT}/api/dbs/fatura-kayit")
    ERP_WEBHOOK_URL = os.environ.get('ERP_WEBHOOK_URL', f"http://127.0.0.1:{PORT}/api/webhook/mail-gonder")
