import os
import re
import pyodbc

def run_sql_schema():
    server = r'DESKTOP-02AA25J\MSSQLSERVER01'
    driver = 'ODBC Driver 17 for SQL Server'
    db_name = 'SILLAJE_BANK_ERP_PRO_DB'
    
    print(f"[*] MSSQL Veri Tabanı Kurulumu Başlatılıyor... Sunucu: {server}")
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    if not os.path.exists(schema_path):
        print(f"[X] Hata: {schema_path} bulunamadı!")
        return False

    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    batches = re.split(r'(?i)^\s*GO\s*$', sql_content, flags=re.MULTILINE)

    try:
        # Master DB Bağlantısı
        master_conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE=master;Trusted_Connection=yes;TrustServerCertificate=yes;"
        conn = pyodbc.connect(master_conn_str, autocommit=True, timeout=5)
        cursor = conn.cursor()
        
        print(f"[*] 'master' veritabanına bağlandı. Veri tabanı ({db_name}) kontrol ediliyor...")
        cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{db_name}') CREATE DATABASE {db_name};")
        conn.close()
        print(f"[+] Veri tabanı ({db_name}) hazır.")

        # Ana DB Bağlantısı
        db_conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={db_name};Trusted_Connection=yes;TrustServerCertificate=yes;"
        conn = pyodbc.connect(db_conn_str, autocommit=False, timeout=5)
        cursor = conn.cursor()

        count = 0
        for batch in batches:
            clean_batch = batch.strip()
            if clean_batch and not clean_batch.lower().startswith('use '):
                cursor.execute(clean_batch)
                conn.commit()
                count += 1
                
        conn.close()
        print(f"[SUCCESS] Toplam {count} T-SQL bloğu MSSQL sunucusunda çalıştırıldı.")
        print(f"[SUCCESS] Veri Tabanı '{db_name}' ve tüm tablolar kuruldu!")
        return True

    except Exception as e:
        print(f"[X] MSSQL Kurulum Hatası: {e}")
        return False

if __name__ == '__main__':
    run_sql_schema()
