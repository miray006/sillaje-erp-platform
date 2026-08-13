from flask import Flask, render_template, request, jsonify, session, send_from_directory
import pyodbc
import sqlite3
import os
import requests
from datetime import datetime
from bank_setup import BankConfig, get_bank_db_connection, init_bank_db

BANK_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BANK_BASE_DIR, 'static'),
    template_folder=os.path.join(BANK_BASE_DIR, 'templates')
)
app.secret_key = "corporate-bank-portal-secret-2026"

# Run setup on launch
init_bank_db()

is_render = os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_HOSTNAME')
default_webhook_url = "https://sillaje-erp.onrender.com/api/webhook/mail-gonder" if is_render else "http://127.0.0.1:5000/api/webhook/mail-gonder"
ERP_WEBHOOK_URL = os.environ.get('ERP_WEBHOOK_URL', default_webhook_url)

@app.after_request
def add_header(response):
    """Prevents browser from caching bank portal HTML/API responses."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

def dict_from_row(cursor, row):
    if hasattr(row, 'keys'):
        d = dict(row)
    else:
        columns = [column[0] for column in cursor.description]
        d = dict(zip(columns, row))

    for k in ['dbs_limit', 'used_limit', 'available_limit', 'amount']:
        if k in d and d[k] is not None:
            try:
                d[k] = float(d[k])
            except Exception:
                pass
    return d

def sync_dealer_limits(cursor):
    """Dynamically recalculates used_limit and available_limit for all dealers based on pending receivables."""
    try:
        cursor.execute("SELECT dealer_code, SUM(amount) FROM Bank_DBS_Transactions WHERE status = 'Bekliyor' GROUP BY dealer_code")
        pending_rows = cursor.fetchall()
        pending_map = {}
        for r in pending_rows:
            d_code = r[0]
            sum_amt = float(r[1] or 0)
            pending_map[d_code] = sum_amt

        cursor.execute("SELECT id, dealer_code, dbs_limit FROM Bank_Dealers")
        dealer_rows = cursor.fetchall()
        for d in dealer_rows:
            d_id = d[0]
            d_code = d[1]
            dbs_limit = float(d[2] or 0)
            used = pending_map.get(d_code, 0.0)
            available = max(0.0, dbs_limit - used)
            cursor.execute("UPDATE Bank_Dealers SET used_limit = ?, available_limit = ? WHERE id = ?", (used, available, d_id))
    except Exception as e:
        print("[BANK WARN] sync_dealer_limits error:", e)

@app.route("/")
def index():
    return render_template("bank_portal.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(os.path.join(BANK_BASE_DIR, "static"), filename)

@app.route("/api/login", methods=["POST"])
def login():
    """Handles bank platform operator login."""
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if email == "banka@kurumsal-banka.com" and password == "Banka2026!":
        session["bank_user"] = {"email": email, "role": "Hazine Operasyon Müdürü"}
        return jsonify({"status": "success", "user": session["bank_user"]})
    
    return jsonify({"status": "error", "message": "Hatalı e-posta veya şifre!"}), 401

@app.route("/api/dbs/fatura-kayit", methods=["POST"])
def register_dbs_invoice():
    """Endpoint called by SILLAJÉ ERP when submitting a payment request."""
    try:
        data = request.json or {}
        invoice_no = data.get("invoice_no") or data.get("fatura_no")
        dealer_code = data.get("dealer_code") or data.get("bayi_kodu")
        dealer_name = data.get("dealer_name") or data.get("bayi_adi")
        amount = float(data.get("amount") or data.get("tutar") or 0)
        due_date = data.get("due_date") or data.get("vade_tarihi") or datetime.now().strftime("%Y-%m-%d")

        if not invoice_no or not dealer_code or amount <= 0:
            return jsonify({"status": "error", "message": "Geçersiz fatura veya bayi verisi."}), 400

        conn, engine = get_bank_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM Bank_DBS_Transactions WHERE invoice_no = ?", (invoice_no,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"status": "warning", "message": "Bu fatura için alacak kaydı zaten mevcut."}), 200

        dbs_ref = f"BNK-REF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
        INSERT INTO Bank_DBS_Transactions (dbs_ref, dealer_code, dealer_name, invoice_no, amount, due_date, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Bekliyor', ?)
        """, (dbs_ref, dealer_code, dealer_name, invoice_no, amount, due_date, now_str))

        cursor.execute("""
        INSERT INTO Bank_Logs (action, details, created_at)
        VALUES ('BNK_FATURA_KAYIT', ?, ?)
        """, (f"ERP'den yeni BNK alacak kaydı alındı: {invoice_no} - Ref: {dbs_ref} - Tutar: {amount:,.2f} TL - Bayi: {dealer_name}", now_str))

        sync_dealer_limits(cursor)

        conn.commit()
        conn.close()

        print(f"[BANKA PORTALI] Yeni alacak kaydı yapıldı: {dbs_ref} ({invoice_no})")
        return jsonify({
            "status": "success",
            "message": "Alacak kaydı Banka Operasyon Platformu sistemine başarıyla işlendi.",
            "dbs_ref": dbs_ref
        }), 200

    except Exception as e:
        print("[BANKA ERROR] fatura-kayit error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/dbs/receivables", methods=["GET"])
@app.route("/api/bank/transactions", methods=["GET"])
def get_receivables():
    """Returns all pending and processed transactions with dynamically calculated dealer credit limits."""
    try:
        conn, engine = get_bank_db_connection()
        cursor = conn.cursor()

        sync_dealer_limits(cursor)
        conn.commit()

        cursor.execute("SELECT * FROM Bank_DBS_Transactions ORDER BY id DESC")
        rows = cursor.fetchall()
        transactions = [dict_from_row(cursor, r) for r in rows]

        cursor.execute("SELECT * FROM Bank_Dealers ORDER BY id ASC")
        dealer_rows = cursor.fetchall()
        dealers = [dict_from_row(cursor, r) for r in dealer_rows]

        conn.close()
        return jsonify({
            "status": "success",
            "transactions": transactions,
            "receivables": transactions,
            "dealers": dealers
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/bank/accounts", methods=["GET"])
def get_bank_accounts():
    """Returns bank dealers and credit limits for accounts tab."""
    try:
        conn, engine = get_bank_db_connection()
        cursor = conn.cursor()
        sync_dealer_limits(cursor)
        conn.commit()

        cursor.execute("SELECT * FROM Bank_Dealers ORDER BY id ASC")
        rows = cursor.fetchall()
        dealers = [dict_from_row(cursor, r) for r in rows]
        conn.close()
        return jsonify({"status": "success", "accounts": dealers, "dealers": dealers})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/bank/mail-outbox", methods=["GET"])
def get_mail_outbox():
    """Returns dispatch email logs."""
    try:
        conn, engine = get_bank_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Bank_Logs WHERE action LIKE '%TAHSILAT%' OR details LIKE '%Dekont%' ORDER BY id DESC")
        rows = cursor.fetchall()
        logs = [dict_from_row(cursor, r) for r in rows]
        conn.close()
        return jsonify({"status": "success", "outbox": logs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/dbs/collect", methods=["POST"])
@app.route("/api/bank/collect", methods=["POST"])
def collect_dbs():
    """Triggers collection of receivables, updates dealer credit limits, and posts webhook email notification back to SILLAJÉ ERP."""
    try:
        data = request.json or {}
        transaction_id = data.get("transaction_id")
        
        conn, engine = get_bank_db_connection()
        cursor = conn.cursor()

        if transaction_id:
            cursor.execute("SELECT * FROM Bank_DBS_Transactions WHERE id = ? AND status = 'Bekliyor'", (transaction_id,))
        else:
            cursor.execute("SELECT * FROM Bank_DBS_Transactions WHERE status = 'Bekliyor'")
        
        rows = cursor.fetchall()
        pending_txs = [dict_from_row(cursor, r) for r in rows]

        if not pending_txs:
            conn.close()
            return jsonify({"status": "info", "message": "Tahsil edilecek vadesi gelmiş/bekleyen alacak bulunamadı."})

        collected_count = 0
        total_collected = 0.0

        for tx in pending_txs:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            receipt_code = f"DEKONT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{tx['id']}"
            
            cursor.execute("""
            UPDATE Bank_DBS_Transactions 
            SET status = 'Tahsil Edildi', processed_at = ?, receipt_code = ?
            WHERE id = ?
            """, (now_str, receipt_code, tx['id']))

            cursor.execute("""
            INSERT INTO Bank_Logs (action, details, created_at)
            VALUES ('BNK_TAHSILAT', ?, ?)
            """, (f"BNK Tahsilatı gerçekleştirildi. Dekont No: {receipt_code} - Tutar: {tx['amount']:,.2f} TL - Fatura: {tx['invoice_no']}", now_str))

            collected_count += 1
            total_collected += float(tx['amount'])

            email_payload = {
                "receipt_code": receipt_code,
                "sender": "Banka Operasyon Platformu <operasyon@kurumsal-banka.com>",
                "subject": f"BNK Otomatik Tahsilat Bildirimi - {tx['invoice_no']}",
                "amount": float(tx['amount']),
                "invoice_no": tx['invoice_no'],
                "dealer_name": tx['dealer_name'],
                "received_at": now_str,
                "body_html": f"""
                <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; background: #0b0f19; color: #f8fafc; padding: 24px; border-radius: 12px; border: 1px solid #1e293b;">
                    <div style="display: flex; justify-content: space-between; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 16px;">
                        <h2 style="color: #3b82f6; margin: 0; font-size: 20px;">BNK ELEKTRONİK TAHSİLAT DEKONTU</h2>
                        <span style="background: #10b981; color: #ffffff; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;">ONAYLANDI</span>
                    </div>
                    <p style="font-size: 14px; color: #cbd5e1;">Sayın <strong>SILLAJÉ PARFUMS A.Ş.</strong> Finans Yönetimi,</p>
                    <p style="font-size: 14px; color: #cbd5e1;">Banka Operasyon Platformu kapsamında bayiniz <strong>{tx['dealer_name']}</strong> hesabından <strong>{tx['invoice_no']}</strong> numaralı faturanıza istinaden <strong>{float(tx['amount']):,.2f} TL</strong> tutarındaki alacak tahsil edilmiş ve kurumsal hesabınıza aktarılmıştır.</p>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; color: #e2e8f0;">
                        <tr style="background: #1e293b;"><td style="padding: 8px 12px; font-weight: bold;">Banka Dekont No:</td><td style="padding: 8px 12px;">{receipt_code}</td></tr>
                        <tr><td style="padding: 8px 12px; font-weight: bold;">İşlem Tarihi:</td><td style="padding: 8px 12px;">{now_str}</td></tr>
                        <tr style="background: #1e293b;"><td style="padding: 8px 12px; font-weight: bold;">Fatura Tutar:</td><td style="padding: 8px 12px; color: #10b981; font-weight: bold;">{float(tx['amount']):,.2f} TL</td></tr>
                        <tr><td style="padding: 8px 12px; font-weight: bold;">Borçlu Bayi:</td><td style="padding: 8px 12px;">{tx['dealer_name']} ({tx['dealer_code']})</td></tr>
                    </table>
                    <p style="font-size: 12px; color: #64748b; margin-top: 20px; text-align: center;">Bu e-posta Banka Operasyon Platformu Otomatik Tahsilat Servisi tarafından üretilmiştir.</p>
                </div>
                """
            }

            # Multi-target Webhook retry mechanism for ERP notification
            webhook_targets = [
                ERP_WEBHOOK_URL,
                "https://sillaje-erp.onrender.com/api/webhook/mail-gonder",
                "http://127.0.0.1:5000/api/webhook/mail-gonder"
            ]
            unique_webhooks = list(dict.fromkeys(webhook_targets))

            for w_url in unique_webhooks:
                try:
                    resp = requests.post(w_url, json=email_payload, timeout=5)
                    if resp.status_code in [200, 201]:
                        print(f"[BANKA WEBHOOK] Webhook post delivered to ERP via {w_url} for {receipt_code}")
                        break
                except Exception as webhook_err:
                    print(f"[BANKA WEBHOOK WARN] Target {w_url} failed: {webhook_err}")

        sync_dealer_limits(cursor)

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"Toplam {collected_count} adet alacak ({total_collected:,.2f} TL) başarıyla tahsil edildi ve SILLAJÉ ERP sistemine bildirim gönderildi.",
            "collected_count": collected_count,
            "total_collected": total_collected
        })

    except Exception as e:
        print("[BANKA ERROR] collect_dbs error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/logs", methods=["GET"])
def get_logs():
    try:
        conn, engine = get_bank_db_connection()
        cursor = conn.cursor()
        if engine == "MSSQL":
            cursor.execute("SELECT TOP 50 * FROM Bank_Logs ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM Bank_Logs ORDER BY id DESC LIMIT 50")
        rows = cursor.fetchall()
        logs = [dict_from_row(cursor, r) for r in rows]
        conn.close()
        return jsonify({"status": "success", "logs": logs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("[BANKA OPERASYON PLATFORMU] Starting dev server on http://127.0.0.1:5001 ...")
    app.run(host="127.0.0.1", port=5001, debug=True, use_reloader=False)
