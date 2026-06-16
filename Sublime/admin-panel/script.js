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

    if (options.body) {

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

    } catch (error) {

        showToast(
            'Error cargando datos de ventas:',
            'error'
        );

    }

}

/* =========================
   CARRITO
========================= */

function addToCart(product) {

    const existing = cart.find(
        item => item.id === product.id
    );

    if (existing) {

        existing.cantidad += 1;

    } else {

        cart.push({
            ...product,
            cantidad: 1
        });

    }

    renderCart();

}

function renderCart() {

    const cartContent =
        document.getElementById('cartContent');

    if (!cartContent) return;

    if (!cart.length) {

        cartContent.innerHTML =
            '<p>Carrito vacío</p>';

        return;

    }

    cartContent.innerHTML = cart.map(item => `

        <div class="cart-item">

            <strong>${item.nombre}</strong>

            <p>
                Cantidad: ${item.cantidad}
                •
                ${formatCurrency(item.precio)} c/u
            </p>

        </div>

    `).join('');

}

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

        if (!nombre || !categoria || isNaN(precio) || isNaN(stock)) {
            showToast('Completa nombre, categoría, precio y stock.', 'error');
            return;
        }

        try {
            await apiRequest('product', {
                method: 'POST',
                body: {
                    nombre,
                    categoria,
                    precio,
                    stock,
                    descripcion
                }
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

let usdRate = Number(localStorage.getItem('usdRate')) || 36.5;

const usdInput = document.getElementById('usdRate');
const saveUsdBtn = document.getElementById('saveUsdRate');

/* cargar valor en input */
if (usdInput) {
    usdInput.value = usdRate;
}

/* guardar tasa */
if (saveUsdBtn) {

    saveUsdBtn.addEventListener('click', () => {

        usdRate = Number(usdInput.value);

        if (!usdRate || usdRate <= 0) {
            showToast('Ingresa una tasa válida', 'error');
            return;
        }

        localStorage.setItem('usdRate', usdRate);

        showToast('Tasa actualizada correctamente', 'success');

        location.reload(); // recarga para aplicar cambios

    });

}

const ivaRateInput = 
    document.getElementById('ivaRate');

    if(ivaRateInput){
        ivaRateInput.value =
            localStorage.getItem('ivaRate') || '16';
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

        localStorage.setItem(
            'ivaRate',
            iva
        );

        showToast(
            `IVA actualizado a ${iva}%`, 'success'
        );

    });

}

function getCurrentIVA(){
    return parseFloat(
        localStorage.getItem('ivaRate')
    ) || 16;
}

async function openEditProduct(id) {

    try {

        const response = await apiRequest(`product/${id}`);
        const product = response.product;

        document.getElementById('editId').value = product.id_producto;
        document.getElementById('editNombre').value = product.nombre;
        document.getElementById('editCategoria').value = product.categoria || '';
        document.getElementById('editPrecio').value = product.precio;
        document.getElementById('editStock').value = product.stock;
        document.getElementById('editImagen').value = product.imagen || '';
        document.getElementById('editDescripcion').value = product.descripcion || '';

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

        await apiRequest(`product/${id}`, {
            method: 'PUT',
            body: {
                nombre: document.getElementById('editNombre').value,
                categoria: document.getElementById('editCategoria').value,
                precio: Number(document.getElementById('editPrecio').value),
                stock: Number(document.getElementById('editStock').value),
                descripcion: document.getElementById('editDescripcion').value
            }
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

const closeInvoiceBtn = 
    document.getElementById('closeInvoiceBtn');

if(closeInvoiceBtn){
    closeInvoiceBtn.addEventListener('click',()=>{

    document
        .getElementById('invoiceModal')
        .classList.remove('active');

});

}

document
.getElementById('downloadInvoiceBtn')
.addEventListener('click',()=>{

    window.print();

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
