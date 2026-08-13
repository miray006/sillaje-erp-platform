from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from config import Config
from db import query_all, query_one, execute_cmd, check_mssql_status
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# ----------------------------------------------------
# ARAYÜZ (FRONTEND)
# ----------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

# ----------------------------------------------------
# API ENDPOINT'LERİ (DİREKT MSSQL İLE ÇALIŞIR)
# ----------------------------------------------------

@app.route('/api/status', methods=['GET'])
def get_status():
    """MSSQL Sunucu Bağlantı Sağlık Kontrolü"""
    mssql_info = check_mssql_status()
    return jsonify(mssql_info)

@app.route('/api/dashboard/ozet', methods=['GET'])
def get_dashboard_summary():
    """MSSQL Veri Tabanından Özet İstatistikleri Çeker"""
    try:
        banka_toplam = query_one("SELECT SUM(Bakiye) as ToplamBakiye FROM dbo.BankaHesaplari")
        fatura_ozet = query_one("""
            SELECT 
                COUNT(*) as ToplamFaturaSayisi,
                SUM(CASE WHEN Durum = 'BEKLIYOR' THEN ToplamTutar ELSE 0 END) as BekleyenTutar,
                SUM(CASE WHEN Durum = 'ODENDI' THEN ToplamTutar ELSE 0 END) as TahsilEdilenTutar
            FROM dbo.Faturalar
        """)
        eslesme_ozet = query_one("""
            SELECT 
                COUNT(*) as ToplamHareket,
                SUM(CASE WHEN EslesmeDurumu != 'ESLESMEDI' THEN 1 ELSE 0 END) as EslesenHareketSayisi
            FROM dbo.BankaHareketleri
        """)
        
        return jsonify({
            "status": "success",
            "toplam_banka_bakiye": float(banka_toplam["ToplamBakiye"] or 0) if banka_toplam else 0,
            "bekleyen_fatura_tutar": float(fatura_ozet["BekleyenTutar"] or 0) if fatura_ozet else 0,
            "tahsil_edilen_tutar": float(fatura_ozet["TahsilEdilenTutar"] or 0) if fatura_ozet else 0,
            "toplam_fatura_sayisi": fatura_ozet["ToplamFaturaSayisi"] if fatura_ozet else 0,
            "toplam_hareket": eslesme_ozet["ToplamHareket"] if eslesme_ozet else 0,
            "eslesen_hareket": eslesme_ozet["EslesenHareketSayisi"] if eslesme_ozet else 0
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/banka/hesaplar', methods=['GET'])
def get_banka_hesaplari():
    """MSSQL'den Banka Hesaplarını Çeker"""
    try:
        hesaplar = query_all("SELECT * FROM dbo.BankaHesaplari ORDER BY BankaId ASC")
        for h in hesaplar:
            h['Bakiye'] = float(h['Bakiye'])
            h['OlusturmaTarihi'] = str(h['OlusturmaTarihi'])
        return jsonify({"status": "success", "data": hesaplar})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/banka/hareketler', methods=['GET'])
def get_banka_hareketleri():
    """MSSQL'den Banka Ekstre Hareketlerini Çeker"""
    try:
        sql = """
            SELECT h.*, b.BankaAdi 
            FROM dbo.BankaHareketleri h
            JOIN dbo.BankaHesaplari b ON h.BankaId = b.BankaId
            ORDER BY h.IslemTarihi DESC
        """
        hareketler = query_all(sql)
        for hr in hareketler:
            hr['Borc'] = float(hr['Borc'])
            hr['Alacak'] = float(hr['Alacak'])
            hr['IslemTarihi'] = str(hr['IslemTarihi'])
        return jsonify({"status": "success", "data": hareketler})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/erp/faturalar', methods=['GET'])
def get_erp_faturalar():
    """MSSQL'den ERP Faturalarını Çeker"""
    try:
        sql = """
            SELECT f.*, c.Unvan, c.VknTckn, c.CariKod
            FROM dbo.Faturalar f
            JOIN dbo.CariHesaplar c ON f.CariId = c.CariId
            ORDER BY f.VadeTarihi ASC
        """
        faturalar = query_all(sql)
        for f in faturalar:
            f['Tutar'] = float(f['Tutar'])
            f['KdvTutar'] = float(f['KdvTutar'])
            f['ToplamTutar'] = float(f['ToplamTutar'])
            f['VadeTarihi'] = str(f['VadeTarihi'])
            f['OlusturmaTarihi'] = str(f['OlusturmaTarihi'])
        return jsonify({"status": "success", "data": faturalar})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/erp/cariler', methods=['GET'])
def get_erp_cariler():
    """MSSQL'den Cari Hesapları Çeker"""
    try:
        cariler = query_all("SELECT * FROM dbo.CariHesaplar ORDER BY CariKod ASC")
        for c in cariler:
            c['Bakiye'] = float(c['Bakiye'])
            c['OlusturmaTarihi'] = str(c['OlusturmaTarihi'])
        return jsonify({"status": "success", "data": cariler})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/mutabakat/otomatik', methods=['GET', 'POST'])
def akilli_mutabakat_calistir():
    """
    MSSQL Üzerinde Otomatik Eşleştirme / Mutabakat Motoru.
    Eşleşmemiş banka hareketleri ile bekleyen ERP faturalarını eşleştirir.
    """
    try:
        # Eşleşmemiş gelen transferleri getir
        eslesmeyen_hareketler = query_all("""
            SELECT * FROM dbo.BankaHareketleri 
            WHERE EslesmeDurumu = 'ESLESMEDI' AND Alacak > 0
        """)

        # Ödeme bekleyen satış faturalarını getir
        bekleyen_faturalar = query_all("""
            SELECT f.*, c.VknTckn, c.Unvan 
            FROM dbo.Faturalar f
            JOIN dbo.CariHesaplar c ON f.CariId = c.CariId
            WHERE f.Durum = 'BEKLIYOR' AND f.FaturaTipi = 'SATIS'
        """)

        eslesenler = []

        for h in eslesmeyen_hareketler:
            alacak_tutar = float(h['Alacak'])
            aciklama = h['Aciklama'].upper() if h['Aciklama'] else ""
            gonderen_vkn = h['GonderenVkn']

            for f in bekleyen_faturalar:
                toplam_tutar = float(f['ToplamTutar'])
                fatura_no = f['FaturaNo'].upper()
                cari_vkn = f['VknTckn']

                eslesme_skoru = 0
                eslesme_nedeni = ""

                # Kural 1: Fatura No açıklamada geçiyor mu VE Tutar tam eşit mi? (Skor: 100)
                if fatura_no in aciklama and abs(alacak_tutar - toplam_tutar) < 0.01:
                    eslesme_skoru = 100
                    eslesme_nedeni = f"Fatura No ({fatura_no}) Açıklamada Bulundu ve Tutar Eşit"

                # Kural 2: Gönderen VKN/TCKN tam eşleşiyor VE Tutar tam eşit mi? (Skor: 90)
                elif gonderen_vkn and gonderen_vkn == cari_vkn and abs(alacak_tutar - toplam_tutar) < 0.01:
                    eslesme_skoru = 90
                    eslesme_nedeni = f"VKN/TCKN ({gonderen_vkn}) ve Tutar Tam Eşleşti"

                # Kural 3: Tutar tam eşit mi? (Skor: 75)
                elif abs(alacak_tutar - toplam_tutar) < 0.01:
                    eslesme_skoru = 75
                    eslesme_nedeni = f"Tutar Eşleşti ({alacak_tutar} TRY)"

                if eslesme_skoru > 0:
                    # MSSQL İşlemlerini Başlat (Fatura Ödendi, Hareket Eşleşti, Cari Bakiye Güncellendi, Mutabakat Kaydı Atıldı)
                    execute_cmd(
                        "UPDATE dbo.BankaHareketleri SET EslesmeDurumu = 'OTOMATIK_ESLESTI' WHERE HareketId = ?", 
                        (h['HareketId'],)
                    )
                    execute_cmd(
                        "UPDATE dbo.Faturalar SET Durum = 'ODENDI' WHERE FaturaId = ?", 
                        (f['FaturaId'],)
                    )
                    execute_cmd(
                        "UPDATE dbo.CariHesaplar SET Bakiye = Bakiye - ? WHERE CariId = ?", 
                        (toplam_tutar, f['CariId'])
                    )
                    execute_cmd(
                        """
                        INSERT INTO dbo.ErpBankaMutabakat 
                        (HareketId, FaturaId, CariId, EslesmeTutar, EslesmeTipi, EslesmeSkoru) 
                        VALUES (?, ?, ?, ?, 'OTOMATIK', ?)
                        """,
                        (h['HareketId'], f['FaturaId'], f['CariId'], toplam_tutar, eslesme_skoru)
                    )
                    
                    log_msg = f"[MUTABAKAT BAŞARILI] Hareket #{h['HareketId']} -> Fatura #{f['FaturaNo']} ({eslesme_nedeni})"
                    execute_cmd(
                        "INSERT INTO dbo.SistemLoglari (LogTipi, Mesaj, Kaynak) VALUES ('INFO', ?, 'AUTOMATIC_RECONCILIATION')",
                        (log_msg,)
                    )

                    eslesenler.append({
                        "hareket_id": h['HareketId'],
                        "fatura_no": f['FaturaNo'],
                        "cari_unvan": f['Unvan'],
                        "tutar": toplam_tutar,
                        "skor": eslesme_skoru,
                        "neden": eslesme_nedeni
                    })
                    break

        return jsonify({
            "status": "success",
            "toplam_eslesen": len(eslesenler),
            "eslesme_detaylari": eslesenler
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/banka/transfer', methods=['POST'])
def yeni_banka_transferi():
    """Banka Hesabından Yeni Gelen/Giden Transfer Kaydı (MSSQL'e Direkt Yazar)"""
    try:
        data = request.json
        banka_id = data.get('banka_id', 1)
        islem_tipi = data.get('islem_tipi', 'GELEN_TRANSFER') # GELEN_TRANSFER / GIDEN_TRANSFER
        tutar = float(data.get('tutar', 0))
        aciklama = data.get('aciklama', '')
        gonderen_unvan = data.get('gonderen_unvan', '')
        gonderen_vkn = data.get('gonderen_vkn', '')
        karsi_iban = data.get('karsi_iban', '')

        if tutar <= 0:
            return jsonify({"status": "error", "message": "Tutar 0'dan büyük olmalıdır."}), 400

        borc = tutar if islem_tipi == 'GIDEN_TRANSFER' else 0.0
        alacak = tutar if islem_tipi == 'GELEN_TRANSFER' else 0.0

        # MSSQL Hareket Kaydı
        execute_cmd("""
            INSERT INTO dbo.BankaHareketleri 
            (BankaId, IslemTarihi, IslemTipi, Aciklama, Borc, Alacak, KarsiIban, GonderenUnvan, GonderenVkn, EslesmeDurumu)
            VALUES (?, GETDATE(), ?, ?, ?, ?, ?, ?, ?, 'ESLESMEDI')
        """, (banka_id, islem_tipi, aciklama, borc, alacak, karsi_iban, gonderen_unvan, gonderen_vkn))

        # Banka Bakiyesi Güncelleme
        if islem_tipi == 'GELEN_TRANSFER':
            execute_cmd("UPDATE dbo.BankaHesaplari SET Bakiye = Bakiye + ? WHERE BankaId = ?", (tutar, banka_id))
        else:
            execute_cmd("UPDATE dbo.BankaHesaplari SET Bakiye = Bakiye - ? WHERE BankaId = ?", (tutar, banka_id))

        execute_cmd(
            "INSERT INTO dbo.SistemLoglari (LogTipi, Mesaj, Kaynak) VALUES ('INFO', ?, 'BANK_TRANSFER_API')",
            (f"Yeni {islem_tipi}: {tutar} TRY - {gonderen_unvan} ({aciklama})",)
        )

        return jsonify({"status": "success", "message": "Banka hareketi MSSQL'e başarıyla eklendi."})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/loglar', methods=['GET'])
def get_system_logs():
    """MSSQL'deki Sistem Loglarını Getirir"""
    try:
        loglar = query_all("SELECT TOP 20 * FROM dbo.SistemLoglari ORDER BY Tarih DESC")
        for l in loglar:
            l['Tarih'] = str(l['Tarih'])
        return jsonify({"status": "success", "data": loglar})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print(f"[*] Sillaje ERP & Banka Entegrasyon Servisi Başlatılıyor...")
    print(f"[*] MSSQL Bağlantı Dizesi: {Config.SQLALCHEMY_DATABASE_URI}")
    app.run(host='0.0.0.0', port=Config.PORT, debug=False)
