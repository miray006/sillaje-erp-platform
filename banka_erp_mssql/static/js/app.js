document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadMssqlStatus();
    loadDashboardData();
    bindEvents();
});

// ----------------------------------------------------
// TAB NAVIGATION
// ----------------------------------------------------
function initNavigation() {
    const navButtons = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');

            navButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const activeTabContent = document.getElementById(`tab-${targetTab}`);
            if (activeTabContent) {
                activeTabContent.classList.add('active');
            }

            // Tab özel yüklemeler
            if (targetTab === 'banka') loadBankaHareketleri();
            if (targetTab === 'erp') loadErpFaturalar();
            if (targetTab === 'loglar') loadSystemLogs();
        });
    });
}

// ----------------------------------------------------
// BİND EVENT HANDLERS
// ----------------------------------------------------
function bindEvents() {
    document.getElementById('btnRefresh')?.addEventListener('click', refreshAllData);
    document.getElementById('btnRunSync')?.addEventListener('click', runAutomaticSync);
    document.getElementById('btnRunSyncLarge')?.addEventListener('click', runAutomaticSync);
    
    // Transfer Form Submit
    document.getElementById('formTransfer')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        await submitNewTransfer();
    });
}

function refreshAllData() {
    loadMssqlStatus();
    loadDashboardData();
    loadBankaHareketleri();
    loadErpFaturalar();
    loadSystemLogs();
}

// ----------------------------------------------------
// API ÇAĞRILARI VE VERİ YÜKLEME
// ----------------------------------------------------

async function loadMssqlStatus() {
    const badge = document.getElementById('mssqlStatusBadge');
    const indicator = badge.querySelector('.status-indicator');
    const serverNameSpan = document.getElementById('mssqlServerName');
    const infoServerName = document.getElementById('infoServerName');

    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        if (data.status === 'connected') {
            indicator.className = 'status-indicator connected';
            serverNameSpan.textContent = data.server || 'MSSQLSERVER01';
            if (infoServerName) infoServerName.textContent = data.server;
            badge.title = `MSSQL Bağlantısı Aktif: ${data.version}`;
        } else {
            indicator.className = 'status-indicator error';
            serverNameSpan.textContent = 'Bağlantı Hatası';
            badge.title = data.error_message || 'MSSQL sunucusuna ulaşılamadı';
        }
    } catch (err) {
        indicator.className = 'status-indicator error';
        serverNameSpan.textContent = 'Çevrimdışı';
    }
}

async function loadDashboardData() {
    try {
        const res = await fetch('/api/dashboard/ozet');
        const data = await res.json();

        if (data.status === 'success') {
            document.getElementById('valBankaBakiye').textContent = formatCurrency(data.toplam_banka_bakiye);
            document.getElementById('valBekleyenTutar').textContent = formatCurrency(data.bekleyen_fatura_tutar);
            document.getElementById('valTahsilTutar').textContent = formatCurrency(data.tahsil_edilen_tutar);
            document.getElementById('valBekleyenFaturaSayi').textContent = `${data.toplam_fatura_sayisi} Bekleyen Fatura`;

            const toplamHareket = data.toplam_hareket || 1;
            const eslesen = data.eslesen_hareket || 0;
            const oran = Math.round((eslesen / toplamHareket) * 100);
            
            document.getElementById('valEslesmeOran').textContent = `%${oran}`;
            document.getElementById('valEslesmeDetay').textContent = `${eslesen} / ${toplamHareket} Hareket Eşleşti`;
        }

        // Hesap ve Cari Özet Tabloları
        loadBankaHesapOzet();
        loadCariOzet();

    } catch (err) {
        console.error("Dashboard yükleme hatası:", err);
    }
}

async function loadBankaHesapOzet() {
    try {
        const res = await fetch('/api/banka/hesaplar');
        const result = await res.json();
        const tbody = document.querySelector('#tblBankaHesapozet tbody');
        if (!tbody) return;

        if (result.status === 'success' && result.data.length > 0) {
            tbody.innerHTML = result.data.map(h => `
                <tr>
                    <td><strong>${h.BankaAdi}</strong></td>
                    <td>${h.SubeAdi || '-'}</td>
                    <td><code>${h.Iban}</code></td>
                    <td class="text-success"><strong>${formatCurrency(h.Bakiye)}</strong></td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Banka hesabı bulunamadı.</td></tr>';
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadCariOzet() {
    try {
        const res = await fetch('/api/erp/cariler');
        const result = await res.json();
        const tbody = document.querySelector('#tblCariOzet tbody');
        if (!tbody) return;

        if (result.status === 'success' && result.data.length > 0) {
            tbody.innerHTML = result.data.map(c => `
                <tr>
                    <td><code>${c.CariKod}</code></td>
                    <td><strong>${c.Unvan}</strong></td>
                    <td>${c.VknTckn}</td>
                    <td class="${c.Bakiye > 0 ? 'text-warning' : 'text-success'}">
                        <strong>${formatCurrency(c.Bakiye)}</strong>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Cari hesap bulunamadı.</td></tr>';
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadBankaHareketleri() {
    try {
        const res = await fetch('/api/banka/hareketler');
        const result = await res.json();
        const tbody = document.querySelector('#tblBankaHareketleri tbody');
        if (!tbody) return;

        if (result.status === 'success' && result.data.length > 0) {
            tbody.innerHTML = result.data.map(hr => {
                const isGelen = hr.Alacak > 0;
                const tutar = isGelen ? hr.Alacak : hr.Borc;
                const badgeClass = hr.EslesmeDurumu === 'ESLESMEDI' ? 'badge-warning' : 'badge-success';
                const durumText = hr.EslesmeDurumu === 'ESLESMEDI' ? 'Eşleşmedi' : 'Otomatik Eşleşti';

                return `
                    <tr>
                        <td>#${hr.HareketId}</td>
                        <td>${formatDate(hr.IslemTarihi)}</td>
                        <td>${hr.BankaAdi}</td>
                        <td>
                            <span class="badge ${isGelen ? 'badge-success' : 'badge-secondary'}">
                                ${isGelen ? '<i class="fa-solid fa-arrow-down"></i> GELEN' : '<i class="fa-solid fa-arrow-up"></i> GİDEN'}
                            </span>
                        </td>
                        <td>${hr.Aciklama}</td>
                        <td>${hr.GonderenUnvan || '-'} <br><small class="text-muted">${hr.GonderenVkn || ''}</small></td>
                        <td class="${isGelen ? 'text-success' : ''}"><strong>${formatCurrency(tutar)}</strong></td>
                        <td><span class="badge ${badgeClass}">${durumText}</span></td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Banka ekstresi boş.</td></tr>';
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadErpFaturalar() {
    try {
        const res = await fetch('/api/erp/faturalar');
        const result = await res.json();
        const tbody = document.querySelector('#tblErpFaturalar tbody');
        if (!tbody) return;

        if (result.status === 'success' && result.data.length > 0) {
            tbody.innerHTML = result.data.map(f => {
                const isOdendi = f.Durum === 'ODENDI';
                const badgeClass = isOdendi ? 'badge-success' : 'badge-warning';

                return `
                    <tr>
                        <td><code>${f.FaturaNo}</code></td>
                        <td><strong>${f.Unvan}</strong></td>
                        <td>${f.VknTckn}</td>
                        <td><span class="badge badge-secondary">${f.FaturaTipi}</span></td>
                        <td>${formatDate(f.VadeTarihi)}</td>
                        <td><strong>${formatCurrency(f.ToplamTutar)}</strong></td>
                        <td><span class="badge ${badgeClass}">${isOdendi ? 'ÖDENDİ' : 'BEKLİYOR'}</span></td>
                    </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">ERP fatura kaydı yok.</td></tr>';
        }
    } catch (e) {
        console.error(e);
    }
}

async function runAutomaticSync() {
    const btnContainer = document.getElementById('mutabakatResultsContainer');
    btnContainer.innerHTML = '<p class="text-center py-4"><i class="fa-solid fa-spinner fa-spin"></i> MSSQL veri tabanı üzerinde eşleştirme yapılıyor...</p>';

    try {
        const res = await fetch('/api/mutabakat/otomatik', { method: 'POST' });
        const data = await res.json();

        if (data.status === 'success') {
            if (data.toplam_eslesen > 0) {
                btnContainer.innerHTML = `
                    <div class="alert alert-success mb-3" style="background: rgba(16,185,129,0.15); padding: 12px; border-radius: 8px; border: 1px solid rgba(16,185,129,0.3);">
                        <strong><i class="fa-solid fa-circle-check"></i> ${data.toplam_eslesen} Adet Fatura ve Ekstre Hareketi Başarıyla Eşleştirildi!</strong>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Hareket ID</th>
                                <th>Fatura No</th>
                                <th>Cari Unvan</th>
                                <th>Tutar</th>
                                <th>Güven Skoru</th>
                                <th>Eşleşme Nedeni</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.eslesme_detaylari.map(d => `
                                <tr>
                                    <td>#${d.hareket_id}</td>
                                    <td><code>${d.fatura_no}</code></td>
                                    <td>${d.cari_unvan}</td>
                                    <td class="text-success"><strong>${formatCurrency(d.tutar)}</strong></td>
                                    <td><span class="badge badge-success">%${d.skor}</span></td>
                                    <td>${d.neden}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } else {
                btnContainer.innerHTML = '<p class="text-muted text-center py-4"><i class="fa-solid fa-info-circle"></i> Eşleştirilecek yeni açık fatura veya ekstre hareketi bulunamadı (Tüm kayıtlar güncel).</p>';
            }

            refreshAllData();
        } else {
            btnContainer.innerHTML = `<p class="text-danger text-center py-4">Hata: ${data.message}</p>`;
        }

    } catch (e) {
        btnContainer.innerHTML = `<p class="text-danger text-center py-4">İşlem hatası oluştu.</p>`;
    }
}

async function submitNewTransfer() {
    const payload = {
        banka_id: 1,
        islem_tipi: document.getElementById('trIslemTipi').value,
        gonderen_unvan: document.getElementById('trGonderenUnvan').value,
        gonderen_vkn: document.getElementById('trGonderenVkn').value,
        tutar: document.getElementById('trTutar').value,
        aciklama: document.getElementById('trAciklama').value
    };

    try {
        const res = await fetch('/api/banka/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.status === 'success') {
            toggleModal('modalTransfer');
            document.getElementById('formTransfer').reset();
            refreshAllData();
        } else {
            alert('Hata: ' + data.message);
        }
    } catch (e) {
        alert('İşlem kaydedilirken sunucu hatası oluştu.');
    }
}

async function loadSystemLogs() {
    try {
        const res = await fetch('/api/loglar');
        const result = await res.json();
        const logUl = document.getElementById('sysLogList');
        if (!logUl) return;

        if (result.status === 'success' && result.data.length > 0) {
            logUl.innerHTML = result.data.map(l => `
                <li class="log-item">
                    <span>[${l.Kaynak}] ${l.Mesaj}</span>
                    <span class="log-time">${l.Tarih}</span>
                </li>
            `).join('');
        } else {
            logUl.innerHTML = '<li class="text-muted p-3">Log kaydı bulunamadı.</li>';
        }
    } catch (e) {
        console.error(e);
    }
}

// ----------------------------------------------------
// UTILS
// ----------------------------------------------------
function toggleModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.toggle('active');
}

function formatCurrency(val) {
    return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(val || 0);
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('tr-TR') + ' ' + d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return dateStr;
    }
}
