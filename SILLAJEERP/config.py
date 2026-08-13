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
    
    # Integration Endpoints (Detects local vs cloud Render environment automatically with path normalization)
    is_render = os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    default_bank_url = "https://banka-portal.onrender.com/api/dbs/fatura-kayit" if is_render else f"http://127.0.0.1:{BANK_PORT}/api/dbs/fatura-kayit"
    default_webhook_url = "https://sillaje-erp.onrender.com/api/webhook/mail-gonder" if is_render else f"http://127.0.0.1:{PORT}/api/webhook/mail-gonder"

    raw_bank_url = os.environ.get('BANK_API_URL', default_bank_url)
    if raw_bank_url and not raw_bank_url.endswith('/api/dbs/fatura-kayit'):
        raw_bank_url = raw_bank_url.rstrip('/') + '/api/dbs/fatura-kayit'
    BANK_API_URL = raw_bank_url

    raw_webhook_url = os.environ.get('ERP_WEBHOOK_URL', default_webhook_url)
    if raw_webhook_url and not raw_webhook_url.endswith('/api/webhook/mail-gonder'):
        raw_webhook_url = raw_webhook_url.rstrip('/') + '/api/webhook/mail-gonder'
    ERP_WEBHOOK_URL = raw_webhook_url
