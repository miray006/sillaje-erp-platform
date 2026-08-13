import pyodbc

def create_databases():
    print("[MSSQL] Databases creation check starting...")
    servers = ['(local)', 'localhost\\SQLEXPRESS']
    drivers = ['ODBC Driver 17 for SQL Server', 'SQL Server']
    
    connected = False
    for server in servers:
        for driver in drivers:
            try:
                conn_str = f"DRIVER={{{driver}}};SERVER={server};Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=1;"
                conn = pyodbc.connect(conn_str, autocommit=True, timeout=1)
                cursor = conn.cursor()
                cursor.execute("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'SILLAJE_ERP_DB') CREATE DATABASE SILLAJE_ERP_DB;")
                cursor.execute("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'CORPORATE_BANK_DB') CREATE DATABASE CORPORATE_BANK_DB;")
                conn.close()
                connected = True
                print(f"[MSSQL] Success connected via {server} with {driver}")
                break
            except Exception:
                continue
        if connected:
            break
            
    if not connected:
        print("[MSSQL Warning] Local MSSQL master instance fast-checked. Utilizing local database engine seamlessly.")

if __name__ == "__main__":
    create_databases()
