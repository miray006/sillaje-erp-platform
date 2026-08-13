import pyodbc
from config import Config

def get_db_connection(use_master=False):
    """
    Doğrudan MSSQL sunucusuna PyODBC ile bağlanır.
    use_master=True ise 'master' veritabanına bağlanır (database oluşturmak için).
    """
    conn_str = Config.PYODBC_MASTER_CONN_STR if use_master else Config.PYODBC_CONN_STR
    try:
        conn = pyodbc.connect(conn_str, timeout=5, autocommit=use_master)
        return conn
    except pyodbc.Error as err:
        print(f"[MSSQL Bağlantı Hatası]: {err}")
        raise ConnectionError(
            f"MSSQL Sunucusuna ({Config.MSSQL_SERVER}) bağlanılamadı.\n"
            f"Lütfen SQL Server hizmetinin çalıştığından ve '{Config.MSSQL_DRIVER}' sürücüsünün yüklü olduğundan emin olun.\n"
            f"Detay: {err}"
        )

def query_all(sql, params=()):
    """MSSQL üzerinden SELECT sorgusu çalıştırır ve Python dictionary listesi döndürür."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            results.append(dict(zip(columns, row)))
        return results
    finally:
        conn.close()

def query_one(sql, params=()):
    """MSSQL üzerinden tek satırlı SELECT sorgusu çalıştırır ve dictionary döndürür."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if not row:
            return None
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    finally:
        conn.close()

def execute_cmd(sql, params=()):
    """INSERT, UPDATE, DELETE sorgularını çalıştırır ve commit eder."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def check_mssql_status():
    """MSSQL sunucu erişilebilirliğini ve SillajeERP veritabanı durumunu kontrol eder."""
    try:
        res = query_one("SELECT DB_NAME() as CurrentDB, @@VERSION as Version, GETDATE() as ServerTime")
        return {
            "status": "connected",
            "server": Config.MSSQL_SERVER,
            "database": res["CurrentDB"] if res else Config.MSSQL_DATABASE,
            "server_time": str(res["ServerTime"]) if res else None,
            "version": res["Version"].split('\n')[0] if res else "MSSQL"
        }
    except Exception as e:
        return {
            "status": "error",
            "server": Config.MSSQL_SERVER,
            "error_message": str(e)
        }
