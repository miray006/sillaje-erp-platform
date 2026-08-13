/* SILLAJÉ ERP - API Service Module */
const API = {
    async request(endpoint, options = {}) {
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        options.headers = { ...defaultHeaders, ...options.headers };

        try {
            const response = await fetch(endpoint, options);
            const data = await response.json();
            if (!response.ok && data.status === 'error') {
                throw new Error(data.message || 'API İsteği Başarısız.');
            }
            return data;
        } catch (error) {
            console.error(`[API Error] ${endpoint}:`, error);
            throw error;
        }
    },

    // Authentication
    login(email, password) {
        return this.request('/api/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
    },

    // Dashboard Stats
    getDashboardStats() {
        return this.request('/api/dashboard/stats');
    },

    // Products
    getProducts(search = '', category = '') {
        const query = new URLSearchParams({ search, category }).toString();
        return this.request(`/api/products?${query}`);
    },

    addProduct(productData) {
        return this.request('/api/products/add', {
            method: 'POST',
            body: JSON.stringify(productData)
        });
    },

    addPerfume(productData) {
        return this.addProduct(productData);
    },

    // Inventory & ABC Analysis
    getABCAnalysis() {
        return this.request('/api/inventory/abc-analysis');
    },

    // Orders & DBS
    getOrders() {
        return this.request('/api/orders');
    },

    createOrder(orderData, amount, dueDate) {
        let payload = orderData;
        if (typeof orderData === 'string') {
            payload = { dealer_code: orderData, total_amount: amount, due_date: dueDate };
        }
        return this.request('/api/orders/create', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },

    sendDBSRequest(invoiceNo) {
        return this.request('/api/dbs/send-invoice', {
            method: 'POST',
            body: JSON.stringify({ invoice_no: invoiceNo })
        });
    },

    // Suppliers
    getSuppliers() {
        return this.request('/api/suppliers');
    },

    addSupplier(supplierData) {
        return this.request('/api/suppliers/add', {
            method: 'POST',
            body: JSON.stringify(supplierData)
        });
    },

    // Bank Mail Inbox
    getMailInbox() {
        return this.request('/api/mail/inbox');
    },

    markMailRead(mailId) {
        return this.request('/api/mail/mark-read', {
            method: 'POST',
            body: JSON.stringify({ mail_id: mailId })
        });
    }
};

window.API = API;
