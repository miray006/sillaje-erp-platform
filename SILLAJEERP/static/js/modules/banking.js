/* SILLAJÉ ERP - Banking & DBS Module */
const BankingModule = {
    init() {
        this.startMailInboxPolling();
    },

    async handleSendDBS(invoiceNo, btnElement) {
        let confirmed = false;
        if (window.App && typeof window.App.showConfirmModal === 'function') {
            confirmed = await window.App.showConfirmModal(
                `${invoiceNo} numaralı fatura için Banka Operasyon Platformuna alacak kaydı iletilsin mi?`,
                "Banka Alacak İsteği Onayı"
            );
        } else {
            confirmed = confirm(`${invoiceNo} numaralı fatura için Banka Operasyon Platformuna alacak kaydı iletilsin mi?`);
        }

        if (!confirmed) return;

        const originalText = btnElement.innerHTML;
        btnElement.disabled = true;
        btnElement.innerHTML = `<span class="spinner"></span> İletiliyor...`;

        // Determine target Bank URL for instant redirect
        const isCloud = window.location.hostname.includes("onrender.com");
        const bankTargetUrl = isCloud ? "https://bank-portal-3u87.onrender.com" : "http://127.0.0.1:5001";

        try {
            // Send API POST request asynchronously
            const resPromise = API.sendDBSRequest(invoiceNo);

            if (window.App && typeof window.App.showToast === 'function') {
                window.App.showToast(`${invoiceNo} numaralı fatura Bankaya aktarıldı. Banka sayfasına yönlendiriliyorsunuz...`, "success");
            }

            // Immediately open Bank Platform tab so user is not kept waiting
            setTimeout(() => {
                window.open(bankTargetUrl, "_blank");
            }, 400);

            const res = await resPromise;
            if (window.App) {
                window.App.loadOrders();
                window.App.loadDashboardStats();
            }
        } catch (error) {
            console.warn("sendDBSRequest warning:", error);
            // Even if background API has delay, open Bank page for user
            window.open(bankTargetUrl, "_blank");
        } finally {
            btnElement.disabled = false;
            btnElement.innerHTML = originalText;
        }
    },

    async loadMailInbox() {
        try {
            const data = await API.getMailInbox();
            const mailContainer = document.getElementById("mail-inbox-list");
            const badgeEl = document.getElementById("mail-unread-badge");
            const topBadgeEl = document.getElementById("top-unread-badge");

            if (!mailContainer) return;

            // Update badge counters
            if (badgeEl) {
                badgeEl.innerText = data.unread_count || "0";
                badgeEl.style.display = data.unread_count > 0 ? "inline-block" : "none";
            }
            if (topBadgeEl) {
                topBadgeEl.innerText = data.unread_count || "0";
            }

            if (!data.mails || data.mails.length === 0) {
                mailContainer.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-dim);">Gelen kutusunda banka dekontu veya bildirim bulunmuyor.</div>`;
                return;
            }

            mailContainer.innerHTML = data.mails.map(m => `
                <div class="mail-item ${m.is_read === 0 ? 'unread' : ''}" style="cursor: pointer;" onclick="window.BankingModule.openMailDetail('${m.id}')">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div style="width: 42px; height: 42px; border-radius: 12px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); display: flex; align-items: center; justify-content: center; color: #60A5FA;">
                            <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                        </div>
                        <div>
                            <div class="mail-subject">${m.subject}</div>
                            <div class="mail-meta">Kimden: ${m.sender} &bull; ${m.received_at}</div>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 16px; font-weight: 800; color: #4ADE80;">+${parseFloat(m.amount).toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</div>
                        <span class="badge ${m.is_read === 0 ? 'badge-danger' : 'badge-purple'}">${m.is_read === 0 ? 'Okunmadı' : 'Okundu'}</span>
                    </div>
                </div>
            `).join('');

            // Store current mails globally for modal viewing
            window.currentMails = data.mails;

        } catch (error) {
            console.error("loadMailInbox Error:", error);
        }
    },

    async openMailDetail(mailId) {
        let mails = window.currentMails;
        if (!mails || mails.length === 0) {
            try {
                const res = await API.getMailInbox();
                mails = res.mails || [];
                window.currentMails = mails;
            } catch (e) {
                console.error("Fetch inbox error:", e);
            }
        }
        const mail = (mails || []).find(m => String(m.id) === String(mailId));
        if (!mail) return;

        // Mark read
        if (mail.is_read === 0) {
            await API.markMailRead(mail.id);
            this.loadMailInbox();
        }

        const modal = document.getElementById("mail-detail-modal");
        const bodyEl = document.getElementById("mail-detail-body");

        if (modal && bodyEl) {
            bodyEl.innerHTML = mail.body_html || `<div style="padding: 24px; color: #FFF; font-size: 14px; line-height: 1.6;"><h3 style="color: #60A5FA;">${mail.subject}</h3><p style="margin-top:10px;">Kimden: ${mail.sender}</p><p>Tutar: ${parseFloat(mail.amount).toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</p></div>`;
            modal.classList.add("active");
        }
    },

    closeMailDetail() {
        const modal = document.getElementById("mail-detail-modal");
        if (modal) modal.classList.remove("active");
    },

    startMailInboxPolling() {
        this.loadMailInbox();
        // Poll every 8 seconds for live receipts
        setInterval(() => {
            this.loadMailInbox();
        }, 8000);
    }
};

window.BankingModule = BankingModule;
