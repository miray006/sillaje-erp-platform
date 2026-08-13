-- ====================================================================
-- SILLAJE ERP & BANKA ENTEGRASYONU - MSSQL VERİ TABANI OLUŞTURMA SCRIPT'İ
-- Sunucu: DESKTOP-02AA25J\MSSQLSERVER01
-- Sürücü: ODBC Driver 17 for SQL Server
-- ====================================================================

-- 1. VERİ TABANI OLUŞTURMA
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'SillajeERP')
BEGIN
    CREATE DATABASE SillajeERP;
    PRINT '[BAŞARILI] SillajeERP veri tabanı oluşturuldu.';
END
GO

USE SillajeERP;
GO

-- 2. TABLOLARI TEMİZLE (Varsa Baştan Oluşturmak İçin)
IF OBJECT_ID('dbo.ErpBankaMutabakat', 'U') IS NOT NULL DROP TABLE dbo.ErpBankaMutabakat;
IF OBJECT_ID('dbo.SistemLoglari', 'U') IS NOT NULL DROP TABLE dbo.SistemLoglari;
IF OBJECT_ID('dbo.BankaHareketleri', 'U') IS NOT NULL DROP TABLE dbo.BankaHareketleri;
IF OBJECT_ID('dbo.Faturalar', 'U') IS NOT NULL DROP TABLE dbo.Faturalar;
IF OBJECT_ID('dbo.BankaHesaplari', 'U') IS NOT NULL DROP TABLE dbo.BankaHesaplari;
IF OBJECT_ID('dbo.CariHesaplar', 'U') IS NOT NULL DROP TABLE dbo.CariHesaplar;
GO

-- 3. CARİ HESAPLAR TABLOSU (ERP Müşteri & Tedarikçiler)
CREATE TABLE dbo.CariHesaplar (
    CariId INT IDENTITY(1,1) PRIMARY KEY,
    CariKod NVARCHAR(50) NOT NULL UNIQUE,
    Unvan NVARCHAR(150) NOT NULL,
    VknTckn NVARCHAR(20) NOT NULL,
    Eposta NVARCHAR(100) NULL,
    Telefon NVARCHAR(30) NULL,
    Bakiye DECIMAL(18,2) DEFAULT 0.00,
    OlusturmaTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 4. BANKA HESAPLARI TABLOSU
CREATE TABLE dbo.BankaHesaplari (
    BankaId INT IDENTITY(1,1) PRIMARY KEY,
    BankaAdi NVARCHAR(100) NOT NULL,
    SubeAdi NVARCHAR(100) NULL,
    HesapNo NVARCHAR(50) NOT NULL,
    Iban NVARCHAR(50) NOT NULL UNIQUE,
    ParaBirimi NVARCHAR(10) DEFAULT 'TRY',
    Bakiye DECIMAL(18,2) DEFAULT 0.00,
    OlusturmaTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 5. FATURALAR TABLOSU (ERP Satış / Alış Faturaları)
CREATE TABLE dbo.Faturalar (
    FaturaId INT IDENTITY(1,1) PRIMARY KEY,
    FaturaNo NVARCHAR(50) NOT NULL UNIQUE,
    CariId INT NOT NULL FOREIGN KEY REFERENCES dbo.CariHesaplar(CariId),
    FaturaTipi NVARCHAR(20) NOT NULL CHECK (FaturaTipi IN ('SATIS', 'ALIS')),
    Tutar DECIMAL(18,2) NOT NULL,
    KdvTutar DECIMAL(18,2) DEFAULT 0.00,
    ToplamTutar DECIMAL(18,2) NOT NULL,
    VadeTarihi DATETIME NOT NULL,
    Durum NVARCHAR(20) DEFAULT 'BEKLIYOR' CHECK (Durum IN ('BEKLIYOR', 'ODENDI', 'KISMI_ODENDI', 'IPTAL')),
    OlusturmaTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 6. BANKA HAREKETLERİ TABLOSU (Banka Ekstresi / Gelen-Giden Havale)
CREATE TABLE dbo.BankaHareketleri (
    HareketId INT IDENTITY(1,1) PRIMARY KEY,
    BankaId INT NOT NULL FOREIGN KEY REFERENCES dbo.BankaHesaplari(BankaId),
    IslemTarihi DATETIME DEFAULT GETDATE(),
    IslemTipi NVARCHAR(20) NOT NULL CHECK (IslemTipi IN ('GELEN_TRANSFER', 'GIDEN_TRANSFER', 'KOMISYON')),
    Aciklama NVARCHAR(255) NOT NULL,
    Borc DECIMAL(18,2) DEFAULT 0.00,    -- Çıkan para (Giden Transfer)
    Alacak DECIMAL(18,2) DEFAULT 0.00,  -- Gelen para (Gelen Transfer)
    KarsiIban NVARCHAR(50) NULL,
    GonderenUnvan NVARCHAR(150) NULL,
    GonderenVkn NVARCHAR(20) NULL,
    EslesmeDurumu NVARCHAR(20) DEFAULT 'ESLESMEDI' CHECK (EslesmeDurumu IN ('ESLESMEDI', 'OTOMATIK_ESLESTI', 'MANUEL_ESLESTI'))
);
GO

-- 7. ERP - BANKA MUTABAKAT TABLOSU (Eşleşen Hareketler & Faturalar)
CREATE TABLE dbo.ErpBankaMutabakat (
    MutabakatId INT IDENTITY(1,1) PRIMARY KEY,
    HareketId INT NOT NULL FOREIGN KEY REFERENCES dbo.BankaHareketleri(HareketId),
    FaturaId INT NOT NULL FOREIGN KEY REFERENCES dbo.Faturalar(FaturaId),
    CariId INT NOT NULL FOREIGN KEY REFERENCES dbo.CariHesaplar(CariId),
    EslesmeTutar DECIMAL(18,2) NOT NULL,
    EslesmeTipi NVARCHAR(30) DEFAULT 'OTOMATIK',
    EslesmeSkoru INT DEFAULT 100,
    MutabakatTarihi DATETIME DEFAULT GETDATE()
);
GO

-- 8. SİSTEM LOGLARI TABLOSU
CREATE TABLE dbo.SistemLoglari (
    LogId INT IDENTITY(1,1) PRIMARY KEY,
    LogTipi NVARCHAR(50) DEFAULT 'INFO',
    Mesaj NVARCHAR(MAX) NOT NULL,
    Kaynak NVARCHAR(50) DEFAULT 'MSSQL_INTEGRATION',
    Tarih DATETIME DEFAULT GETDATE()
);
GO

-- 9. BAŞLANGIÇ ÖRNEK VERİLERİNİ MSSQL'E EKLENMESİ (DML)

-- Cariler
INSERT INTO dbo.CariHesaplar (CariKod, Unvan, VknTckn, Eposta, Telefon, Bakiye) VALUES
('CAR-001', 'Anadolu Mobilya Tekstil San. Tic. A.Ş.', '1234567890', 'muhasebe@anadolumobilya.com', '+90 212 555 1010', 47200.00),
('CAR-002', 'Sillaje Luxury Ahşap & Tasarım Ltd.', '9876543210', 'finance@sillajeluxury.com', '+90 212 555 2020', 118000.00),
('CAR-003', 'Borusan Lojistik A.Ş.', '5544332211', 'operasyon@borusanlogistics.com', '+90 212 555 3030', 17700.00);

-- Banka Hesapları
INSERT INTO dbo.BankaHesaplari (BankaAdi, SubeAdi, HesapNo, Iban, ParaBirimi, Bakiye) VALUES
('Anadolu Corporate Bank', 'Maslak Kurumsal Şube', '9901-8847291', 'TR4400062000000099018847291', 'TRY', 845000.00),
('Garanti BBVA', 'Levent Ticari Şube', '4410-1293847', 'TR1200062000000044101293847', 'TRY', 320000.00);

-- Faturalar (ERP tarafında ödeme bekleyen faturalar)
INSERT INTO dbo.Faturalar (FaturaNo, CariId, FaturaTipi, Tutar, KdvTutar, ToplamTutar, VadeTarihi, Durum) VALUES
('FAT-2026-001', 1, 'SATIS', 40000.00, 7200.00, 47200.00, DATEADD(day, 15, GETDATE()), 'BEKLIYOR'),
('FAT-2026-002', 2, 'SATIS', 100000.00, 18000.00, 118000.00, DATEADD(day, 30, GETDATE()), 'BEKLIYOR'),
('FAT-2026-003', 3, 'ALIS', 15000.00, 2700.00, 17700.00, DATEADD(day, 7, GETDATE()), 'BEKLIYOR');

-- Banka Ekstre Hareketleri (Banka sisteminden gelen transferler)
INSERT INTO dbo.BankaHareketleri (BankaId, IslemTarihi, IslemTipi, Aciklama, Borc, Alacak, KarsiIban, GonderenUnvan, GonderenVkn, EslesmeDurumu) VALUES
(1, GETDATE(), 'GELEN_TRANSFER', 'FAT-2026-001 FATURA ODEMESI HKN ÖZTÜRK', 0.00, 47200.00, 'TR550001000200030004000500', 'Anadolu Mobilya Tekstil San. Tic. A.Ş.', '1234567890', 'ESLESMEDI'),
(1, DATEADD(hour, -2, GETDATE()), 'GELEN_TRANSFER', 'SILLAJE LUXURY PROJE AVANSI ÖDEMESİ FAT-2026-002', 0.00, 118000.00, 'TR880001000200030004000500', 'Sillaje Luxury Ahşap & Tasarım Ltd.', '9876543210', 'ESLESMEDI'),
(1, DATEADD(day, -1, GETDATE()), 'GIDEN_TRANSFER', 'NAKLİYE VE LOJİSTİK HİZMET BEDELİ ÖDEMESİ FAT-2026-003', 17700.00, 0.00, 'TR990001000200030004000500', 'Borusan Lojistik A.Ş.', '5544332211', 'ESLESMEDI');

-- Log Kaydı
INSERT INTO dbo.SistemLoglari (LogTipi, Mesaj, Kaynak) VALUES
('INFO', 'MSSQL SillajeERP Veri Tabanı ve Tabloları Başarıyla Oluşturuldu.', 'TSQL_SCHEMA_SETUP');
GO

PRINT '====================================================================';
PRINT '[BAŞARILI] SillajeERP Veri Tabanı, Tabloları ve Örnek Verileri Yüklendi!';
PRINT '====================================================================';
GO
