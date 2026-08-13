import pyodbc
from config import Config

def get_db_connection():
    try:
        conn = pyodbc.connect(Config.PYODBC_CONN_STR, timeout=5)
        return conn
    except pyodbc.Error as err:
        raise ConnectionError(
            f"MSSQL Sunucusuna ({Config.MSSQL_SERVER}) bağlanılamadı.\n"
            f"Veri tabanı: {Config.MSSQL_DATABASE}\nDetay: {err}"
        )

def query_all(sql, params=()):
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
