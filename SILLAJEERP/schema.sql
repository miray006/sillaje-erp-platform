-- ====================================================================
-- SILLAJE ERP & BANKA OPERASYON PLATFORMU - TEK VERİ TABANI SCRIPT'İ
-- Veri Tabanı Adı: SILLAJE_BANK_ERP_PRO_DB
-- Sunucu: DESKTOP-02AA25J\MSSQLSERVER01
-- Sürücü: ODBC Driver 17 for SQL Server
-- ====================================================================

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'SILLAJE_BANK_ERP_PRO_DB')
BEGIN
    CREATE DATABASE SILLAJE_BANK_ERP_PRO_DB;
    PRINT '[BAŞARILI] SILLAJE_BANK_ERP_PRO_DB veri tabanı oluşturuldu.';
END
GO

USE SILLAJE_BANK_ERP_PRO_DB;
GO

-- 1. ESKİ TABLOLARI TEMİZLE (Sıfırdan Temiz Kurulum)
IF OBJECT_ID('dbo.ErpMailInbox', 'U') IS NOT NULL DROP TABLE dbo.ErpMailInbox;
IF OBJECT_ID('dbo.BankaMailOutbox', 'U') IS NOT NULL DROP TABLE dbo.BankaMailOutbox;
IF OBJECT_ID('dbo.BankaIslemler', 'U') IS NOT NULL DROP TABLE dbo.BankaIslemler;
IF OBJECT_ID('dbo.BankaAlacaklar', 'U') IS NOT NULL DROP TABLE dbo.BankaAlacaklar;
IF OBJECT_ID('dbo.Faturalar', 'U') IS NOT NULL DROP TABLE dbo.Faturalar;
IF OBJECT_ID('dbo.Bayiler', 'U') IS NOT NULL DROP TABLE dbo.Bayiler;
IF OBJECT_ID('dbo.Tedarikciler', 'U') IS NOT NULL DROP TABLE dbo.Tedarikciler;
IF OBJECT_ID('dbo.Urunler', 'U') IS NOT NULL DROP TABLE dbo.Urunler;
IF OBJECT_ID('dbo.Kullanicilar', 'U') IS NOT NULL DROP TABLE dbo.Kullanicilar;
GO

-- 2. KULLANICILAR TABLOSU (ERP Ayarlar & Giriş)
CREATE TABLE dbo.Kullanicilar (
    KullaniciId INT IDENTITY(1,1) PRIMARY KEY,
    Eposta NVARCHAR(100) NOT NULL UNIQUE,
    Sifre NVARCHAR(100) NOT NULL,
    AdSoyad NVARCHAR(100) NOT NULL,
    Unvan NVARCHAR(100) DEFAULT 'Kurumsal Yönetici',
    SonGirisTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 3. ÜRÜNLER TABLOSU (Lüks Parfüm Koleksiyonu & ABC / ROP)
CREATE TABLE dbo.Urunler (
    UrunId INT IDENTITY(1,1) PRIMARY KEY,
    UrunKod NVARCHAR(50) NOT NULL UNIQUE,
    UrunAdi NVARCHAR(150) NOT NULL,
    Kategori NVARCHAR(50) DEFAULT 'Haute Parfumerie',
    UstNota NVARCHAR(150),
    OrtaNota NVARCHAR(150),
    DipNota NVARCHAR(150),
    Fiyat DECIMAL(18,2) NOT NULL,
    Stok INT NOT NULL DEFAULT 0,
    ROP INT NOT NULL DEFAULT 15, -- Reorder Point (Sipariş Verme Noktası)
    AbcSinifi CHAR(1) DEFAULT 'A', -- A, B, C
    GorselUrl NVARCHAR(255) NULL
);
GO

-- 4. TEDARİKÇİLER TABLOSU (Fransa / İtalya Hammadde Verimliliği)
CREATE TABLE dbo.Tedarikciler (
    TedarikciId INT IDENTITY(1,1) PRIMARY KEY,
    TedarikciAdi NVARCHAR(150) NOT NULL,
    Ulke NVARCHAR(50) NOT NULL,
    KaliteSkoru INT CHECK (KaliteSkoru BETWEEN 0 AND 100),
    TeslimatHiziDays INT NOT NULL,
    ZamanindaTeslimatOrani INT CHECK (ZamanindaTeslimatOrani BETWEEN 0 AND 100),
    Durum NVARCHAR(20) DEFAULT 'AKTIF'
);
GO

-- 5. BAYİLER TABLOSU (Kurumsal Beymen, Sephora vb. Kredi Limitleri)
CREATE TABLE dbo.Bayiler (
    BayiId INT IDENTITY(1,1) PRIMARY KEY,
    BayiKod NVARCHAR(50) NOT NULL UNIQUE,
    BayiUnvan NVARCHAR(150) NOT NULL,
    VknTckn NVARCHAR(20) NOT NULL,
    Eposta NVARCHAR(100) NOT NULL,
    Telefon NVARCHAR(30) NULL,
    KrediLimiti DECIMAL(18,2) DEFAULT 500000.00,
    RiskTutari DECIMAL(18,2) DEFAULT 0.00,
    KullanilabilirLimit AS (KrediLimiti - RiskTutari)
);
GO

-- 6. FATURALAR TABLOSU (ERP Bayi Siparişleri & DBS)
CREATE TABLE dbo.Faturalar (
    FaturaId INT IDENTITY(1,1) PRIMARY KEY,
    FaturaNo NVARCHAR(50) NOT NULL UNIQUE,
    BayiId INT NOT NULL FOREIGN KEY REFERENCES dbo.Bayiler(BayiId),
    Tutar DECIMAL(18,2) NOT NULL,
    KdvTutar DECIMAL(18,2) NOT NULL,
    ToplamTutar DECIMAL(18,2) NOT NULL,
    VadeTarihi DATETIME NOT NULL,
    Durum NVARCHAR(30) DEFAULT 'BEKLIYOR' CHECK (Durum IN ('BEKLIYOR', 'BANKAYA_ILETIKDI', 'TAHSILEDILDI', 'IPTAL')),
    OlusturmaTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 7. BANKA BEKLEYEN ALACAKLAR TABLOSU (Banka Back-Office Receivables)
CREATE TABLE dbo.BankaAlacaklar (
    AlacakId INT IDENTITY(1,1) PRIMARY KEY,
    DbsRefNo NVARCHAR(50) NOT NULL UNIQUE,
    FaturaId INT NOT NULL FOREIGN KEY REFERENCES dbo.Faturalar(FaturaId),
    BayiId INT NOT NULL FOREIGN KEY REFERENCES dbo.Bayiler(BayiId),
    Tutar DECIMAL(18,2) NOT NULL,
    VadeTarihi DATETIME NOT NULL,
    Durum NVARCHAR(30) DEFAULT 'BEKLIYOR' CHECK (Durum IN ('BEKLIYOR', 'TAHSILEDILDI', 'REDDEDILDI')),
    KayitTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 8. BANKA GERÇEKLEŞEN İŞLEMLER TABLOSU (Bank Operations History)
CREATE TABLE dbo.BankaIslemler (
    IslemId INT IDENTITY(1,1) PRIMARY KEY,
    DekontNo NVARCHAR(50) NOT NULL UNIQUE,
    AlacakId INT NOT NULL FOREIGN KEY REFERENCES dbo.BankaAlacaklar(AlacakId),
    BayiId INT NOT NULL FOREIGN KEY REFERENCES dbo.Bayiler(BayiId),
    Tutar DECIMAL(18,2) NOT NULL,
    IslemTarihi DATETIME DEFAULT GETDATE(),
    Aciklama NVARCHAR(255) NOT NULL
);
GO

-- 9. BANKA E-POSTA ÇIKIŞLARI LOG TABLOSU (Mail Outbox / Webhook Log)
CREATE TABLE dbo.BankaMailOutbox (
    MailId INT IDENTITY(1,1) PRIMARY KEY,
    DekontNo NVARCHAR(50) NOT NULL,
    AliciEposta NVARCHAR(100) NOT NULL,
    Konu NVARCHAR(200) NOT NULL,
    Icerik NVARCHAR(MAX) NOT NULL,
    HttpStatusCode INT DEFAULT 200,
    GonderimTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 10. ERP GELEN KUTUSU TABLOSU (Mail Inbox)
CREATE TABLE dbo.ErpMailInbox (
    InboxId INT IDENTITY(1,1) PRIMARY KEY,
    DekontNo NVARCHAR(50) NOT NULL,
    Gonderen NVARCHAR(100) DEFAULT 'Anadolu Corporate Bank <dbs@anadolubank.com>',
    Konu NVARCHAR(200) NOT NULL,
    Icerik NVARCHAR(MAX) NOT NULL,
    OkunduMu BIT DEFAULT 0,
    Tarih DATETIME DEFAULT GETDATE()
);
GO

-- ====================================================================
-- ÖRNEK KURUMSAL VERİLERİN YÜKLENMESİ (DML)
-- ====================================================================

-- Varsayılan Kullanıcı
INSERT INTO dbo.Kullanicilar (Eposta, Sifre, AdSoyad, Unvan) VALUES
('admin@sillaje.com', 'Sillaje2026!', 'Hakan Öztürk', 'Lüks Ürünler ve Finans Direktörü');

-- Parfüm Koleksiyonu
INSERT INTO dbo.Urunler (UrunKod, UrunAdi, Kategori, UstNota, OrtaNota, DipNota, Fiyat, Stok, ROP, AbcSinifi) VALUES
('PRF-001', 'Sillajé Royal Oud Extract', 'Haute Parfumerie', 'Safran, Bergamot', 'Kamboçya Udu, Gül', 'Deri, Amber, Misk', 18500.00, 45, 15, 'A'),
('PRF-002', 'Sillajé Black Rose Nectar', 'Haute Parfumerie', 'Siyah Gül, Pembe Biber', 'Isparta Gülü, Yasemin', 'Sedir Ağacı, Vanilya', 14200.00, 80, 20, 'A'),
('PRF-003', 'Sillajé Imperial Iris Extrait', 'Haute Parfumerie', 'Floransa İrisi, İncir Yaprağı', 'Menekşe Kökü, Süsen', 'Sandal Ağacı, Beyaz Misk', 12500.00, 18, 25, 'B'),
('PRF-004', 'Sillajé Amber Mystique', 'Private Blend', 'Amber, Tarçın', 'Tütün Yaprağı, Bal', 'Tonka Fasulyesi, Kakao', 9800.00, 12, 15, 'C');

-- Tedarikçiler
INSERT INTO dbo.Tedarikciler (TedarikciAdi, Ulke, KaliteSkoru, TeslimatHiziDays, ZamanindaTeslimatOrani, Durum) VALUES
('Grasse Essential Oils SA', 'Fransa', 98, 4, 96, 'AKTIF'),
('Milano Glass & Flacon SRL', 'İtalya', 94, 6, 92, 'AKTIF'),
('Provence Rose Farming Ltd.', 'Fransa', 99, 3, 98, 'AKTIF');

-- Bayiler & Kredi Limitleri
INSERT INTO dbo.Bayiler (BayiKod, BayiUnvan, VknTckn, Eposta, KrediLimiti, RiskTutari) VALUES
('BAYI-001', 'Beymen Lüks Mağazacılık A.Ş.', '1234567890', 'finans@beymen.com', 2500000.00, 185000.00),
('BAYI-002', 'Sephora Kozmetik A.Ş.', '9876543210', 'accounting@sephora.com.tr', 1800000.00, 142000.00),
('BAYI-003', 'Harvey Nichols Istanbul', '5544332211', 'dbs@harveynichols.com', 1200000.00, 0.00);

-- ERP Faturaları
INSERT INTO dbo.Faturalar (FaturaNo, BayiId, Tutar, KdvTutar, ToplamTutar, VadeTarihi, Durum) VALUES
('FAT-2026-101', 1, 150000.00, 35000.00, 185000.00, DATEADD(day, 15, GETDATE()), 'BANKAYA_ILETIKDI'),
('FAT-2026-102', 2, 120000.00, 22000.00, 142000.00, DATEADD(day, 30, GETDATE()), 'BANKAYA_ILETIKDI');

-- Banka Bekleyen Alacaklar
INSERT INTO dbo.BankaAlacaklar (DbsRefNo, FaturaId, BayiId, Tutar, VadeTarihi, Durum) VALUES
('DBS-REF-2026-001', 1, 1, 185000.00, DATEADD(day, 15, GETDATE()), 'BEKLIYOR'),
('DBS-REF-2026-002', 2, 2, 142000.00, DATEADD(day, 30, GETDATE()), 'BEKLIYOR');

PRINT '====================================================================';
PRINT '[BAŞARILI] SILLAJE_BANK_ERP_PRO_DB ve Tüm Tablolar MSSQL Üzerine Yüklendi!';
PRINT '====================================================================';
GO
