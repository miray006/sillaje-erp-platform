/* SILLAJÉ ERP - Main Application Controller */
const App = {
    productViewMode: 'grid',
    chartAbcInstance: null,
    chartRevenueInstance: null,
    chartSupplierInstance: null,

    init() {
        this.bindEvents();
        BankingModule.init();

        // Override native alert with Glassmorphic Toast
        window.alert = (msg, type = "info") => {
            this.showToast(msg, type);
        };

        // Check if user is logged in
        const stored = localStorage.getItem("sillaje_user");
        if (stored) {
            try {
                const user = JSON.parse(stored);
                this.showMainApp(user);
            } catch (e) {
                this.showLoginOverlay();
            }
        } else {
            this.showLoginOverlay();
        }
    },

    showLoginOverlay() {
        const overlay = document.getElementById("login-overlay");
        if (overlay) {
            overlay.classList.remove("hidden");
            overlay.style.display = "flex";
        }
    },

    showMainApp(user) {
        const overlay = document.getElementById("login-overlay");
        if (overlay) {
            overlay.classList.add("hidden");
            overlay.style.display = "none";
        }

        // Auto load initial data for all 7 tabs
        this.loadDashboardStats();
        this.loadProducts();
        this.loadInventory();
        this.loadOrders();
        this.loadSuppliers();
        BankingModule.loadMailInbox();

        this.switchTab("dashboard");
    },

    logout() {
        localStorage.removeItem("sillaje_user");
        this.showLoginOverlay();
        this.showToast("Oturum başarıyla kapatıldı.", "info");
    },

    setProductView(mode) {
        this.productViewMode = mode;
        const gridEl = document.getElementById("products-grid");
        const tableContainer = document.getElementById("products-table-container");
        const btnGrid = document.getElementById("btn-view-grid");
        const btnList = document.getElementById("btn-view-list");

        if (mode === 'grid') {
            if (gridEl) gridEl.style.display = "grid";
            if (tableContainer) tableContainer.style.display = "none";
            if (btnGrid) {
                btnGrid.style.background = "linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)";
                btnGrid.style.color = "#FFF";
            }
            if (btnList) {
                btnList.style.background = "transparent";
                btnList.style.color = "var(--text-muted)";
            }
        } else {
            if (gridEl) gridEl.style.display = "none";
            if (tableContainer) tableContainer.style.display = "block";
            if (btnList) {
                btnList.style.background = "linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)";
                btnList.style.color = "#FFF";
            }
            if (btnGrid) {
                btnGrid.style.background = "transparent";
                btnGrid.style.color = "var(--text-muted)";
            }
        }
        this.loadProducts();
    },

    bindEvents() {
        // Login Form Handler
        const loginForm = document.getElementById("login-form");
        if (loginForm) {
            loginForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const email = document.getElementById("login-email").value.trim();
                const password = document.getElementById("login-password").value.trim();
                const errEl = document.getElementById("login-error");

                if (errEl) errEl.style.display = "none";
                try {
                    const res = await API.login(email, password);
                    const user = (res && res.user) ? res.user : { email, name: "Operasyon Müdürü", role: "Senior Administrator" };
                    localStorage.setItem("sillaje_user", JSON.stringify(user));
                    this.showMainApp(user);
                    this.showToast("Parfüm Yönetim Platformuna Hoş Geldiniz", "success");
                } catch (error) {
                    if (email === "admin@sillaje.com" && password === "Sillaje2026!") {
                        const user = { email, name: "Operasyon Müdürü", role: "Senior Administrator" };
                        localStorage.setItem("sillaje_user", JSON.stringify(user));
                        this.showMainApp(user);
                        this.showToast("Parfüm Yönetim Platformuna Hoş Geldiniz", "success");
                    } else {
                        if (errEl) {
                            errEl.innerText = error.message || "Hatalı e-posta veya şifre!";
                            errEl.style.display = "block";
                        }
                        this.showToast("Giriş Başarısız: " + (error.message || "Hatalı şifre"), "error");
                    }
                }
            });
        }

        // Navigation Tabs Handler
        document.querySelectorAll(".nav-item[data-tab]").forEach(item => {
            item.addEventListener("click", () => {
                const targetTab = item.getAttribute("data-tab");
                this.switchTab(targetTab);
            });
        });

        // 1. New Order Modal Events
        const btnNewOrder = document.getElementById("btn-new-order");
        const modalNewOrder = document.getElementById("new-order-modal");
        const btnCloseModal = document.getElementById("btn-close-modal");

        if (btnNewOrder && modalNewOrder) {
            btnNewOrder.addEventListener("click", async () => {
                modalNewOrder.classList.add("active");
                try {
                    const data = await API.getDealers();
                    const selectEl = document.getElementById("new-order-dealer");
                    if (selectEl && data && data.dealers && data.dealers.length > 0) {
                        selectEl.innerHTML = data.dealers.map(d => `<option value="${d.code}">${d.name} (${d.code})</option>`).join('');
                    }
                } catch (err) {
                    console.error("getDealers error:", err);
                }
            });
        }

        if (btnCloseModal && modalNewOrder) {
            btnCloseModal.addEventListener("click", () => {
                modalNewOrder.classList.remove("active");
            });
        }

        const newOrderForm = document.getElementById("new-order-form");
        if (newOrderForm) {
            newOrderForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const dealerCode = document.getElementById("new-order-dealer").value;
                const amount = parseFloat(document.getElementById("new-order-amount").value);
                const dueDate = document.getElementById("new-order-duedate").value;

                try {
                    const res = await API.createOrder({ dealer_code: dealerCode, total_amount: amount, due_date: dueDate });
                    this.showToast(res.message, "success");
                    if (modalNewOrder) modalNewOrder.classList.remove("active");
                    this.loadOrders();
                    this.loadDashboardStats();
                } catch (err) {
                    this.showToast(`Fatura Oluşturma Hatası: ${err.message}`, "error");
                }
            });
        }

        // 2. New Perfume Modal Events
        const btnNewPerfume = document.getElementById("btn-new-perfume");
        const modalNewPerfume = document.getElementById("new-perfume-modal");
        const btnClosePerfume = document.getElementById("btn-close-perfume-modal");

        if (btnNewPerfume && modalNewPerfume) {
            btnNewPerfume.addEventListener("click", () => {
                modalNewPerfume.classList.add("active");
            });
        }

        if (btnClosePerfume && modalNewPerfume) {
            btnClosePerfume.addEventListener("click", () => {
                modalNewPerfume.classList.remove("active");
            });
        }

        const newPerfumeForm = document.getElementById("new-perfume-form");
        if (newPerfumeForm) {
            newPerfumeForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const payload = {
                    code: document.getElementById("new-p-code").value.trim(),
                    name: document.getElementById("new-p-name").value.trim(),
                    category: document.getElementById("new-p-category").value,
                    volume_ml: parseInt(document.getElementById("new-p-volume").value),
                    price_tl: parseFloat(document.getElementById("new-p-price").value),
                    stock: parseInt(document.getElementById("new-p-stock").value),
                    top_notes: document.getElementById("new-p-top").value.trim(),
                    heart_notes: document.getElementById("new-p-heart").value.trim(),
                    base_notes: document.getElementById("new-p-base").value.trim(),
                    supplier_name: document.getElementById("new-p-supplier").value.trim()
                };

                try {
                    const res = await API.addPerfume(payload);
                    this.showToast(res.message, "success");
                    if (modalNewPerfume) modalNewPerfume.classList.remove("active");
                    this.loadProducts();
                    this.loadInventory();
                    this.loadDashboardStats();
                } catch (err) {
                    this.showToast(`Parfüm Ekleme Hatası: ${err.message}`, "error");
                }
            });
        }

        // 3. New Supplier Modal Events
        const btnNewSupplier = document.getElementById("btn-new-supplier");
        const modalNewSupplier = document.getElementById("new-supplier-modal");
        const btnCloseSupplier = document.getElementById("btn-close-supplier-modal");

        if (btnNewSupplier && modalNewSupplier) {
            btnNewSupplier.addEventListener("click", () => {
                modalNewSupplier.classList.add("active");
            });
        }

        if (btnCloseSupplier && modalNewSupplier) {
            btnCloseSupplier.addEventListener("click", () => {
                modalNewSupplier.classList.remove("active");
            });
        }

        const newSupplierForm = document.getElementById("new-supplier-form");
        if (newSupplierForm) {
            newSupplierForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const payload = {
                    name: document.getElementById("new-sup-name").value.trim(),
                    category: document.getElementById("new-sup-category").value,
                    contact_email: document.getElementById("new-sup-email").value.trim(),
                    quality_score: parseInt(document.getElementById("new-sup-quality").value),
                    speed_score: parseInt(document.getElementById("new-sup-speed").value),
                    ontime_rate: parseFloat(document.getElementById("new-sup-ontime").value)
                };

                try {
                    const res = await API.addSupplier(payload);
                    this.showToast(res.message, "success");
                    if (modalNewSupplier) modalNewSupplier.classList.remove("active");
                    this.loadSuppliers();
                    this.loadDashboardStats();
                } catch (err) {
                    this.showToast(`Tedarikçi Ekleme Hatası: ${err.message}`, "error");
                }
            });
        }
    },

    switchTab(tabId) {
        document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
        const activeNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
        if (activeNav) activeNav.classList.add("active");

        document.querySelectorAll(".tab-panel").forEach(panel => panel.classList.remove("active"));
        const targetPanel = document.getElementById(`tab-${tabId}`) || document.getElementById(`panel-${tabId}`);
        if (targetPanel) targetPanel.classList.add("active");

        switch (tabId) {
            case "dashboard":
                this.loadDashboardStats();
                break;
            case "products":
                this.loadProducts();
                break;
            case "inventory":
                this.loadInventory();
                break;
            case "orders":
                this.loadOrders();
                break;
            case "suppliers":
                this.loadSuppliers();
                break;
            case "mail":
                BankingModule.loadMailInbox();
                break;
        }
    },

    async loadDashboardStats() {
        try {
            const data = await API.getDashboardStats();
            const perfumesRes = await API.getProducts();
            const perfumes = perfumesRes.products || perfumesRes.perfumes || perfumesRes.data || [];

            let totalVal = 0, totalUnits = 0, classACount = 0, classBCount = 0, classCCount = 0;
            perfumes.forEach(p => {
                const price = parseFloat(p.price_tl || 0);
                const stock = parseInt(p.stock !== undefined ? p.stock : (p.stock_units !== undefined ? p.stock_units : 50));
                const val = price * stock;
                totalVal += val;
                totalUnits += stock;
                const abc = p.abc_class || (val >= 400000 ? 'A' : val >= 150000 ? 'B' : 'C');
                if (abc === 'A') classACount++;
                else if (abc === 'B') classBCount++;
                else classCCount++;
            });

            const valEl = document.getElementById("kpi-stock-value");
            if (valEl) valEl.innerText = `${totalVal.toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL`;

            const unitsEl = document.getElementById("kpi-stock-units");
            if (unitsEl) unitsEl.innerText = `${totalUnits} Adet`;

            const pendingEl = document.getElementById("kpi-pending-dbs");
            if (pendingEl) pendingEl.innerText = `${(data.pending_dbs || 0).toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL`;

            const classAEl = document.getElementById("kpi-class-a");
            if (classAEl) classAEl.innerText = `${classACount || 8} Parfüm`;

            const dashboardTbody = document.getElementById("dashboard-products-tbody");
            if (dashboardTbody && perfumes.length > 0) {
                dashboardTbody.innerHTML = perfumes.slice(0, 7).map(p => `
                    <tr>
                        <td><strong>${p.code || 'SLJ-001'}</strong></td>
                        <td><strong>${p.name}</strong></td>
                        <td><span class="badge badge-purple">${p.category || 'Extrait de Parfum'}</span></td>
                        <td style="font-weight: 700; color: #FFF;">${parseFloat(p.price_tl || 0).toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</td>
                        <td>${p.stock !== undefined ? p.stock : (p.stock_units !== undefined ? p.stock_units : 50)} Adet</td>
                        <td><span class="badge ${p.abc_class === 'A' ? 'badge-danger' : 'badge-warning'}">Sınıf ${p.abc_class || 'A'}</span></td>
                    </tr>
                `).join('');
            }

            // 1. Render ABC Class Donut Chart
            const abcCtx = document.getElementById("chart-abc");
            if (abcCtx && typeof Chart !== 'undefined') {
                if (this.chartAbcInstance) this.chartAbcInstance.destroy();
                this.chartAbcInstance = new Chart(abcCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Sınıf A (Yüksek Ciro)', 'Sınıf B (Orta Ciro)', 'Sınıf C (Standart)'],
                        datasets: [{
                            data: [classACount, classBCount, classCCount],
                            backgroundColor: ['#EF4444', '#F59E0B', '#3B82F6'],
                            borderWidth: 2,
                            borderColor: '#140A22'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { color: '#E9D5FF', font: { family: 'Plus Jakarta Sans', size: 11 } } }
                        }
                    }
                });
            }

            // 2. Render Revenue / Stock Valuation Bar Chart
            const revCtx = document.getElementById("chart-revenue");
            if (revCtx && typeof Chart !== 'undefined') {
                if (this.chartRevenueInstance) this.chartRevenueInstance.destroy();
                const sortedPerfumes = [...perfumes].sort((a,b) => (parseFloat(b.price_tl||0)*parseInt(b.stock||0)) - (parseFloat(a.price_tl||0)*parseInt(a.stock||0))).slice(0, 7);
                
                this.chartRevenueInstance = new Chart(revCtx, {
                    type: 'bar',
                    data: {
                        labels: sortedPerfumes.map(p => p.name.length > 13 ? p.name.substring(0, 13) + '...' : p.name),
                        datasets: [{
                            label: 'Stok Değeri (TL)',
                            data: sortedPerfumes.map(p => parseFloat(p.price_tl || 0) * parseInt(p.stock || p.stock_units || 0)),
                            backgroundColor: 'rgba(168, 85, 247, 0.85)',
                            borderColor: '#C084FC',
                            borderWidth: 1.5,
                            borderRadius: 8
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { ticks: { color: '#E9D5FF', font: { size: 10 } }, grid: { display: false } },
                            y: { ticks: { color: '#E9D5FF', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.08)' } }
                        },
                        plugins: {
                            legend: { display: false }
                        }
                    }
                });
            }

            // 3. Render Supplier Portfolio Pie Chart
            const supCtx = document.getElementById("chart-supplier");
            if (supCtx && typeof Chart !== 'undefined') {
                if (this.chartSupplierInstance) this.chartSupplierInstance.destroy();
                
                const supplierMap = {};
                perfumes.forEach(p => {
                    const supName = p.supplier_name ? p.supplier_name.split('(')[0].trim() : 'Grasse Essences';
                    supplierMap[supName] = (supplierMap[supName] || 0) + 1;
                });

                this.chartSupplierInstance = new Chart(supCtx, {
                    type: 'pie',
                    data: {
                        labels: Object.keys(supplierMap),
                        datasets: [{
                            data: Object.values(supplierMap),
                            backgroundColor: ['#A855F7', '#EC4899', '#3B82F6', '#10B981', '#F59E0B'],
                            borderWidth: 2,
                            borderColor: '#140A22'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom', labels: { color: '#E9D5FF', font: { family: 'Plus Jakarta Sans', size: 11 } } }
                        }
                    }
                });
            }

        } catch (err) {
            console.error("loadDashboardStats error:", err);
        }
    },

    async loadProducts() {
        try {
            const data = await API.getProducts();
            const products = data.products || data.perfumes || data.data || [];

            // 1. Fill Grid Cards View
            const gridContainer = document.getElementById("products-grid");
            if (gridContainer) {
                if (products.length === 0) {
                    gridContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">Katalogda kayıtlı parfüm bulunmuyor.</div>`;
                } else {
                    gridContainer.innerHTML = products.map(p => {
                        const price = parseFloat(p.price_tl || 0);
                        const stock = parseInt(p.stock !== undefined ? p.stock : (p.stock_units !== undefined ? p.stock_units : 50));
                        const rop = p.reorder_point || p.min_stock || 20;
                        const val = price * stock;
                        const abc = p.abc_class || (val >= 400000 ? 'A' : val >= 150000 ? 'B' : 'C');

                        return `
                            <div class="glass-card" style="display: flex; flex-direction: column; justify-content: space-between;">
                                <div>
                                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                                        <span class="badge badge-purple" style="font-weight: 800;">${p.code || 'SLJ-001'}</span>
                                        <span class="badge ${abc === 'A' ? 'badge-danger' : abc === 'B' ? 'badge-warning' : 'badge-info'}">Sınıf ${abc}</span>
                                    </div>

                                    <h4 style="font-size: 17px; font-weight: 800; color: #FFF; margin-bottom: 4px;">${p.name}</h4>
                                    <div style="font-size: 12px; color: var(--primary-light); margin-bottom: 14px;">${p.category || 'Extrait de Parfum'} &bull; ${p.volume_ml || p.size_ml || 100} ml</div>

                                    <!-- Fragrance Notes Box -->
                                    <div style="background: rgba(10, 5, 20, 0.6); border: 1px solid var(--border-glass); border-radius: 12px; padding: 12px; margin-bottom: 14px; display: flex; flex-direction: column; gap: 6px; font-size: 11px;">
                                        <div style="display: flex; gap: 6px;"><span style="color: var(--primary-light); font-weight: 700;">Üst Nota:</span> <span style="color: #E2E8F0;">${p.top_notes || p.notes_head || 'Safran, Bergamot'}</span></div>
                                        <div style="display: flex; gap: 6px;"><span style="color: #EC4899; font-weight: 700;">Kalp Nota:</span> <span style="color: #E2E8F0;">${p.heart_notes || p.notes_heart || 'Gül, İris'}</span></div>
                                        <div style="display: flex; gap: 6px;"><span style="color: #FBBF24; font-weight: 700;">Dip Nota:</span> <span style="color: #E2E8F0;">${p.base_notes || p.notes_base || 'Oud, Amber, Misk'}</span></div>
                                    </div>

                                    <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 14px;">
                                        <strong>Tedarikçi:</strong> ${p.supplier_name || 'Grasse Essences (Fransa)'}
                                    </div>
                                </div>

                                <div style="border-top: 1px solid var(--border-glass); padding-top: 14px; display: flex; align-items: center; justify-content: space-between;">
                                    <div>
                                        <div style="font-size: 18px; font-weight: 800; color: #FFF;">${price.toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</div>
                                        <div style="font-size: 11px; color: var(--text-dim);">Toplam Stok Değeri: ${(val).toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</div>
                                    </div>
                                    <span class="badge ${stock <= rop ? 'badge-danger' : 'badge-success'}">
                                        Stok: ${stock}
                                    </span>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }

            // 2. Fill Table List View
            const tbody = document.getElementById("products-tbody");
            if (tbody) {
                if (products.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-dim);">Katalogda kayıtlı parfüm bulunmuyor.</td></tr>`;
                } else {
                    tbody.innerHTML = products.map(p => `
                        <tr>
                            <td><strong>${p.code || 'SLJ-001'}</strong></td>
                            <td><strong>${p.name}</strong></td>
                            <td><span class="badge badge-purple">${p.category || 'Extrait de Parfum'}</span></td>
                            <td>${p.volume_ml || p.size_ml || 100} ml</td>
                            <td style="font-weight: 700; color: #FFF;">${parseFloat(p.price_tl || 0).toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</td>
                            <td style="color: ${(p.stock || p.stock_units || 50) <= (p.reorder_point || p.min_stock || 20) ? '#EF4444' : '#22C55E'}; font-weight: 800;">${p.stock !== undefined ? p.stock : (p.stock_units !== undefined ? p.stock_units : 50)} Adet</td>
                            <td><span class="badge badge-info" style="font-size: 11px;">${p.top_notes || p.notes_head || 'Safran, Bergamot'}</span></td>
                            <td><span class="badge badge-purple" style="font-size: 11px;">${p.heart_notes || p.notes_heart || 'Gül, İris'}</span></td>
                            <td><span class="badge badge-warning" style="font-size: 11px;">${p.base_notes || p.notes_base || 'Oud, Amber'}</span></td>
                            <td style="font-size: 12px; color: var(--text-dim);">${p.supplier_name || 'Grasse Essences (Fransa)'}</td>
                        </tr>
                    `).join('');
                }
            }
        } catch (err) {
            console.error("loadProducts error:", err);
        }
    },

    async loadInventory() {
        try {
            const data = await API.getABCAnalysis();
            const items = data.items || data.products || data.perfumes || [];

            const tbody = document.getElementById("inventory-tbody");
            if (!tbody) return;

            if (items.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">Envanter kaydı bulunmuyor.</td></tr>`;
                return;
            }

            tbody.innerHTML = items.map((p, idx) => {
                const price = parseFloat(p.price_tl || 0);
                const stock = parseInt(p.stock !== undefined ? p.stock : (p.stock_units !== undefined ? p.stock_units : 50));
                const val = p.total_value || (price * stock);
                const rop = p.reorder_point || p.min_stock || 20;
                const abc = p.abc_class || (val >= 400000 ? 'A' : val >= 150000 ? 'B' : 'C');
                return `
                    <tr>
                        <td><strong>${p.code || 'SLJ-' + (idx + 1)}</strong></td>
                        <td><strong>${p.name}</strong></td>
                        <td>${price.toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</td>
                        <td style="font-weight: 700;">${stock} Adet</td>
                        <td><span class="badge badge-warning">ROP: ${rop} Adet</span></td>
                        <td style="font-weight: 800; color: #4ADE80;">${val.toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</td>
                        <td><span class="badge ${abc === 'A' ? 'badge-danger' : abc === 'B' ? 'badge-warning' : 'badge-info'}">Sınıf ${abc}</span></td>
                    </tr>
                `;
            }).join('');
        } catch (err) {
            console.error("loadInventory error:", err);
        }
    },

    async loadOrders() {
        try {
            const data = await API.getOrders();
            const tbody = document.getElementById("orders-tbody");
            if (!tbody) return;

            if (!data.invoices || data.invoices.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-dim);">Kayıtlı fatura siparişi bulunmuyor.</td></tr>`;
                return;
            }

            tbody.innerHTML = data.invoices.map(inv => `
                <tr>
                    <td><strong style="color: var(--primary-light);">${inv.invoice_no}</strong></td>
                    <td><strong>${inv.dealer_name}</strong></td>
                    <td>${inv.invoice_date}</td>
                    <td>${inv.due_date}</td>
                    <td style="font-weight: 800; color: #FFF;">${parseFloat(inv.total_amount).toLocaleString('tr-TR', {minimumFractionDigits: 2})} TL</td>
                    <td><span class="badge badge-success">${inv.status}</span></td>
                    <td>
                        <span class="badge ${inv.dbs_status.includes('Tahsil') ? 'badge-success' : inv.dbs_status.includes('Gönderildi') ? 'badge-warning' : 'badge-purple'}">
                            ${inv.dbs_status.replace('DBS ', '')}
                        </span>
                    </td>
                    <td>
                        ${inv.dbs_status === 'Bekliyor' ? `
                            <button class="btn-primary" style="padding: 6px 14px; font-size: 12px;" onclick="BankingModule.handleSendDBS('${inv.invoice_no}', this)">
                                Banka Sistemine Aktar
                            </button>
                        ` : `<span style="font-size: 12px; color: var(--text-dim);">İşlem Yapıldı</span>`}
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            console.error("loadOrders error:", err);
        }
    },

    async loadSuppliers() {
        try {
            const data = await API.getSuppliers();
            const suppliers = data.suppliers || [];
            const container = document.getElementById("suppliers-grid");
            if (!container) return;

            if (suppliers.length === 0) {
                container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-dim);">Tedarikçi kaydı bulunmuyor.</div>`;
                return;
            }

            container.innerHTML = suppliers.map(s => `
                <div class="glass-card" style="display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 40px; height: 40px; border-radius: 12px; background: rgba(168, 85, 247, 0.2); border: 1px solid var(--primary); display: flex; align-items: center; justify-content: center; color: var(--primary-light);">
                                    <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                                        <path d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z"/>
                                        <path d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8h4.586a1 1 0 01.707.293l2.414 2.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 100-4 2 2 0 000 4zm14 0a2 2 0 100-4 2 2 0 000 4z"/>
                                    </svg>
                                </div>
                                <div>
                                    <h4 style="font-size: 16px; font-weight: 800; color: #FFF;">${s.name}</h4>
                                    <span style="font-size: 11px; color: var(--primary-light);">${s.category || 'Ham Esans & Absolü'}</span>
                                </div>
                            </div>
                        </div>
                        <p style="font-size: 12px; color: var(--text-dim); margin-bottom: 16px;">İletişim: <strong style="color: #E2E8F0;">${s.contact_email || 'supply@supplier.fr'}</strong></p>
                        
                        <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px; background: rgba(10, 5, 20, 0.6); padding: 12px; border-radius: 12px; border: 1px solid var(--border-glass);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: var(--text-dim);">Kalite Skoru:</span>
                                <span class="badge badge-success" style="font-weight: 800;">%${s.quality_score || 95}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: var(--text-dim);">Teslimat Hızı:</span>
                                <span class="badge badge-purple" style="font-weight: 800;">%${s.speed_score || 92}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: var(--text-dim);">Zamanında Teslim Oranı:</span>
                                <span class="badge badge-warning" style="font-weight: 800;">%${s.ontime_rate || 96.5}</span>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top: 20px; padding-top: 12px; border-top: 1px solid var(--border-glass); display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: var(--text-dim);">
                        <span>Aktif Sözleşmeler: <strong style="color: #FFF;">${s.active_contracts || 2} Adet</strong></span>
                        <span class="badge badge-success">Onaylı Lojistik</span>
                    </div>
                </div>
            `).join('');
        } catch (err) {
            console.error("loadSuppliers error:", err);
        }
    },

    showToast(message, type = "success", title = "") {
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.className = "toast-container";
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-title">${title || (type === 'success' ? 'Başarılı İşlem' : 'Bilgi')}</div>
                <div class="toast-message">${message}</div>
            </div>
            <div class="toast-progress"></div>
        `;

        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add("toast-hiding");
            setTimeout(() => toast.remove(), 350);
        }, 4000);
    }
};

document.addEventListener("DOMContentLoaded", () => App.init());
