import os
import re
import pyodbc
from config import Config
from db import get_db_connection

def run_sql_schema():
    print(f"[*] MSSQL Veri Tabanı Kurulumu Başlatılıyor... Sunucu: {Config.MSSQL_SERVER}")
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    if not os.path.exists(schema_path):
        print(f"[X] Hata: {schema_path} bulunamadı!")
        return False

    with open(schema_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # T-SQL Script'ini 'GO' komutlarına göre böl
    batches = re.split(r'(?i)^\s*GO\s*$', sql_content, flags=re.MULTILINE)

    try:
        # Önce master veritabanına bağlanıp Veri Tabanının olup olmadığını kontrol edelim
        conn = get_db_connection(use_master=True)
        cursor = conn.cursor()
        
        print(f"[*] 'master' veritabanına bağlandı. Veri tabanı ({Config.MSSQL_DATABASE}) kontrol ediliyor...")
        cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{Config.MSSQL_DATABASE}') CREATE DATABASE {Config.MSSQL_DATABASE};")
        conn.close()
        print(f"[+] Veri tabanı ({Config.MSSQL_DATABASE}) hazır.")

        # Şimdi ana veritabanımıza bağlanıp tabloları ve örnek verileri yükleyelim
        conn = get_db_connection(use_master=False)
        cursor = conn.cursor()

        count = 0
        for batch in batches:
            clean_batch = batch.strip()
            if clean_batch and not clean_batch.lower().startswith('use '):
                cursor.execute(clean_batch)
                conn.commit()
                count += 1
                
        conn.close()
        print(f"[SUCCESS] Toplam {count} T-SQL komut bloğu MSSQL üzerinde başarıyla çalıştırıldı.")
        print(f"[SUCCESS] Tablolar, ilişkiler ve örnek veriler MSSQL'e yüklendi!")
        return True

    except Exception as e:
        print(f"[X] MSSQL Kurulum Hatası: {e}")
        print("\nÖNERİ: Bilgisayarınızda SQL Server Server instance'ının çalışıp çalışmadığını kontrol edin veya 'schema.sql' dosyasını SQL Server Management Studio (SSMS) üzerinden doğrudan çalıştırın.")
        return False

if __name__ == '__main__':
    run_sql_schema()
