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

/* =========================
   DASHBOARD
========================= */

async function loadDashboard() {

    try {

        const response = await apiRequest('dashboard');

        const stats = response.stats || {};

        dashboardData = response;

        dashboardData.totalIncome = stats.totalIncome || 0;

        document.getElementById('salesCount').textContent =
            stats.totalSales || 0;

        document.getElementById('incomeValue').textContent =
            formatCurrency(stats.totalIncome);

        document.getElementById('stockValue').textContent =
            stats.totalStock || 0;

        document.getElementById('clientCount').textContent =
            stats.totalClients || 0;

        if (response.categories?.length) {
            createDonutChart(response.categories);
        }

        if (response.monthly?.length) {
            createLineChart(response.monthly);
        }

        if (response.topProducts?.length) {
            updateTopProducts(response.topProducts);
        }

    } catch (error) {

        console.error('Error cargando dashboard:', error);

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

}

/* =========================
   CHARTS
========================= */

function createDonutChart(categories) {

    const labels = categories.map(
        item => item.categoria || 'Sin categoría'
    );

    const values = categories.map(
        item => item.stock || 0
    );

    const colors = [
        '#3b82f6',
        '#8b5cf6',
        '#f59e0b',
        '#10b981',
        '#ef4444'
    ];

    if (donutChart) {

        donutChart.data.labels = labels;
        donutChart.data.datasets[0].data = values;

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
                borderWidth: 0
            }]

        },

        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    display: false
                }
            }
        }

    });

}

function createLineChart(monthly) {

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
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34,197,94,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                },

                {
                    label: 'Gastos',
                    data: gastos,
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239,68,68,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
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
                    position: 'bottom'
                }
            },

            scales: {

                x: {
                    grid: {
                        display: false
                    }
                },

                y: {
                    grid: {
                        color: '#eee'
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

        body.innerHTML = response.inventory.map(item => `

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

        `).join('');

    } catch (error) {

        console.error(
            'Error cargando inventario:',
            error
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

            const initials = client.nombre
                ? client.nombre.charAt(0).toUpperCase()
                : 'C';

            return `

                <div class="client-card">

                    <div class="client-avatar">
                        ${initials}
                    </div>

                    <div>

                        <h3>${client.nombre}</h3>

                        <p>${client.correo || ''}</p>

                        <p>${client.telefono || ''}</p>

                        <p>${client.direccion || ''}</p>

                    </div>

                </div>

            `;

        }).join('');

    } catch (error) {

        console.error(
            'Error cargando clientes:',
            error
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
                    Ver Detalle
                </td>

            </tr>

        `).join('');

    } catch (error) {

        console.error(
            'Error cargando facturas:',
            error
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

        console.error(
            'Error cargando datos de ventas:',
            error
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

    renderBarsAnimation();

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

const themeModeText =
    document.getElementById('themeModeText');

function applyDarkMode(enabled) {

    document.body.classList.toggle('dark', enabled);

    if (themeModeText) {

        themeModeText.textContent =
            enabled
                ? 'Modo oscuro'
                : 'Modo claro';

    }

    localStorage.setItem(
        'darkMode',
        enabled ? 'true' : 'false'
    );

}

if (darkModeToggle) {

    darkModeToggle.addEventListener('change', () => {

        applyDarkMode(
            darkModeToggle.checked
        );

    });

    if (localStorage.getItem('darkMode') === 'true') {

        darkModeToggle.checked = true;

        applyDarkMode(true);

    }

}

/* =========================
   MODAL REPORTE
========================= */

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

    productForm.addEventListener('submit', e => {

        e.preventDefault();

        const nombre =
            document.getElementById('productName').value;

        const categoria =
            document.getElementById('productCategory').value;

        const precio =
            document.getElementById('productPrice').value;

        const stock =
            document.getElementById('productStock').value;

        const descripcion =
            document.getElementById('productDescription').value;

        const imagenInput =
            document.getElementById('productImage');

        const imagen =
            imagenInput.files[0];

        const tableBody =
            document.getElementById('inventoryTableBody');

        if (!tableBody) return;

        let imageHTML = 'Sin imagen';

        if (imagen) {

            const imageURL =
                URL.createObjectURL(imagen);

            imageHTML = `
                <img src="${imageURL}"
                     alt="${nombre}"
                     class="inventory-image">
            `;

        }

        const newRow = document.createElement('tr');

        newRow.innerHTML = `

            <td>

                <div class="inventory-product">

                    ${imageHTML}

                    <div>

                        <strong>${nombre}</strong>

                        <p class="inventory-description">
                            ${descripcion || 'Sin descripción'}
                        </p>

                    </div>

                </div>

            </td>

            <td>${categoria}</td>

            <td>${formatCurrency(precio)}</td>

            <td>${stock}</td>

            <td>

                <button class="table-btn edit-btn">
                    Editar
                </button>

                <button class="table-btn delete-btn">
                    Eliminar
                </button>

            </td>

        `;

        tableBody.prepend(newRow);

        /* LIMPIAR FORMULARIO */

        productForm.reset();

        /* CERRAR MODAL */

        cerrarProductModal();

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

        }

    }

});

/* =========================
   MODAL CLIENTES
========================= */

const clientModal =
    document.getElementById('clientModal');

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

        clientModal.classList.add('active');

    });

}

/* CERRAR */

function cerrarClientModal() {

    clientModal.classList.remove('active');

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

    clientForm.addEventListener('submit', e => {

        e.preventDefault();

        const name = document.getElementById('clientName').value;
        const email = document.getElementById('clientEmail').value;
        const phone = document.getElementById('clientPhone').value;
        const address = document.getElementById('clientAddress').value;

        const container =
            document.getElementById('clientsList');

        const card = document.createElement('div');
        card.classList.add('client-card');

        const initial = name.charAt(0).toUpperCase();

        card.innerHTML = `
            <div class="client-avatar">${initial}</div>

            <div>
                <h3>${name}</h3>
                <p>${email}</p>
                <p>${phone}</p>
                <p>${address}</p>
            </div>
        `;

        container.prepend(card);

        clientForm.reset();

        cerrarClientModal();

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
            alert('Ingresa una tasa válida');
            return;
        }

        localStorage.setItem('usdRate', usdRate);

        alert('Tasa actualizada correctamente');

        location.reload(); // recarga para aplicar cambios

    });

}

async function openEditProduct(id){

    try{

        const response = await apiRequest(`product/${id}`);

        const product = response.product;

        document.getElementById('editId').value = product.id_producto;
        document.getElementById('editNombre').value = product.nombre;
        document.getElementById('editCategoria').value = product.categoria;
        document.getElementById('editPrecio').value = product.precio;
        document.getElementById('editStock').value = product.stock;
        document.getElementById('editImagen').value = product.imagen || '';
        document.getElementById('editDescripcion').value = product.descripcion || '';

        document
            .getElementById('editProductModal')
            .classList.add('active');

    }catch(error){

        console.error(error);

    }
}

document
    .getElementById('saveEditBtn')
    .addEventListener('click', async ()=>{

    const id = document.getElementById('editId').value;

    try{

        await apiRequest(`product/${id}`,{
            method:'PUT',
            body:{
                nombre:document.getElementById('editNombre').value,
                categoria:document.getElementById('editCategoria').value,
                precio:document.getElementById('editPrecio').value,
                stock:document.getElementById('editStock').value,
                imagen:document.getElementById('editImagen').value,
                descripcion:document.getElementById('editDescripcion').value
            }
        });

        document
            .getElementById('editProductModal')
            .classList.remove('active');

        loadInventory();

    }catch(error){

        alert(error.message);

    }

});

document
    .getElementById('cancelEditBtn')
    .addEventListener('click',()=>{

    document
        .getElementById('editProductModal')
        .classList.remove('active');

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

window.openEditProduct = async function(id){

    console.log("Editar producto:", id);

    const modal =
        document.getElementById("editProductModal");

    if(!modal){
        console.error("No existe editProductModal");
        return;
    }

    modal.classList.add("active");

}