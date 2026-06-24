const apiBase = '../api';

let donutChart = null;
let lineChart = null;

let dashboardData = {
    topProducts: [],
    totalIncome: 0
};

let cart = [];

const donut = document.getElementById('donutChart');
const line = document.getElementById('lineChart');

/* =========================
   API
========================= */

function apiRequest(endpoint, options = {}) {

    const url = `${apiBase}/${endpoint}`;

    if (!options.method) {
        options.method = 'GET';
    }

    if (options.body && !(options.body instanceof FormData)) {
        options.headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };
        options.body = JSON.stringify(options.body);
    }

    return fetch(url, options).then(async response => {

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.message || 'Error en la petición');
        }

        return data;

    });

}

function formatCurrency(value) {
    
    const usd = Number(value || 0);

    const bs = usd * usdRate;

    return `Bs ${bs.toFixed(2)} (${usd.toFixed(2)}$)`;
}

function showToast(
    message,
    type = 'success'
){

    const container =
        document.getElementById(
            'toastContainer'
        );
    if(!container) return;

    const toast = 
    document.createElement('div');

    toast.className =
        `toast ${type}`;

    toast.textContent = 
        message;

    container.appendChild(toast);

    setTimeout(() => {

        toast.style.animation =
            'slideOut .3s ease forwards';

        setTimeout(() => {

            toast.remove();

        }, 300);

    }, 3000);
}

/* =========================
   DASHBOARD
========================= */

async function loadDashboard() {

    try {

        const response = await apiRequest('dashboard');

        const stats = response.stats || {};

        dashboardData = response;

        dashboardData.categories = response.categories || [];
        dashboardData.monthly = response.monthly || [];
        dashboardData.totalIncome = stats.totalIncome || 0;

        const salesCountEl = document.getElementById('salesCount');
        const incomeValueEl = document.getElementById('incomeValue');
        const stockValueEl = document.getElementById('stockValue');
        const clientCountEl = document.getElementById('clientCount');

        if (salesCountEl) {
            salesCountEl.textContent = stats.totalSales || 0;
        }
        if (incomeValueEl) {
            incomeValueEl.textContent = formatCurrency(stats.totalIncome);
        }
        if (stockValueEl) {
            stockValueEl.textContent = stats.totalStock || 0;
        }
        if (clientCountEl) {
            clientCountEl.textContent = stats.totalClients || 0;
        }

        if (dashboardData.categories?.length) {

            createDonutChart(dashboardData.categories);
        }
        if (dashboardData.monthly?.length) {

            createLineChart(dashboardData.monthly);
        }
        if (response.topProducts?.length) {
            updateTopProducts(response.topProducts);
        }

    } catch (error) {

        showToast('Error cargando dashboard:', 'error');

    }

}

function updateTopProducts(products) {

    const container = document.querySelector('.products-box');

    if (!container) return;

    container.innerHTML = `
        <h3>Top 10 Productos por Ventas</h3>

        ${products.slice(0, 5).map(prod => {

            const width = Math.min(
                100,
                Math.max(10, Math.round((prod.cantidad || 0) * 5))
            );

            return `
                <div class="bar">

                    <span>${prod.producto}</span>

                    <div class="progress">
                        <div style="width:${width}%"></div>
                    </div>

                    <b>${formatCurrency(prod.total)}</b>

                </div>
            `;

        }).join('')}
    `;

    renderBarsAnimation();

}

/* =========================
   ANIMACIÓN BARRAS
========================= */

function renderBarsAnimation() {

    document.querySelectorAll('.progress div').forEach(bar => {

        let width = bar.style.width;

        bar.style.width = '0';

        setTimeout(() => {
            bar.style.width = width;
        }, 300);

    });

}


function isDarkMode() {

    return document.body.classList.contains('dark');
}

function createDonutChart(categories) {

    if (!donut) return;

    const labels = categories.map(
        item => item.categoria || 'Sin categoría'
    );

    const values = categories.map(
        item => item.stock || 0
    );

    const colors = [
        '#4f8cff',
        '#8b5cf6',
        '#ec4899',
        '#f59e0b',
        '#00d084',
        '#ef4444',
        '#14b8a6'
    ];

    if (donutChart) {

        donutChart.data.labels = labels;
        donutChart.data.datasets[0].data = values;
        donutChart.data.datasets[0].backgroundColor = colors.slice(0, values.length);

        donutChart.update();

        return;

    }

    donutChart = new Chart(donut, {

        type: 'doughnut',

        data: {

            labels,

            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, values.length),
                borderWidth: 2,
                borderColor: '#0b1730',
                hoverOffset: 10
            }]

        },

        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '68%',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: isDarkMode() ? '#081326' : '#ffffff',
                    titleColor: isDarkMode() ? '#fff' : '#172033',
                    bodyColor: isDarkMode() ? '#fff' : '#172033',
                    borderColor: '#15346e',
                    borderWidth: 1
                }
            }
        }

    });

}

function createLineChart(monthly) {

    if (!line) return;

    const months = monthly.map(item => item.mes || '00');

    const totals = monthly.map(item =>
        Number(item.total || 0)
    );

    const gastos = totals.map(value =>
        Number(value * 0.4)
    );

    if (lineChart) {

        lineChart.data.labels = months;

        lineChart.data.datasets[0].data = totals;

        lineChart.data.datasets[1].data = gastos;

        lineChart.update();

        return;

    }

    lineChart = new Chart(line, {

        type: 'line',

        data: {

            labels: months,

            datasets: [

                {
                    label: 'Ganancias',
                    data: totals,
                    borderColor: '#00d084',
                    backgroundColor: 'rgba(0,208,132,.15)',
                    fill: true,
                    tension: 0.45,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    borderWidth: 3
                },

                {
                    label: 'Gastos',
                    data: gastos,
                    borderColor: '#ff4d4f',
                    backgroundColor: 'rgba(255,77,79,.08)',
                    fill: true,
                    tension: 0.45,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    borderWidth: 2
                }

            ]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            interaction: {
                mode: 'index',
                intersect: false
            },

            plugins: {
                legend: {
                    position: 'bottom',

                    labels: {
                        color: isDarkMode() ? '#ffffff' : '#172033',
                        usePointStyle: true,
                    }
                },

                tooltip: {
                    backgroundColor: isDarkMode() ? '#081326' : '#ffffff',
                    titleColor: isDarkMode() ? '#fff' : '#172033',
                    bodyColor: isDarkMode() ? '#fff' : '#172033',
                    borderColor: '#15346e',
                    borderWidth: 1
                },
            },

            

            scales: {

                x: {
                    
                    ticks: {
                        color: isDarkMode() ? '#9fb3d1' : '#6b7280'
                    },
                    grid: {
                        color: 'rgba(159,179,209,.10)'
                    }
                },

                y: {
                    ticks: {
                        color: isDarkMode() ? '#9fb3d1' : '#6b7280'
                    },
                    grid: {
                        color: 'rgba(159,179,209,.15)'
                    }
                }

            }

        }

    });

}

/* =========================
   INVENTARIO
========================= */

async function loadInventory() {

    try {

        const response = await apiRequest('inventory');

        const body = document.getElementById(
            'inventoryTableBody'
        );

        if (!body) return;

        body.innerHTML = response.inventory.map(item => {
            if (item.stock <= 5) {
                showToast(
                    `Stock bajo: ${item.nombre}`,
                    'error'
                );
            }

            return `
            <tr>

                <td>${item.nombre}</td>

                <td>${item.categoria || 'Sin categoría'}</td>

                <td>${formatCurrency(item.precio)}</td>

                <td>${item.stock}</td>

                <td>
                    <button class="btn-edit"
                        onclick="openEditModal(${item.id_producto})">
                        Editar
                    </button>

                    <button class="btn-delete"
                        onclick="deleteProduct(${item.id_producto})">
                        Eliminar
                    </button>
                </td>
            </tr>

        `;
        }).join('');

    } catch (error) {

        showToast(
            'Error cargando inventario:',
            'error'
        );

    }

}

/* =========================
   CLIENTES
========================= */

async function loadClients() {

    try {

        const response = await apiRequest('clients');

        const container = document.getElementById('clientsList');

        if (!container) return;

        container.innerHTML = response.clients.map(client => {

            const inicial =
                client.nombre.charAt(0).toUpperCase();

            return `
                <div class="client-card-modern">

                    <div class="client-actions">

                        <button
                            class="edit-client-btn"
                            onclick="openEditClient(${client.id_cliente})">

                            ✏️

                        </button>

                        <button
                            class="delete-client-btn"
                            onclick="deleteClient(${client.id_cliente})">

                            🗑️

                        </button>

                    </div>

                    <div class="client-avatar-modern">
                        ${inicial}
                    </div>

                    <h3>${client.nombre}</h3>

                    <p>${client.correo}</p>

                    <p>${client.telefono}</p>

                    <p>${client.direccion}</p>

                    <hr>

                    <small>
                        Registrado:
                        ${new Date().toLocaleDateString('es-VE')}
                    </small>
                </div>

                `;
        }).join('');

    } catch (error) {

        showToast(
            'Error cargando clientes:',
            'error'
        );

    }

}

/* =========================
   FACTURAS
========================= */

async function loadInvoices() {

    try {

        const response = await apiRequest('invoices');

        const body = document.getElementById(
            'invoicesTableBody'
        );

        if (!body) return;

        body.innerHTML = response.invoices.map(invoice => `

            <tr>

                <td>
                    INV-${String(invoice.id).padStart(3, '0')}
                </td>

                <td>
                    ${invoice.cliente || 'Cliente desconocido'}
                </td>

                <td>
                    ${new Date(invoice.fecha)
                        .toLocaleDateString('es-VE')}
                </td>

                <td>
                    ${invoice.items} producto(s)
                </td>

                <td>
                    ${formatCurrency(invoice.total)}
                </td>

                <td>
                    <button 
                        class="btn-view-invoice"
                        onclick="openInvoiceModal(${invoice.id})">
                        Ver Detalle
                    </button>
                </td>

            </tr>

        `).join('');

    } catch (error) {

        showToast(
            'Error cargando facturas:',
            'error'
        );

    }

}

/* =========================
   VENTAS
========================= */

async function loadSalesData() {

    try {

        const response = await apiRequest('sales-data');

        const clientSelect =
            document.getElementById('salesClientSelect');

        const productsContainer =
            document.getElementById('productCardsContainer');

        if (!clientSelect || !productsContainer) return;

        clientSelect.innerHTML = `
            <option value="">
                Seleccionar cliente...
            </option>

            ${response.clients.map(client => `

                <option value="${client.id_cliente}">
                    ${client.nombre}
                </option>

            `).join('')}
        `;

        productsContainer.innerHTML = response.products.map(product => `

            <div class="product-card"
                 data-id="${product.id_producto}"
                 data-name="${product.nombre}"
                 data-price="${product.precio}">

                <strong>${product.nombre}</strong>

                <p>
                    ${formatCurrency(product.precio)}
                    ·
                    Stock: ${product.stock}
                </p>

                <button type="button" class="add-cart">
                    Agregar
                </button>

            </div>

        `).join('');

        productsContainer
            .querySelectorAll('.add-cart')
            .forEach(button => {

                button.addEventListener('click', event => {

                    const card = event.target.closest('.product-card');

                    if (!card) return;

                    addToCart({
                        id: card.dataset.id,
                        nombre: card.dataset.name,
                        precio: Number(card.dataset.price)
                    });

                });

            });

        clientSelect.addEventListener('change', () => {
            loadClientCart();
        });

    } catch (error) {

        showToast(
            'Error cargando datos de ventas:',
            'error'
        );

    }

}

/* =========================
   CARRITO POR CLIENTE
========================= */

let currentClientId = null;

async function loadClientCart() {
    const clientSelect = document.getElementById('salesClientSelect');
    const clientId = clientSelect.value;
    const label = document.getElementById('cartClientLabel');

    if (!clientId) {
        currentClientId = null;
        cart = [];
        renderCart();
        label.textContent = 'Seleccione un cliente';
        return;
    }

    currentClientId = clientId;
    const option = clientSelect.options[clientSelect.selectedIndex];
    label.textContent = `Cliente: ${option.text}`;

    try {
        const response = await apiRequest(`admin/cart/${clientId}`);
        cart = response.cart.map(item => ({
            id: item.id,
            nombre: item.name,
            precio: item.price,
            cantidad: item.quantity
        }));
        renderCart();
    } catch (error) {
        showToast('Error cargando carrito del cliente.', 'error');
    }
}

async function saveCartToServer() {
    if (!currentClientId) return;
    try {
        await apiRequest(`admin/cart/${currentClientId}`, {
            method: 'POST',
            body: {
                items: cart.map(item => ({
                    id: item.id,
                    quantity: item.cantidad,
                    price: item.precio
                }))
            }
        });
    } catch (error) {
        showToast('Error guardando carrito.', 'error');
    }
}

function addToCart(product) {

    if (!currentClientId) {
        showToast('Seleccione un cliente primero.', 'error');
        return;
    }

    const existing = cart.find(item => item.id === product.id);

    if (existing) {
        existing.cantidad += 1;
    } else {
        cart.push({
            ...product,
            cantidad: 1
        });
    }

    renderCart();
    saveCartToServer();
}

function updateQuantity(id, delta) {
    const item = cart.find(i => i.id == id);
    if (!item) return;
    item.cantidad = Math.max(1, item.cantidad + delta);
    renderCart();
    saveCartToServer();
}

function removeFromCart(id) {
    cart = cart.filter(i => i.id != id);
    renderCart();
    saveCartToServer();
}

function renderCart() {

    const cartContent = document.getElementById('cartContent');
    const cartFooter = document.getElementById('cartFooter');

    if (!cartContent) return;

    if (!cart.length) {
        cartContent.innerHTML = '<p>Carrito vacío</p>';
        if (cartFooter) cartFooter.style.display = 'none';
        return;
    }

    const total = cart.reduce((sum, item) => sum + item.precio * item.cantidad, 0);

    cartContent.innerHTML = cart.map(item => `

        <div class="cart-item" style="display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border-color);">

            <div style="flex:1;">
                <strong>${item.nombre}</strong>
                <div style="font-size:0.85rem; color:var(--text-muted);">${formatCurrency(item.precio)} c/u</div>
            </div>

            <div style="display:flex; align-items:center; gap:8px;">
                <button type="button" class="btn-qty" onclick="updateQuantity(${item.id}, -1)" style="width:28px;height:28px;border-radius:50%;border:1px solid var(--border-color);background:transparent;cursor:pointer;font-weight:700;">−</button>
                <span style="min-width:20px;text-align:center;font-weight:700;">${item.cantidad}</span>
                <button type="button" class="btn-qty" onclick="updateQuantity(${item.id}, 1)" style="width:28px;height:28px;border-radius:50%;border:1px solid var(--border-color);background:transparent;cursor:pointer;font-weight:700;">+</button>
                <button type="button" onclick="removeFromCart(${item.id})" style="background:none;border:none;color:#e74c3c;cursor:pointer;font-size:1.1rem;" title="Eliminar">✕</button>
            </div>

        </div>

    `).join('');

    document.getElementById('cartTotal').textContent = formatCurrency(total);

    if (cartFooter) cartFooter.style.display = 'block';

}

/* =========================
   GENERAR FACTURA
========================= */

document.addEventListener('click', async (e) => {
    if (e.target.id === 'generateInvoiceBtn') {
        if (!currentClientId || !cart.length) {
            showToast('Seleccione un cliente y agregue productos.', 'error');
            return;
        }

        if (!confirm('¿Generar factura para este cliente?')) return;

        try {
            const response = await apiRequest('admin/invoice/create', {
                method: 'POST',
                body: {
                    cliente_id: Number(currentClientId),
                    items: cart.map(item => ({
                        id: item.id,
                        quantity: item.cantidad,
                        price: item.precio
                    }))
                }
            });

            cart = [];
            renderCart();
            await Promise.all([
                loadInvoices(),
                loadDashboard()
            ]);
            showToast(`Factura INV-${String(response.invoice_id).padStart(3, '0')} creada.`, 'success');
        } catch (error) {
            showToast(error.message, 'error');
        }
    }
});

/* =========================
   INICIO
========================= */

window.addEventListener('DOMContentLoaded', async () => {

    await Promise.all([
        loadDashboard(),
        loadInventory(),
        loadClients(),
        loadInvoices(),
        loadSalesData()
    ]);

});

/* =========================
   NAVEGACIÓN
========================= */

const menuItems =
    document.querySelectorAll('.sidebar li[data-section]');

const sections =
    document.querySelectorAll('.page-section');

const pageTitle =
    document.getElementById('pageTitle');

const sectionTitles = {

    dashboard: 'Bienvenido, Admin!',
    inventory: 'Inventario',
    sales: 'Ventas',
    clients: 'Clientes',
    invoices: 'Facturas',
    settings: 'Configuración'

};

menuItems.forEach(item => {

    item.addEventListener('click', () => {

        const target = item.dataset.section;

        menuItems.forEach(menu =>
            menu.classList.remove('active')
        );

        item.classList.add('active');

        sections.forEach(section => {

            section.classList.toggle(
                'active',
                section.id === target
            );

        });

        pageTitle.textContent =
            sectionTitles[target] || 'Panel';

        toggleReportButton(target);

    });

});

/* =========================
   BOTÓN DASHBOARD
========================= */

const reportButton =
    document.querySelector('.dashboard-report-btn');

function toggleReportButton(section) {

    if (!reportButton) return;

    if (section === 'dashboard') {

        reportButton.style.display = 'inline-flex';

    } else {

        reportButton.style.display = 'none';

    }

}

toggleReportButton('dashboard');

/* =========================
   DARK MODE
========================= */

const darkModeToggle =
    document.getElementById('darkModeToggle');

const themeModeText = null;

function applyDarkMode(enabled) {

    document.body.classList.toggle('dark', enabled);

    localStorage.setItem(
        'darkMode',
        enabled ? 'true' : 'false'
    );

    if (dashboardData.categories?.length) {

        donutChart?.destroy();
        donutChart = null;
        createDonutChart(
            dashboardData.categories
        );
}

    if (dashboardData.monthly?.length) {
        lineChart?.destroy();
        lineChart = null;

        createLineChart(
            dashboardData.monthly
        );
    }
}

if (darkModeToggle) {

    darkModeToggle.addEventListener('change', () => {

        applyDarkMode(
            darkModeToggle.checked
        );

    });

    const savedDarkMode = 
        localStorage.getItem('darkMode');

    const enableDark = 
        savedDarkMode !== 'false';

    darkModeToggle.checked =
     enableDark;

    applyDarkMode(enableDark);

}


const modal =
    document.getElementById('modal');

const openModalBtn =
    document.getElementById('openModal');

const closeModalBtn =
    document.getElementById('closeModal');

const cancelBtn =
    document.getElementById('cancelar');

const tipoReporte =
    document.getElementById('tipoReporte');

const descripcion =
    document.getElementById('descripcion');

const reportTitle =
    document.getElementById('reportTitle');

/* ABRIR */

if (openModalBtn) {

    openModalBtn.addEventListener('click', () => {

        modal.classList.add('active');

    });

}

/* CERRAR */

function cerrarModal() {

    modal.classList.remove('active');

}

if (closeModalBtn) {

    closeModalBtn.addEventListener(
        'click',
        cerrarModal
    );

}

if (cancelBtn) {

    cancelBtn.addEventListener(
        'click',
        cerrarModal
    );

}

/* CLICK AFUERA */

window.addEventListener('click', e => {

    if (e.target === modal) {

        cerrarModal();

    }

});

/* DESCRIPCIÓN */

function actualizarDescripcionReporte() {

    const tipo = tipoReporte.value;

    if (tipo === 'mensual') {

        reportTitle.textContent =
            'Reporte Mensual';

        descripcion.textContent =
            'Incluirá: métricas generales, top productos, ventas detalladas y análisis de inventario';

    }

    if (tipo === 'diario') {

        reportTitle.textContent =
            'Reporte Diario';

        descripcion.textContent =
            'Incluirá: ventas del día, ingresos diarios, productos vendidos y movimientos recientes';
    }

    if (tipo === 'anual') {

        reportTitle.textContent =
            'Reporte Anual';

        descripcion.textContent =
            'Incluirá: resumen anual, ganancias totales, productos más vendidos y análisis financiero';
    }

    if (tipo === 'semanal') {

        reportTitle.textContent =
            'Reporte Semanal';

        descripcion.textContent=
            'Incluirá: ventas de la semana, ingresos semanales, productos destacados y análisis de tendencias';
    }

    if (tipo === 'personalizado') {

        reportTitle.textContent =
            'Reporte Personalizado';
        
        descripcion.textContent =
            'Permite seleccionar métricas específicas, rango de fechas y filtros personalizados para generar un reporte a medida';
    }

}

if (tipoReporte) {

    tipoReporte.addEventListener(
        'change',
        actualizarDescripcionReporte
    );

}

actualizarDescripcionReporte();

/* =========================
   PDF
========================= */

function generarPDF(tipo) {

    const { jsPDF } = window.jspdf;

    const doc = new jsPDF();

    doc.setFontSize(22);

    doc.text(
        'Reporte de Ventas',
        20,
        20
    );

    doc.setFontSize(13);

    doc.text(
        `Tipo de reporte: ${tipo}`,
        20,
        35
    );

    doc.text(
        `Fecha: ${new Date()
            .toLocaleDateString('es-VE')}`,
        20,
        45
    );

    let y = 65;

    doc.setFontSize(16);

    doc.text(
        'Top Productos',
        20,
        y
    );

    y += 15;

    dashboardData.topProducts.forEach(producto => {

        doc.setFontSize(12);

        doc.text(
            `${producto.producto} | Cantidad: ${producto.cantidad} | Total: ${formatCurrency(producto.total)}`,
            20,
            y
        );

        y += 10;

    });

    y += 10;

    doc.setFontSize(14);

    doc.text(
        `Ganancias Totales: ${formatCurrency(dashboardData.totalIncome)}`,
        20,
        y
    );

    doc.save(`reporte-${tipo}.pdf`);

}

/* =========================
   EXCEL
========================= */

function generarExcel(tipo) {

    const datos = [
        ['Producto', 'Cantidad', 'Total']
    ];

    dashboardData.topProducts.forEach(producto => {

        datos.push([
            producto.producto,
            producto.cantidad,
            producto.total
        ]);

    });

    datos.push([]);
    datos.push([
        'Ganancias Totales',
        '',
        dashboardData.totalIncome
    ]);

    const hoja =
        XLSX.utils.aoa_to_sheet(datos);

    const libro =
        XLSX.utils.book_new();

    XLSX.utils.book_append_sheet(
        libro,
        hoja,
        'Reporte'
    );

    XLSX.writeFile(
        libro,
        `reporte-${tipo}.xlsx`
    );

}

/* =========================
   DESCARGAR
========================= */

const descargarBtn =
    document.getElementById('descargar');

if (descargarBtn) {

    descargarBtn.addEventListener('click', () => {

        const tipo =
            document.getElementById('tipoReporte').value;

        const formato =
            document.getElementById('formato').value;

        if (formato === 'pdf') {

            generarPDF(tipo);

        } else {

            generarExcel(tipo);

        }

        cerrarModal();

    });

}
document.querySelectorAll('.settings-tab-button').forEach(btn => {
    btn.addEventListener('click', () => {

        const target = btn.dataset.config;

        document.querySelectorAll('.settings-tab-button')
            .forEach(b => b.classList.remove('active'));

        document.querySelectorAll('.settings-panel')
            .forEach(p => p.classList.remove('active'));

        btn.classList.add('active');

        document.getElementById(target).classList.add('active');
    });
});

/* =========================
   MODAL AGREGAR PRODUCTO
========================= */

const productModal =
    document.getElementById('productModal');

const openProductModal =
    document.getElementById('openProductModal');

const closeProductModal =
    document.getElementById('closeProductModal');

const cancelProduct =
    document.getElementById('cancelProduct');

const productForm =
    document.getElementById('productForm');

/* ABRIR MODAL */

if (openProductModal) {

    openProductModal.addEventListener('click', () => {

        productModal.classList.add('active');

    });

}

/* CERRAR MODAL */

function cerrarProductModal() {

    productModal.classList.remove('active');

}

if (closeProductModal) {

    closeProductModal.addEventListener(
        'click',
        cerrarProductModal
    );

}

if (cancelProduct) {

    cancelProduct.addEventListener(
        'click',
        cerrarProductModal
    );

}

/* CLICK AFUERA */

window.addEventListener('click', e => {

    if (e.target === productModal) {

        cerrarProductModal();

        
    }
});

/* =========================
   GUARDAR PRODUCTO
========================= */

if (productForm) {

    productForm.addEventListener('submit', async e => {

        e.preventDefault();

        const nombre = document.getElementById('productName').value;
        const categoria = document.getElementById('productCategory').value;
        const precio = Number(document.getElementById('productPrice').value);
        const stock = Number(document.getElementById('productStock').value);
        const descripcion = document.getElementById('productDescription').value;
        const imagenInput = document.getElementById('productImagen');

        if (!nombre || !categoria || isNaN(precio) || isNaN(stock)) {
            showToast('Completa nombre, categoría, precio y stock.', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('nombre', nombre);
        formData.append('categoria', categoria);
        formData.append('precio', precio);
        formData.append('stock', stock);
        formData.append('descripcion', descripcion);
        if (imagenInput.files.length > 0) {
            formData.append('imagen', imagenInput.files[0]);
        }

        try {
            await apiRequest('product', {
                method: 'POST',
                body: formData
            });

            productForm.reset();
            cerrarProductModal();
            await Promise.all([
                loadInventory(),
                loadSalesData(),
                loadDashboard()
            ]);
            showToast('Producto creado y sincronizado con la base de datos.', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        }

    });

}

/* =========================
   ELIMINAR PRODUCTO
========================= */

document.addEventListener('click', e => {

    if (
        e.target.classList.contains('delete-btn')
    ) {

        const row = e.target.closest('tr');

        if (row) {

            row.remove();

            showToast('Producto eliminado del inventario', 'error');
        }

    }

});

/* =========================
   MODAL CLIENTES
========================= */

const clientModal =
    document.getElementById('editClientModal');

const openClientModal =
    document.getElementById('openClientModal');

const closeClientModal =
    document.getElementById('closeClientModal');

const cancelClient =
    document.getElementById('cancelClient');

const clientForm =
    document.getElementById('clientForm');

/* ABRIR */

if (openClientModal) {

    openClientModal.addEventListener('click', () => {

        const clientModal = document.getElementById('clientModal');
        if (clientModal) {
            clientModal.classList.add('active');
        }

    });

}

/* CERRAR */

function cerrarClientModal() {

    const clientModal = document.getElementById('clientModal');
    if (clientModal) {
        clientModal.classList.remove('active');
    }

}

if (closeClientModal) {

    closeClientModal.addEventListener('click', cerrarClientModal);

}

if (cancelClient) {

    cancelClient.addEventListener('click', cerrarClientModal);

}

/* CLICK FUERA */

window.addEventListener('click', e => {

    if (e.target === clientModal) {

        cerrarClientModal();

    }

});

/* GUARDAR CLIENTE */

if (clientForm) {

    clientForm.addEventListener('submit', async e => {

        e.preventDefault();

        const name = document.getElementById('clientName').value;
        const email = document.getElementById('clientEmail').value;
        const phone = document.getElementById('clientPhone').value;
        const address = document.getElementById('clientAddress').value;

        if (!name || !email) {
            showToast('Nombre y correo son requeridos.', 'error');
            return;
        }

        try {
            await apiRequest('client', {
                method: 'POST',
                body: {
                    nombre: name,
                    correo: email,
                    telefono: phone,
                    direccion: address
                }
            });

            clientForm.reset();
            cerrarClientModal();
            await Promise.all([
                loadClients(),
                loadSalesData(),
                loadDashboard()
            ]);
            showToast('Cliente creado y sincronizado con la base de datos.', 'success');
        } catch (error) {
            showToast(error.message, 'error');
        }

    });

}

/* =========================
   TASA DÓLAR (BS)
========================= */

let usdRate = 40.0;
let eurRate = 45.0;

const usdInput = document.getElementById('usdRate');
const eurInput = document.getElementById('eurRate');
const saveBtn = document.getElementById('saveUsdRate');
const fetchBcvBtn = document.getElementById('fetchBcvRate');
const bcvInfo = document.getElementById('bcvInfo');
const bcvUsdDisplay = document.getElementById('bcvUsdDisplay');
const bcvEurDisplay = document.getElementById('bcvEurDisplay');
const bcvDate = document.getElementById('bcvDate');

function loadRatesFromBackend() {
    fetch('/api/tasa-cambio')
        .then(r => r.json())
        .then(data => {
            if (data.usd && data.usd > 0) {
                usdRate = data.usd;
                eurRate = data.eur || 0;
                if (usdInput) usdInput.value = usdRate;
                if (eurInput) eurInput.value = eurRate;
            }
        })
        .catch(() => {});
}

if (usdInput || eurInput) {
    loadRatesFromBackend();
}

if (fetchBcvBtn) {
    fetchBcvBtn.addEventListener('click', () => {
        fetchBcvBtn.disabled = true;
        fetchBcvBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Obteniendo...';
        fetch('/api/tasa-cambio/bcv')
            .then(r => r.json())
            .then(data => {
                if (data.usd && data.usd > 0) {
                    usdRate = data.usd;
                    eurRate = data.eur || 0;
                    if (usdInput) usdInput.value = usdRate.toFixed(4);
                    if (eurInput) eurInput.value = eurRate.toFixed(4);
                    if (bcvInfo) {
                        bcvInfo.style.display = 'block';
                        bcvUsdDisplay.textContent = 'USD ' + usdRate.toFixed(4) + ' Bs';
                        bcvEurDisplay.textContent = 'EUR ' + eurRate.toFixed(4) + ' Bs';
                        bcvDate.textContent = data.fecha || '';
                    }
                    showToast('Tasas BCV obtenidas', 'success');
                }
            })
            .catch(() => showToast('Error al obtener tasas del BCV', 'error'))
            .finally(() => {
                fetchBcvBtn.disabled = false;
                fetchBcvBtn.innerHTML = '<i class="fas fa-cloud-download-alt"></i> Obtener tasa del BCV';
            });
    });
}

/* guardar tasa */
if (saveBtn) {
    saveBtn.addEventListener('click', () => {
        const usd = Number(usdInput ? usdInput.value : 0);
        const eur = Number(eurInput ? eurInput.value : 0);
        if (!usd || usd <= 0) {
            showToast('Ingresa una tasa USD válida', 'error');
            return;
        }
        fetch('/api/tasa-cambio', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({usd, eur})
        })
        .then(r => r.json())
        .then(data => {
            if (data.mensaje) {
                showToast('Tasas guardadas correctamente', 'success');
                usdRate = data.usd;
                eurRate = data.eur;
            }
        })
        .catch(() => showToast('Error al guardar tasas', 'error'));
    });
}

// ── IVA desde el backend ──
let currentIVARate = 16;

function loadIVARate() {
    fetch('/api/config/iva')
        .then(r => r.json())
        .then(data => {
            currentIVARate = data.iva;
            const inp = document.getElementById('ivaRate');
            if (inp) inp.value = currentIVARate;
        })
        .catch(() => {});
}

function getCurrentIVA() {
    return currentIVARate;
}

const saveIvaRateBtn =
    document.getElementById('saveIvaRate');

if(saveIvaRateBtn){

    saveIvaRateBtn.addEventListener('click', () => {

        const iva =
            parseFloat(
                document.getElementById('ivaRate').value
            );

        if(isNaN(iva) || iva < 0){

            showToast('Ingrese un IVA válido', 'error');
            return;

        }

        fetch('/api/config/iva', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({iva: iva})
        })
        .then(r => r.json())
        .then(data => {
            currentIVARate = data.iva;
            showToast(`IVA actualizado a ${data.iva}%`, 'success');
        })
        .catch(() => showToast('Error al guardar IVA', 'error'));

    });

}

// Load IVA on startup
loadIVARate();

async function openEditProduct(id) {

    try {

        const response = await apiRequest(`product/${id}`);
        const product = response.product;

        document.getElementById('editId').value = product.id_producto;
        document.getElementById('editNombre').value = product.nombre;
        document.getElementById('editCategoria').value = product.categoria || '';
        document.getElementById('editPrecio').value = product.precio;
        document.getElementById('editStock').value = product.stock;
        document.getElementById('editDescripcion').value = product.descripcion || '';

        const imgLabel = document.getElementById('editImagenActual');
        if (product.imagen) {
            imgLabel.textContent = 'Imagen actual: ' + product.imagen;
        } else {
            imgLabel.textContent = 'Sin imagen actual';
        }
        document.getElementById('editImagen').value = '';

        document.getElementById('editProductModal').classList.add('active');

    } catch (error) {

        showToast(error.message, 'error');

    }
}

window.openEditModal = openEditProduct;

window.deleteProduct = async function(id) {
    const confirmar = confirm('¿Desea eliminar este producto?');
    if (!confirmar) return;

    try {
        await apiRequest(`product/${id}`, {
            method: 'DELETE'
        });
        await loadInventory();
        showToast('Producto eliminado correctamente.', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }
};

document
    .getElementById('saveEditBtn')
    .addEventListener('click', async () => {

    const id = document.getElementById('editId').value;

    try {

        const formData = new FormData();
        formData.append('nombre', document.getElementById('editNombre').value);
        formData.append('categoria', document.getElementById('editCategoria').value);
        formData.append('precio', Number(document.getElementById('editPrecio').value));
        formData.append('stock', Number(document.getElementById('editStock').value));
        formData.append('descripcion', document.getElementById('editDescripcion').value);
        const editImagenInput = document.getElementById('editImagen');
        if (editImagenInput.files.length > 0) {
            formData.append('imagen', editImagenInput.files[0]);
        }

        await apiRequest(`product/${id}`, {
            method: 'PUT',
            body: formData
        });

        document
            .getElementById('editProductModal')
            .classList.remove('active');

        await loadInventory();
        showToast('Producto actualizado correctamente', 'success');

    } catch (error) {

        showToast(error.message, 'error');

    }

});

document
    .getElementById('cancelEditBtn')
    .addEventListener('click',()=>{

    document
        .getElementById('editProductModal')
        .classList.remove('active');

});


const editModal =
    document.getElementById('editProductModal');

editModal.addEventListener('click',(e)=>{

    if(e.target === editModal){

        editModal.classList.remove('active');

    }

});


const invoiceModal =
    document.getElementById('invoiceModal');

invoiceModal.addEventListener('click',(e)=>{

    if(e.target === invoiceModal){

        invoiceModal.classList.remove('active');

    }

});

window.openInvoiceModal = async function(id){

    try{

        const invoice =
            await apiRequest(`invoice/${id}`);

        document.getElementById('invoiceNumber')
            .textContent =
            `INV-${String(invoice.id).padStart(3,'0')}`;

        document.getElementById('invoiceClient')
            .textContent =
            invoice.cliente;

        document.getElementById('invoiceDate')
            .textContent =
            new Date(invoice.fecha)
            .toLocaleDateString('es-VE');

        document.getElementById('invoiceSubtotal')
            .textContent =
            formatCurrency(invoice.subtotal || invoice.total);

        document.getElementById('invoiceIVA')
            .textContent =
            formatCurrency(invoice.iva_amount || 0);

        document.getElementById('invoiceTotal')
            .textContent =
            formatCurrency(invoice.total);

        const tbody =
            document.getElementById('invoiceItems');

        tbody.innerHTML =
            invoice.detalles.map(item => `
                <tr>
                    <td>${item.producto}</td>
                    <td>${item.cantidad}</td>
                    <td>${formatCurrency(item.precio)}</td>
                    <td>${formatCurrency(item.total)}</td>
                </tr>
            `).join('');

        document
            .getElementById('invoiceModal')
            .classList.add('active');

    }catch(error){

        console.error(error);

    }

}

/* =========================
   REPORTES
========================= */

document.addEventListener('change', (e) => {
    if (e.target.id === 'reportType') {
        const dr = document.getElementById('reportDateRange');
        dr.style.display = e.target.value === 'custom' ? 'block' : 'none';
    }
});

document.addEventListener('click', (e) => {
    if (e.target.id === 'generateReportBtn') {
        const today = new Date();
        document.getElementById('reportDateFrom').value = today.toISOString().split('T')[0];
        document.getElementById('reportDateTo').value = today.toISOString().split('T')[0];
        document.getElementById('reportType').value = 'daily';
        document.getElementById('reportDateRange').style.display = 'none';
        document.getElementById('reportModal').classList.add('active');
    }
    if (e.target.id === 'cancelReportBtn') {
        document.getElementById('reportModal').classList.remove('active');
    }
    if (e.target.id === 'generateReportAction') {
        generateReport();
    }
});

async function generateReport() {
    const type = document.getElementById('reportType').value;
    const format = document.getElementById('reportFormat').value;
    let dateFrom, dateTo;
    const today = new Date();

    switch (type) {
        case 'daily':
            dateFrom = today.toISOString().split('T')[0];
            dateTo = dateFrom;
            break;
        case 'weekly': {
            const weekStart = new Date(today);
            weekStart.setDate(today.getDate() - today.getDay());
            dateFrom = weekStart.toISOString().split('T')[0];
            dateTo = today.toISOString().split('T')[0];
            break;
        }
        case 'monthly':
            dateFrom = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
            dateTo = today.toISOString().split('T')[0];
            break;
        case 'annual':
            dateFrom = new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0];
            dateTo = today.toISOString().split('T')[0];
            break;
        case 'custom':
            dateFrom = document.getElementById('reportDateFrom').value;
            dateTo = document.getElementById('reportDateTo').value;
            if (!dateFrom || !dateTo) {
                showToast('Seleccione las fechas del reporte.', 'error');
                return;
            }
            break;
    }

    document.getElementById('reportModal').classList.remove('active');

    try {
        const response = await apiRequest('report', {
            method: 'POST',
            body: { date_from: dateFrom, date_to: dateTo }
        });

        if (!response.invoices.length) {
            showToast('No hay facturas en el período seleccionado.', 'error');
            return;
        }

        const typeLabels = { daily: 'Diario', weekly: 'Semanal', monthly: 'Mensual', annual: 'Anual', custom: 'Personalizado' };

        if (format === 'excel') {
            let csv = 'N° Factura,Cliente,Fecha,Items,Total\n';
            response.invoices.forEach(inv => {
                const fecha = new Date(inv.fecha).toLocaleDateString('es-VE');
                const total = (inv.total || 0).toFixed(2);
                csv += `INV-${String(inv.id).padStart(3,'0')},${inv.cliente || 'Desconocido'},${fecha},${inv.items} producto(s),${total}\n`;
            });
            csv += `,,,,Total General,${response.gran_total.toFixed(2)}\n`;

            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `reporte_${type}_${dateFrom}_a_${dateTo}.csv`;
            link.click();
            showToast('Reporte Excel descargado.', 'success');
        } else {
            let html = `
            <html>
            <head><title>Reporte ${typeLabels[type]} - Sublime</title>
            <style>
                body { font-family: 'Inter', sans-serif; padding: 40px; color: #1a1a2e; }
                h1 { font-size: 2rem; margin-bottom: 5px; }
                .sub { color: #888; margin-bottom: 5px; }
                .periodo { color: #888; margin-bottom: 30px; font-size: 0.9rem; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th { background: #1a1a2e; color: #fff; padding: 12px; text-align: left; }
                td { padding: 12px; border-bottom: 1px solid #eee; }
                tr:hover { background: #f5f5f5; }
                .resumen { margin-top: 25px; display: flex; gap: 30px; justify-content: flex-end; font-size: 1rem; }
                .resumen div { text-align: right; }
                .resumen .label { color: #888; font-size: 0.85rem; }
                .resumen .value { font-size: 1.3rem; font-weight: 900; }
                .footer { margin-top: 30px; color: #888; font-size: 0.85rem; text-align: center; border-top: 1px solid #ddd; padding-top: 20px; }
            </style>
            </head>
            <body>
                <h1>Reporte ${typeLabels[type]}</h1>
                <p class="sub">Sublime - Sistema de Ventas</p>
                <p class="periodo">Período: ${new Date(dateFrom).toLocaleDateString('es-VE')} - ${new Date(dateTo).toLocaleDateString('es-VE')}</p>
                <table>
                    <thead>
                        <tr><th>N° Factura</th><th>Cliente</th><th>Fecha</th><th>Items</th><th>Total</th></tr>
                    </thead>
                    <tbody>
            `;

            response.invoices.forEach(inv => {
                html += `
                    <tr>
                        <td>INV-${String(inv.id).padStart(3, '0')}</td>
                        <td>${inv.cliente || 'Desconocido'}</td>
                        <td>${new Date(inv.fecha).toLocaleDateString('es-VE')}</td>
                        <td>${inv.items} producto(s)</td>
                        <td>${formatCurrency(inv.total)}</td>
                    </tr>
                `;
            });

            html += `
                    </tbody>
                </table>
                <div class="resumen">
                    <div><span class="label">Facturas</span><br><span class="value">${response.count}</span></div>
                    <div><span class="label">Total General</span><br><span class="value">${formatCurrency(response.gran_total)}</span></div>
                </div>
                <div class="footer">Reporte generado el ${new Date().toLocaleString('es-VE')}</div>
            </body>
            </html>
            `;

            const win = window.open('', '_blank');
            win.document.write(html);
            win.document.close();
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

const closeInvoiceBtn = 
    document.getElementById('closeInvoiceBtn');

if(closeInvoiceBtn){
    closeInvoiceBtn.addEventListener('click',()=>{

    document
        .getElementById('invoiceModal')
        .classList.remove('active');

});

}

function buildInvoiceHTML() {
    const invoice = {
        number: document.getElementById('invoiceNumber').textContent,
        client: document.getElementById('invoiceClient').textContent,
        date: document.getElementById('invoiceDate').textContent,
        total: document.getElementById('invoiceTotal').textContent,
        items: []
    };
    document.querySelectorAll('#invoiceItems tr').forEach(tr => {
        const tds = tr.querySelectorAll('td');
        if (tds.length === 4) {
            invoice.items.push({
                producto: tds[0].textContent,
                cantidad: tds[1].textContent,
                precio: tds[2].textContent,
                total: tds[3].textContent
            });
        }
    });
    const rows = invoice.items.map((item, i) => {
        const bg = i % 2 === 0 ? ' style="background:#f5f5f5"' : '';
        return `<tr${bg}><td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:9pt">${item.producto}</td><td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:9pt">${item.cantidad}</td><td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:9pt">${item.precio}</td><td style="padding:5px 8px;border-bottom:1px solid #eee;font-size:9pt">${item.total}</td></tr>`;
    }).join('');

    return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>${invoice.number} - Sublime</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Helvetica','Arial',sans-serif;padding:40px;color:#1a1a2e}
.header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:0.5pt solid #1a1a2e;padding-bottom:15px;margin-bottom:18px}
.brand{font-size:24pt;font-weight:700;letter-spacing:3px}
.brand small{font-size:10pt;font-weight:400;color:#888;letter-spacing:0}
.title{text-align:right}
.title h1{font-size:18pt;font-weight:700;margin:0}
.title p{font-size:12pt;color:#888}
.info{display:flex;justify-content:space-between;margin-bottom:18px}
.info div h3{font-size:9pt;font-weight:700;color:#888;margin-bottom:2px}
.info div p{font-size:11pt;font-weight:400;margin:0}
table{width:100%;border-collapse:collapse;margin-bottom:10px}
th{padding:5px 8px;background:#1a1a2e;color:#fff;font-size:9pt;font-weight:700;text-align:left}
.total{text-align:right;font-size:13pt;font-weight:700;padding-top:8px;border-top:0.5pt solid #1a1a2e}
.footer{position:fixed;bottom:10px;left:0;width:100%;text-align:center;color:#888;font-size:8pt;border-top:0.3pt solid #ddd;padding-top:10px}
@media print{body{padding:20px}}
@page{margin:10mm}
</style>
</head>
<body>
<div class="header">
<div class="brand">SUBLIME <small>Sistema de Ventas</small></div>
<div class="title"><h1>FACTURA</h1><p>${invoice.number}</p></div>
</div>
<div class="info">
<div><h3>Facturado a:</h3><p>${invoice.client}</p></div>
<div><h3>Fecha:</h3><p>${invoice.date}</p></div>
</div>
<table>
<thead><tr><th style="width:40%">Producto</th><th style="width:15%">Cantidad</th><th style="width:20%">Precio Unit.</th><th style="width:25%">Total</th></tr></thead>
<tbody>${rows}</tbody>
</table>
<div class="total">Total: ${invoice.total}</div>
<div class="footer">Factura generada el ${new Date().toLocaleString('es-VE')}</div>
</body>
</html>`;
}

document
.getElementById('downloadInvoiceBtn')
.addEventListener('click',()=>{

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: 'mm', format: 'a4' });
    const pageW = 210;
    const margin = 20;
    const usableW = pageW - margin * 2;
    let y = margin;

    const invoice = {
        number: document.getElementById('invoiceNumber').textContent,
        client: document.getElementById('invoiceClient').textContent,
        date: document.getElementById('invoiceDate').textContent,
        total: document.getElementById('invoiceTotal').textContent,
        items: []
    };
    document.querySelectorAll('#invoiceItems tr').forEach(tr => {
        const tds = tr.querySelectorAll('td');
        if (tds.length === 4) {
            invoice.items.push({
                producto: tds[0].textContent,
                cantidad: tds[1].textContent,
                precio: tds[2].textContent,
                total: tds[3].textContent
            });
        }
    });

    // Header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(24);
    doc.text('SUBLIME', margin, y);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(10);
    doc.text('Sistema de Ventas', margin, y + 5);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(18);
    const titleW = doc.getTextWidth('FACTURA');
    doc.text('FACTURA', pageW - margin - titleW, y);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(12);
    const numW = doc.getTextWidth(invoice.number);
    doc.text(invoice.number, pageW - margin - numW, y + 6);

    y += 15;
    doc.setDrawColor(26, 26, 46);
    doc.setLineWidth(0.5);
    doc.line(margin, y, pageW - margin, y);
    y += 10;

    // Info
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text('Facturado a:', margin, y);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(11);
    doc.text(invoice.client, margin, y + 5);

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    const dateLabelW = doc.getTextWidth('Fecha:');
    doc.text('Fecha:', pageW - margin - 50, y);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(11);
    doc.text(invoice.date, pageW - margin - 50, y + 5);

    y += 18;

    // Table header
    const cols = [
        { label: 'Producto', x: margin, w: usableW * 0.4 },
        { label: 'Cantidad', x: margin + usableW * 0.4, w: usableW * 0.15 },
        { label: 'Precio Unit.', x: margin + usableW * 0.55, w: usableW * 0.2 },
        { label: 'Total', x: margin + usableW * 0.75, w: usableW * 0.25 }
    ];

    doc.setFillColor(26, 26, 46);
    doc.rect(margin, y, usableW, 8, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    cols.forEach(c => doc.text(c.label, c.x + 2, y + 5.5));
    y += 8;

    // Table rows
    doc.setTextColor(26, 26, 46);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    invoice.items.forEach((item, i) => {
        if (i % 2 === 0) {
            doc.setFillColor(245, 245, 245);
            doc.rect(margin, y, usableW, 7, 'F');
        }
        doc.text(item.producto, cols[0].x + 2, y + 5);
        doc.text(item.cantidad, cols[1].x + 2, y + 5);
        doc.text(item.precio, cols[2].x + 2, y + 5);
        doc.text(item.total, cols[3].x + 2, y + 5);
        y += 7;
    });

    // Total line
    y += 3;
    doc.setDrawColor(26, 26, 46);
    doc.setLineWidth(0.5);
    doc.line(margin, y, pageW - margin, y);
    y += 5;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    const totalLabel = 'Total: ' + invoice.total;
    const totalW = doc.getTextWidth(totalLabel);
    doc.text(totalLabel, pageW - margin - totalW, y);

    // Footer
    y = 277;
    doc.setDrawColor(221, 221, 221);
    doc.setLineWidth(0.3);
    doc.line(margin, y, pageW - margin, y);
    doc.setTextColor(136, 136, 136);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(8);
    const footerText = 'Factura generada el ' + new Date().toLocaleString('es-VE');
    const footerW = doc.getTextWidth(footerText);
    doc.text(footerText, (pageW - footerW) / 2, y + 5);

    doc.save(invoice.number + '.pdf');

});

document
.getElementById('printInvoiceBtn')
.addEventListener('click',()=>{

    const html = buildInvoiceHTML();
    const win = window.open('about:blank', '_blank');
    win.document.write(html);
    win.document.close();
    setTimeout(() => { win.focus(); win.print(); }, 300);

});

window.openEditClient = async function(id) {

    try {

        const response = await apiRequest(`client/${id}`);
        const client = response.client;

        document.getElementById('editClientId').value = client.id_cliente;
        document.getElementById('editClientName').value = client.nombre;
        document.getElementById('editClientEmail').value = client.correo;
        document.getElementById('editClientPhone').value = client.telefono || '';
        document.getElementById('editClientAddress').value = client.direccion || '';

        document.getElementById('editClientModal').classList.add('active');

    } catch (error) {

        showToast(error.message, 'error');

    }

};

document
.getElementById('saveClientBtn')
.addEventListener('click',async()=>{

    const id =
        document.getElementById(
            'editClientId'
        ).value;

    await apiRequest(`client/${id}`,{

        method:'PUT',

        body:{

            nombre:
                document.getElementById(
                    'editClientName'
                ).value,

            correo:
                document.getElementById(
                    'editClientEmail'
                ).value,

            telefono:
                document.getElementById(
                    'editClientPhone'
                ).value,

            direccion:
                document.getElementById(
                    'editClientAddress'
                ).value
        }

    });

    document
        .getElementById('editClientModal')
        .classList.remove('active');

    loadClients();

});

window.deleteClient = async function(id) {

    const confirmar = confirm('¿Desea eliminar este cliente?');
    if (!confirmar) return;

    try {
        await apiRequest(`client/${id}`, {
            method: 'DELETE'
        });
        await loadClients();
        showToast('Cliente eliminado correctamente.', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    }

};

document
.getElementById('cancelClientBtn')
.addEventListener('click',()=>{

    document
        .getElementById('editClientModal')
        .classList.remove('active');

});

function deleteClientCard(btn){
    btn.closest('.client-card-mordern').remove();

    showToast(
        'Cliente eliminado',
        'error'
    );
}
