import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sillaje-mssql-erp-secret-key-2026')
    PORT = 5050
    
    # MSSQL Sunucu ve Veri Tabanı Ayarları
    MSSQL_SERVER = os.environ.get('MSSQL_SERVER', r'DESKTOP-02AA25J\MSSQLSERVER01')
    MSSQL_DATABASE = os.environ.get('MSSQL_DATABASE', 'SillajeERP')
    MSSQL_DRIVER = os.environ.get('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server')
    
    # SQLAlchemy Bağlantı Metni (Kullanıcı Talebine Uygun)
    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pyodbc://@{MSSQL_SERVER}/{MSSQL_DATABASE}?"
        f"driver={MSSQL_DRIVER.replace(' ', '+')}&Trusted_connection=yes&TrustServerCertificate=yes"
    )
    
    # Düz PyODBC Bağlantı Metni
    PYODBC_CONN_STR = (
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={MSSQL_DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
    
    # Master DB için (Veri tabanı otomatik oluşturulurken kullanılır)
    PYODBC_MASTER_CONN_STR = (
        f"DRIVER={{{MSSQL_DRIVER}}};"
        f"SERVER={MSSQL_SERVER};"
        "DATABASE=master;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )
