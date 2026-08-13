import pyodbc
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from config import Config

def get_db_connection():
    """Returns an active pyodbc MSSQL connection or sqlite3 fallback connection wrapped with dict cursor capability."""
    try:
        conn = pyodbc.connect(Config.MSSQL_CONN_STR, timeout=2)
        return conn, "MSSQL"
    except Exception as e:
        # Seamless SQLite fallback
        conn = sqlite3.connect(Config.SQLITE_PATH)
        conn.row_factory = sqlite3.Row
        return conn, "SQLITE"

def init_erp_db():
    print("[SILLAJÉ ERP DB] Initializing refined database tables and seed data...")
    conn, engine_type = get_db_connection()
    cursor = conn.cursor()

    if engine_type == "MSSQL":
        # Create Users Table
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
        CREATE TABLE Users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            email NVARCHAR(100) UNIQUE NOT NULL,
            password NVARCHAR(100) NOT NULL,
            name NVARCHAR(100) NOT NULL,
            role NVARCHAR(50) DEFAULT 'Senior Administrator',
            updated_at NVARCHAR(50) NOT NULL
        )
        """)

        # Drop old ERP_Products table if exists without top_notes column to ensure clean schema update
        cursor.execute("""
        IF EXISTS (SELECT * FROM sys.tables WHERE name = 'ERP_Products') 
           AND NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('ERP_Products') AND name = 'top_notes')
        DROP TABLE ERP_Products;
        """)

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ERP_Products')
        CREATE TABLE ERP_Products (
            id INT IDENTITY(1,1) PRIMARY KEY,
            code NVARCHAR(50) UNIQUE NOT NULL,
            name NVARCHAR(150) NOT NULL,
            brand NVARCHAR(100) DEFAULT 'SILLAJÉ PARFUMS',
            category NVARCHAR(100) NOT NULL,
            collection NVARCHAR(100) NOT NULL,
            volume_ml INT NOT NULL,
            price_tl DECIMAL(18,2) NOT NULL,
            cost_tl DECIMAL(18,2) NOT NULL,
            stock INT NOT NULL,
            reorder_point INT NOT NULL,
            safety_stock INT NOT NULL,
            daily_demand DECIMAL(10,2) NOT NULL,
            lead_time_days INT DEFAULT 7,
            top_notes NVARCHAR(200) NOT NULL,
            heart_notes NVARCHAR(200) NOT NULL,
            base_notes NVARCHAR(200) NOT NULL,
            supplier_name NVARCHAR(150) NOT NULL,
            status NVARCHAR(50) DEFAULT 'Aktif'
        )
        """)

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Dealers')
        CREATE TABLE Dealers (
            id INT IDENTITY(1,1) PRIMARY KEY,
            code NVARCHAR(50) UNIQUE NOT NULL,
            name NVARCHAR(200) NOT NULL,
            tax_office NVARCHAR(100) NOT NULL,
            tax_no NVARCHAR(50) NOT NULL,
            dbs_limit DECIMAL(18,2) NOT NULL,
            dbs_available DECIMAL(18,2) NOT NULL,
            contact NVARCHAR(100) NOT NULL,
            email NVARCHAR(100) NOT NULL,
            phone NVARCHAR(50) NOT NULL,
            status NVARCHAR(50) DEFAULT 'Aktif'
        )
        """)

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ERP_Invoices')
        CREATE TABLE ERP_Invoices (
            id INT IDENTITY(1,1) PRIMARY KEY,
            invoice_no NVARCHAR(50) UNIQUE NOT NULL,
            dealer_code NVARCHAR(50) NOT NULL,
            dealer_name NVARCHAR(200) NOT NULL,
            invoice_date NVARCHAR(50) NOT NULL,
            due_date NVARCHAR(50) NOT NULL,
            total_amount DECIMAL(18,2) NOT NULL,
            tax_amount DECIMAL(18,2) NOT NULL,
            net_amount DECIMAL(18,2) NOT NULL,
            status NVARCHAR(50) DEFAULT 'Onaylandı',
            dbs_status NVARCHAR(50) DEFAULT 'Bekliyor',
            created_at NVARCHAR(50) NOT NULL
        )
        """)

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ERP_Suppliers')
        CREATE TABLE ERP_Suppliers (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(200) NOT NULL,
            category NVARCHAR(100) NOT NULL,
            quality_score INT NOT NULL,
            speed_score INT NOT NULL,
            ontime_rate DECIMAL(5,2) NOT NULL,
            reliability_score INT NOT NULL,
            active_contracts INT DEFAULT 1,
            contact_email NVARCHAR(100) NOT NULL
        )
        """)

        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Bank_Mail_Inbox')
        CREATE TABLE Bank_Mail_Inbox (
            id INT IDENTITY(1,1) PRIMARY KEY,
            receipt_code NVARCHAR(50) UNIQUE NOT NULL,
            sender NVARCHAR(150) NOT NULL,
            subject NVARCHAR(250) NOT NULL,
            body_html NTEXT NOT NULL,
            amount DECIMAL(18,2) NOT NULL,
            invoice_no NVARCHAR(50) NOT NULL,
            dealer_name NVARCHAR(200) NOT NULL,
            received_at NVARCHAR(50) NOT NULL,
            is_read INT DEFAULT 0
        )
        """)
    else:
        # Create Tables in SQLite
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT 'Senior Administrator',
            updated_at TEXT NOT NULL
        )
        """)

        # Recreate SQLite ERP_Products if missing notes
        cursor.execute("PRAGMA table_info(ERP_Products)")
        cols = [c[1] for c in cursor.fetchall()]
        if cols and 'top_notes' not in cols:
            cursor.execute("DROP TABLE ERP_Products")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ERP_Products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            brand TEXT DEFAULT 'SILLAJÉ PARFUMS',
            category TEXT NOT NULL,
            collection TEXT NOT NULL,
            volume_ml INTEGER NOT NULL,
            price_tl REAL NOT NULL,
            cost_tl REAL NOT NULL,
            stock INTEGER NOT NULL,
            reorder_point INTEGER NOT NULL,
            safety_stock INTEGER NOT NULL,
            daily_demand REAL NOT NULL,
            lead_time_days INTEGER DEFAULT 7,
            top_notes TEXT NOT NULL,
            heart_notes TEXT NOT NULL,
            base_notes TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            status TEXT DEFAULT 'Aktif'
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Dealers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            tax_office TEXT NOT NULL,
            tax_no TEXT NOT NULL,
            dbs_limit REAL NOT NULL,
            dbs_available REAL NOT NULL,
            contact TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            status TEXT DEFAULT 'Aktif'
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ERP_Invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            dealer_code TEXT NOT NULL,
            dealer_name TEXT NOT NULL,
            invoice_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            total_amount REAL NOT NULL,
            tax_amount REAL NOT NULL,
            net_amount REAL NOT NULL,
            status TEXT DEFAULT 'Onaylandı',
            dbs_status TEXT DEFAULT 'Bekliyor',
            created_at TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ERP_Suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quality_score INTEGER NOT NULL,
            speed_score INTEGER NOT NULL,
            ontime_rate REAL NOT NULL,
            reliability_score INTEGER NOT NULL,
            active_contracts INTEGER DEFAULT 1,
            contact_email TEXT NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bank_Mail_Inbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_code TEXT UNIQUE NOT NULL,
            sender TEXT NOT NULL,
            subject TEXT NOT NULL,
            body_html TEXT NOT NULL,
            amount REAL NOT NULL,
            invoice_no TEXT NOT NULL,
            dealer_name TEXT NOT NULL,
            received_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0
        )
        """)

    conn.commit()

    # Migrate existing invoice statuses to 'Tahsil Edildi'
    try:
        cursor.execute("UPDATE ERP_Invoices SET dbs_status = 'Tahsil Edildi' WHERE dbs_status LIKE 'Tahsil Edildi%'")
        conn.commit()
    except Exception as e:
        print("[ERP DB WARN] Invoice status migration warning:", e)

    # Seed User Credentials
    cursor.execute("SELECT COUNT(*) FROM Users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO Users (email, password, name, role, updated_at)
        VALUES ('admin@sillaje.com', 'Sillaje2026!', 'Operasyon Müdürü', 'Senior Administrator', ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        conn.commit()
    else:
        cursor.execute("UPDATE Users SET name = 'Operasyon Müdürü' WHERE name LIKE '%Lüks%'")
        conn.commit()

    # Seed 30 Luxury Perfumes with Fragrance Notes & Suppliers
    cursor.execute("SELECT COUNT(*) FROM ERP_Products")
    prod_count = cursor.fetchone()[0]
    if prod_count == 0:
        print("[SILLAJÉ ERP DB] Seeding 30 luxury perfumes with fragrance pyramids & suppliers...")
        perfumes = [
            ("SLJ-101", "Oud Royale Extrait", "Extrait de Parfum", "Haute Parfumerie", 100, 12500.00, 4200.00, 85, 25, 10, 4.5, "Bergamot, Safran, Zencefil", "Bulgar Gülü, İris, Paçuli", "Kamboçya Oudu, Amber, Deri", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-102", "Nuit d'Ambre Impériale", "Private Blend", "Royal Collection", 100, 9800.00, 3100.00, 42, 30, 12, 3.8, "Pembe Biber, Mandolika", "Siyah Misk, Tarçın, Tütsü", "Sıcak Amber, Vanilya, Sandal", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-103", "Velvet Rose & Musk", "Niche Perfume", "Velvet Line", 50, 6400.00, 1950.00, 18, 25, 10, 3.2, "Grasse Gülü, Şeftali", "Mayıs Gülü, Menekşe", "Beyaz Misk, Sedir Ağacı", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-104", "Elixir de Soie", "Extrait de Parfum", "Silk Heritage", 50, 8900.00, 2800.00, 64, 20, 8, 2.9, "İtalyan Bergamotu, İncir", "İpek Çiçeği, Beyaz Şakayık", "Kaşmir Ağacı, Misk", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-105", "Santal Impérial", "Private Blend", "Royal Collection", 100, 14200.00, 4900.00, 12, 25, 10, 4.1, "Avustralya Sandalı, Kakule", "Menekşe Yaprağı, İris", "Dumanlı Deri, Ambergris", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-106", "Iris Absolute", "Niche Perfume", "Botanical Gold", 75, 7600.00, 2300.00, 95, 30, 15, 5.0, "Florsan İris, Neroli", "Orris Kökü, Mavi Süsen", "Beyaz Misk, Tonka Fasulyesi", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-107", "Soleil d'Or Atmosphere", "Atmosphere & Home", "Maison Ambience", 250, 4200.00, 1100.00, 140, 40, 20, 7.5, "Sicilya Limonu, Tatlı Portakal", "Akdeniz Biberiyesi, Lavanta", "Sedir Ağacı, Beyaz Amber", "KozmoPak Lüks Ambalaj A.Ş."),
            ("SLJ-108", "Cedar & Cashmere", "Private Blend", "Velvet Line", 100, 8500.00, 2600.00, 52, 25, 10, 3.4, "Atlas Sediri, Yeşil Çay", "Kaşmir İpeği, Yasemin", "Vetiver, Odunsu Misk", "Bormioli Luxury Glassware (İtalya)"),
            ("SLJ-109", "Rose de Mai Pure", "Extrait de Parfum", "Grasse Reserve", 50, 11000.00, 3700.00, 8, 15, 8, 2.1, "Mayıs Gülü Absolüsü, Limon", "Şam Gülü, Sardunya", "Bal Akoru, Amber", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-110", "Gris Encens", "Niche Perfume", "Haute Parfumerie", 100, 9200.00, 2900.00, 78, 25, 12, 4.0, "Mür Ağacı, Pembe Biber", "Kutsal Tütsü, Ladan", "Gri Amber, Siyah Misk", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-111", "Baccarat Sublime", "Extrait de Parfum", "Crown Jewels", 100, 18500.00, 6200.00, 15, 20, 8, 2.5, "Acı Badem, Safran", "Mısır Yasemini, Sedir", "Esmer Amber, Odunsu Misk", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-112", "Cuir de Russie Prestige", "Private Blend", "Royal Collection", 100, 13800.00, 4500.00, 29, 20, 10, 2.8, "Nyır Ağacı, Bergamot", "Rus Derisi, İris, Karanfil", "Styrax, Huş Ağacı Katranı", "Silgan Dispensing Systems (İsviçre)"),
            ("SLJ-113", "Fleur d'Oranger Royal", "Niche Perfume", "Botanical Gold", 75, 6900.00, 2100.00, 110, 35, 15, 5.8, "Portakal Çiçeği, Petitgrain", "Tunus Nerolisi, Tüberoz", "Beyaz Amber, Misk", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-114", "Bergamote Calabria", "Atmosphere & Home", "Maison Ambience", 250, 3800.00, 980.00, 165, 45, 20, 8.2, "Kalabriya Bergamotu, Lime", "Yeşil Fesleğen, İncir Yaprağı", "Misk, Odunsu Notalar", "KozmoPak Lüks Ambalaj A.Ş."),
            ("SLJ-115", "Patchouli Imperiale", "Private Blend", "Silk Heritage", 100, 10500.00, 3300.00, 45, 25, 10, 3.6, "Endonezya Paçulisi, Kakao", "Gül, Kişniş, Süsen", "Sandal Ağacı, Deri", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-116", "Vétiver Céleste", "Niche Perfume", "Haute Parfumerie", 100, 8100.00, 2450.00, 88, 30, 12, 4.2, "Haiti Vetiveri, Greyfurt", "Pembe Biber, Sedir", "Meşe Yosunu, Benzoin", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-117", "Jasmin de Grasse", "Extrait de Parfum", "Grasse Reserve", 50, 12900.00, 4100.00, 22, 20, 10, 2.7, "Grasse Yasemini Absolüsü", "Gece Açan Yasemin, Ylang-Ylang", "Madagaskar Vanilyası, Misk", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-118", "Ambre Noir Ultra", "Extrait de Parfum", "Crown Jewels", 100, 16000.00, 5400.00, 19, 20, 8, 2.3, "Siyah Amber, Kakule", "Orta Doğu Oudu, Labdanum", "Dumanlı Vanilya, Deri", "Silgan Dispensing Systems (İsviçre)"),
            ("SLJ-119", "Tabac & Vanille Impériale", "Private Blend", "Royal Collection", 100, 11500.00, 3600.00, 60, 25, 12, 3.9, "Tütün Yaprağı, Baharatlar", "Tonka Fasulyesi, Tütün Çiçeği", "Kurutulmuş Meyveler, Odunsu", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-120", "Bois d'Argent Supérieur", "Niche Perfume", "Velvet Line", 100, 9700.00, 3000.00, 34, 25, 10, 3.1, "Ardıç Meyvesi, İris", "Mür, Paçuli, Bal", "Amber, Deri, Misk", "Bormioli Luxury Glassware (İtalya)"),
            ("SLJ-121", "Néroli Sauvage", "Atmosphere & Home", "Maison Ambience", 200, 4500.00, 1250.00, 125, 40, 15, 6.4, "Yaban Nerolisi, Greyfurt", "Portakal Çiçeği, Mine Çiçeği", "Sedir, Ambergris", "KozmoPak Lüks Ambalaj A.Ş."),
            ("SLJ-122", "Tubéreuse Royale", "Extrait de Parfum", "Grasse Reserve", 50, 10800.00, 3400.00, 26, 20, 10, 2.8, "Hindistan Tüberozu, Gardenya", "Beyaz Zambak, Yasemin", "Sandal Ağacı, Misk", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-123", "Safran Oud Prestige", "Private Blend", "Crown Jewels", 100, 15400.00, 5100.00, 14, 20, 8, 2.2, "İran Safranı, Ahududu", "Damask Gülü, Nagarmotha", "Nadir Kamboçya Oudu, Amber", "Silgan Dispensing Systems (İsviçre)"),
            ("SLJ-124", "Musc Poudré", "Niche Perfume", "Silk Heritage", 75, 5900.00, 1750.00, 105, 30, 15, 5.5, "Pudra Notaları, Beyaz İris", "Pamuk Çiçeği, Menekşe", "Saf Beyaz Misk, Heliotrope", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-125", "Cardamome Intense", "Private Blend", "Velvet Line", 100, 8800.00, 2700.00, 48, 25, 10, 3.5, "Guatemala Kakulesi, Tarçın", "Siyah Çay, Karabiber", "Güve Otu, Amber", "Bormioli Luxury Glassware (İtalya)"),
            ("SLJ-126", "Santal & Myrrhe", "Atmosphere & Home", "Maison Ambience", 250, 4900.00, 1350.00, 90, 35, 15, 4.8, "Mür Reçinesi, Safran", "Sandal Ağacı, Tütsü", "Vanilya, Beyaz Amber", "KozmoPak Lüks Ambalaj A.Ş."),
            ("SLJ-127", "Figuier de Méditerranée", "Niche Perfume", "Botanical Gold", 100, 7200.00, 2150.00, 72, 30, 12, 4.1, "İncir Yaprağı, Mandalina", "İncir Meyvesi, İris", "Hindistan Cevizi, Sedir", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-128", "Rose Noire Extrême", "Extrait de Parfum", "Crown Jewels", 50, 13500.00, 4300.00, 9, 20, 8, 2.0, "Siyah Gül, Safran", "Truffle, Erik Absolüsü", "Karanlık Oud, Vanilya", "Grasse Essences & Pure Oils (Fransa)"),
            ("SLJ-129", "Osmanthus d'Or", "Niche Perfume", "Botanical Gold", 75, 8300.00, 2550.00, 66, 25, 10, 3.7, "Altın Osmanthus, Kayısı", "Çin Çayı, Yasemin", "Süet Deri, Misk", "Drom Fragrances Europe (Almanya)"),
            ("SLJ-130", "Encens Sacred", "Private Blend", "Haute Parfumerie", 100, 12000.00, 3800.00, 38, 25, 10, 3.3, "Oman Tütsüsü, Elemi", "Servi Ağacı, Sedir", "Labdanum, Sıcak Amber", "Grasse Essences & Pure Oils (Fransa)")
        ]
        
        for p in perfumes:
            cursor.execute("""
            INSERT INTO ERP_Products (code, name, category, collection, volume_ml, price_tl, cost_tl, stock, reorder_point, safety_stock, daily_demand, top_notes, heart_notes, base_notes, supplier_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, p)
        conn.commit()

    # Seed & Upsert 15 Corporate Dealers
    dealers = [
        ("DLR-001", "Beymen Lüks Kozmetik A.Ş.", "Büyük Mükellefler V.D.", "1240592817", 5000000.00, 4150000.00, "Ahmet Yılmaz", "dbs@beymen-luxury.com", "+90 212 381 2000"),
        ("DLR-002", "Sephora Türkiye Mağazacılık A.Ş.", "Zincirlikuyu V.D.", "7690184201", 3500000.00, 2900000.00, "Selin Kaya", "finans@sephora.com.tr", "+90 212 373 9000"),
        ("DLR-003", "Harvey Nichols Akasya Boutique", "Kadıköy V.D.", "4520918374", 2500000.00, 2100000.00, "Murat Demir", "muhasebe@harveynichols.com.tr", "+90 216 510 3000"),
        ("DLR-004", "Vakko Perfumery & Beauty", "Beşiktaş V.D.", "9102847162", 4000000.00, 3650000.00, "Deniz Öztürk", "dbs@vakko.com.tr", "+90 212 484 1000"),
        ("DLR-005", "Brandroom Nişantaşı Mağazacılık", "Şişli V.D.", "3810294715", 2000000.00, 1750000.00, "Ece Arslan", "operasyon@brandroom.com.tr", "+90 212 368 4000"),
        ("DLR-006", "Sevil Parfümeri Zinciri", "Bakırköy V.D.", "5520194830", 1500000.00, 1200000.00, "Caner Tekin", "finans@sevil.com.tr", "+90 212 570 1000"),
        ("DLR-007", "Yargıcı Kozmetik ve Yaşam", "Beyoğlu V.D.", "1190284756", 1200000.00, 950000.00, "Zeynep Şahin", "muhasebe@yargici.com.tr", "+90 212 252 2000"),
        ("DLR-008", "Douglas Parfümeri Türkiye", "Ataşehir V.D.", "8829104753", 3000000.00, 2400000.00, "Burak Yıldız", "dbs@douglas.com.tr", "+90 216 468 5000"),
        ("DLR-009", "Boyner Büyük Mağazacılık", "Büyük Mükellefler V.D.", "1829304857", 6000000.00, 5200000.00, "Ayşe Çelik", "finans@boyner.com.tr", "+90 212 335 0000"),
        ("DLR-010", "Watsons Güzellik Mağazaları", "Sarıyer V.D.", "6629104822", 2000000.00, 1800000.00, "Emre Güneş", "muhasebe@watsons.com.tr", "+90 212 345 6000"),
        ("DLR-011", "Rossmann Kozmetik A.Ş.", "Ümraniye V.D.", "4410928371", 2200000.00, 1900000.00, "Gamze Erdem", "dbs@rossmann.com.tr", "+90 216 520 7000"),
        ("DLR-012", "Gratis İç ve Dış Ticaret", "Levent V.D.", "9928104736", 2800000.00, 2450000.00, "Oğuzhan Avcı", "finans@gratis.com", "+90 212 319 8000"),
        ("DLR-013", "Atasoy Lüks Parfümeri", "Fatih V.D.", "3310492819", 1800000.00, 1400000.00, "Mustafa Atasoy", "info@atasoyparfum.com", "+90 212 512 9000"),
        ("DLR-014", "İstinye Parfüm Butik", "Sarıyer V.D.", "7719203845", 3200000.00, 2750000.00, "Hande Soyer", "butik@istinye-parfum.com", "+90 212 345 1200"),
        ("DLR-015", "Kanyon Niche Hub", "Levent V.D.", "5540192837", 4500000.00, 3900000.00, "Barış Kaan", "operasyon@kanyon-niche.com", "+90 212 353 5000")
    ]
    for d in dealers:
        cursor.execute("SELECT COUNT(*) FROM Dealers WHERE code = ?", (d[0],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO Dealers (code, name, tax_office, tax_no, dbs_limit, dbs_available, contact, email, phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", d)
        else:
            cursor.execute("UPDATE Dealers SET name = ?, tax_office = ?, tax_no = ?, dbs_limit = ?, dbs_available = ?, contact = ?, email = ?, phone = ? WHERE code = ?", (d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[0]))
    conn.commit()

    # Seed Suppliers if empty
    cursor.execute("SELECT COUNT(*) FROM ERP_Suppliers")
    if cursor.fetchone()[0] == 0:
        print("[SILLAJÉ ERP DB] Seeding fragrance suppliers...")
        suppliers = [
            ("Grasse Essences & Pure Oils (Fransa)", "Ham Esans & Absolü", 98, 95, 99.2, 98, 3, "supply@grasse-essences.fr"),
            ("Bormioli Luxury Glassware (İtalya)", "Cam Şişe & Kristal", 94, 90, 96.5, 92, 2, "orders@bormioli-luxury.it"),
            ("Silgan Dispensing Systems (İsviçre)", "Valf & Lüks Kapak", 96, 92, 98.0, 95, 4, "b2b@silgandispensing.ch"),
            ("Drom Fragrances Europe (Almanya)", "Özel Niche Formülasyon", 92, 88, 94.0, 90, 2, "info@drom-fragrances.de"),
            ("KozmoPak Lüks Ambalaj A.Ş. (Türkiye)", "Kadife Kutu & Ambalaj", 90, 96, 97.5, 93, 5, "tedarik@kozmopak.com.tr")
        ]
        for s in suppliers:
            cursor.execute("INSERT INTO ERP_Suppliers (name, category, quality_score, speed_score, ontime_rate, reliability_score, active_contracts, contact_email) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", s)
        conn.commit()

    # Seed initial sample invoices if empty
    cursor.execute("SELECT COUNT(*) FROM ERP_Invoices")
    if cursor.fetchone()[0] == 0:
        print("[SILLAJÉ ERP DB] Seeding initial dealer invoices...")
        today = datetime.now().strftime("%Y-%m-%d")
        due30 = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        invoices = [
            ("INV-2026-001", "DLR-001", "Beymen Lüks Kozmetik A.Ş.", today, due30, 850000.00, 170000.00, 680000.00, "Onaylandı", "Bekliyor", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("INV-2026-002", "DLR-002", "Sephora Türkiye Mağazacılık A.Ş.", today, due30, 600000.00, 120000.00, 480000.00, "Onaylandı", "Bekliyor", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("INV-2026-003", "DLR-004", "Vakko Perfumery & Beauty", today, due30, 350000.00, 70000.00, 280000.00, "Onaylandı", "Bekliyor", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        ]
        for inv in invoices:
            cursor.execute("INSERT INTO ERP_Invoices (invoice_no, dealer_code, dealer_name, invoice_date, due_date, total_amount, tax_amount, net_amount, status, dbs_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", inv)
        conn.commit()

    # Seed Initial Bank Mail Inbox
    cursor.execute("SELECT COUNT(*) FROM Bank_Mail_Inbox")
    if cursor.fetchone()[0] == 0:
        print("[SILLAJÉ ERP DB] Seeding initial bank receipt notifications...")
        sample_mail = (
            "DEKONT-20260811-001",
            "Banka Operasyon Platformu <dbs-bildirim@kurumsal-banka.com>",
            "DBS Otomatik Tahsilat Bildirimi - INV-2026-000",
            """<div style='font-family: Arial; color: #e2e8f0; background: #0f172a; padding: 20px; border-radius: 8px;'>
                <h3 style='color: #3b82f6;'>DBS TAHSİLAT DEKONTU</h3>
                <p>Sayın <strong>SILLAJÉ PARFUMS A.Ş.</strong>,</p>
                <p>Bayiniz <strong>Beymen Lüks Kozmetik A.Ş.</strong> adına kayıtlı <strong>INV-2026-000</strong> numaralı faturanın <strong>250.000,00 TL</strong> tutarındaki DBS alacağı başarıyla tahsil edilmiştir ve kurumsal hesabınıza aktarılmıştır.</p>
                <hr style='border: 1px solid #334155;'>
                <p><strong>İşlem Referans No:</strong> DEKONT-20260811-001<br><strong>Tarih:</strong> 2026-08-11 09:30</p>
            </div>""",
            250000.00,
            "INV-2026-000",
            "Beymen Lüks Kozmetik A.Ş.",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            0
        )
        cursor.execute("INSERT INTO Bank_Mail_Inbox (receipt_code, sender, subject, body_html, amount, invoice_no, dealer_name, received_at, is_read) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", sample_mail)
        conn.commit()

    conn.close()
    print("[SILLAJÉ ERP DB] Refined database setup completed successfully.")

if __name__ == "__main__":
    init_erp_db()
