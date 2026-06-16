document.addEventListener('DOMContentLoaded', () => {
    // Lógica del menú de hamburguesas
    const burgerMenu = document.getElementById('burger-menu');
    const navLinks = document.querySelector('.nav-links');

    if (burgerMenu) {
        burgerMenu.addEventListener('click', () => {
            if (navLinks) navLinks.classList.toggle('active');
        });
    }

    // Lógica de alternancia de temas
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    
    // Comprueba el almacenamiento local para el tema
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'light') {
        body.classList.add('light-mode');
        if (themeToggle) themeToggle.innerHTML = '<i class="fa-solid fa-sun fa-lg"></i>';
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            body.classList.toggle('light-mode');
            
            let theme = 'dark';
            if (body.classList.contains('light-mode')) {
                theme = 'light';
                themeToggle.innerHTML = '<i class="fa-solid fa-sun fa-lg"></i>';
            } else {
                themeToggle.innerHTML = '<i class="fa-solid fa-moon fa-lg"></i>';
            }
            
            localStorage.setItem('theme', theme);
        });
    }

    function initHeroCarousel() {
        const slides = document.querySelectorAll('.hero-slide');
        if (!slides.length) return;

        let currentIndex = 0;
        setInterval(() => {
            slides[currentIndex].classList.remove('active');
            currentIndex = (currentIndex + 1) % slides.length;
            slides[currentIndex].classList.add('active');
        }, 6000);
    }

    initHeroCarousel();

    // Image preview overlay for product images (touch/click to open)
    (function initImagePreview() {
        const productImages = document.querySelectorAll('.product-image img, .product-card img');
        if (!productImages.length) return;

        function getImageSrcFromElement(el) {
            if (!el) return null;
            if (el.tagName && el.tagName.toLowerCase() === 'img') {
                return el.currentSrc || el.src || null;
            }
            const candidates = [el, el.parentElement, el.closest('.product-image')];
            for (const c of candidates) {
                if (!c) continue;
                const bg = window.getComputedStyle(c).backgroundImage;
                if (bg && bg !== 'none') {
                    const m = bg.match(/url\(["']?(.*?)["']?\)/);
                    if (m && m[1]) return m[1];
                }
            }
            return null;
        }

        function closePreview(overlay) {
            if (!overlay) return;
            overlay.classList.remove('open');
            setTimeout(() => {
                overlay.remove();
            }, 250); // Matches CSS transition duration
            document.body.style.overflow = '';
        }

        function openPreviewInContainer(img) {
            if (!img) return;
            const src = getImageSrcFromElement(img);
            const alt = img.alt || img.getAttribute('data-caption') || 'Imagen de producto';
            if (!src) return;

            const existing = document.querySelector('.img-preview-modal');
            if (existing) existing.remove();

            const overlay = document.createElement('div');
            overlay.className = 'img-preview-modal';
            overlay.innerHTML = `
                <div class="img-preview-content" role="dialog" aria-modal="true" aria-label="Vista previa de imagen">
                    <button type="button" class="img-preview-close" aria-label="Cerrar vista previa">&times;</button>
                    <img src="${src}" alt="${alt}">
                    <div class="img-preview-caption">${alt}</div>
                </div>
            `;

            const closeBtn = overlay.querySelector('.img-preview-close');

            closeBtn.addEventListener('click', () => closePreview(overlay));
            overlay.addEventListener('click', (event) => {
                if (event.target === overlay) {
                    closePreview(overlay);
                }
            });
            
            const escHandler = function(e) {
                if (e.key === 'Escape') {
                    closePreview(overlay);
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);

            document.body.appendChild(overlay);
            
            // Trigger transition animation
            requestAnimationFrame(() => {
                overlay.classList.add('open');
            });
            
            document.body.style.overflow = 'hidden';
        }

        productImages.forEach(img => {
            img.style.cursor = 'zoom-in';
            img.addEventListener('click', (e) => {
                e.stopPropagation();
                openPreviewInContainer(img);
            });

            const container = img.closest('.product-image') || img.parentElement;
            if (container && !container.querySelector('.preview-btn')) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'preview-btn';
                btn.setAttribute('aria-label', 'Ver imagen');
                btn.innerHTML = '<i class="fa-solid fa-eye"></i> Ver';
                btn.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    openPreviewInContainer(img);
                });
                container.appendChild(btn);
            }
        });
    })();

    // Shein-style Add to Cart Modal
    (function initCartModal() {
        const modalOverlay = document.getElementById('cartModal');
        const modalClose = document.getElementById('cartModalClose');
        const modalContinue = document.getElementById('cartModalContinue');
        const modalBody = document.getElementById('cartModalBody');
        let currentProductId = null;

        function openModal() {
            modalOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            modalOverlay.classList.remove('active');
            document.body.style.overflow = '';
            setTimeout(() => {
                modalBody.innerHTML = '';
            }, 300);
        }

        function showSuccessState(productName, productPrice, productImage) {
            modalBody.innerHTML = `
                <div class="cart-modal-success">
                    <div class="cart-modal-success-icon">
                        <i class="fa-solid fa-check"></i>
                    </div>
                    <h4>¡Añadido al carrito!</h4>
                    <p>${productName}</p>
                </div>
                <div class="cart-modal-product" style="border-bottom:none; padding-bottom:0;">
                    <div class="cart-modal-product-image">
                        <img src="${productImage}" alt="${productName}">
                    </div>
                    <div class="cart-modal-product-info">
                        <p class="cart-modal-product-name">${productName}</p>
                        <p class="cart-modal-product-price">${productPrice}</p>
                    </div>
                </div>
            `;
        }

        // Store base unit price when showing product
        let baseUnitPrice = 0;

        function showProductState(product) {
            const sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL'];
            
            // Extract numeric USD price from formatted string like "$15.00 / 600,00 Bs"
            const priceMatch = product.price.match(/\$?([\d,]+\.?\d*)/);
            baseUnitPrice = priceMatch ? parseFloat(priceMatch[1].replace(/,/g, '')) : 0;
            
            modalBody.innerHTML = `
                <div class="cart-modal-product">
                    <div class="cart-modal-product-image">
                        <img src="${product.image}" alt="${product.name}">
                    </div>
                    <div class="cart-modal-product-info">
                        <p class="cart-modal-product-name">${product.name}</p>
                        <p class="cart-modal-product-price">${product.price}</p>
                    </div>
                </div>
                <div class="cart-modal-options">
                    <div class="cart-modal-option-group">
                        <label>Selecciona tu talla</label>
                        <div class="size-chips" id="sizeChips">
                            ${sizes.map(s => `<button type="button" class="size-chip${s === 'M' ? ' selected' : ''}" data-size="${s}">${s}</button>`).join('')}
                        </div>
                    </div>
                    <div class="cart-modal-option-group">
                        <label>Cantidad</label>
                        <div class="qty-control">
                            <button type="button" class="qty-btn" id="qtyMinus" disabled>&minus;</button>
                            <input type="number" class="qty-value" id="qtyValue" value="1" min="1" max="99" readonly>
                            <button type="button" class="qty-btn" id="qtyPlus">+</button>
                        </div>
                    </div>
                </div>
                <div class="cart-modal-subtotal">
                    <span class="cart-modal-subtotal-label">Subtotal</span>
                    <span class="cart-modal-subtotal-value" id="subtotalValue">${product.price}</span>
                </div>
            `;
        }

        async function addToCart(productId, size, quantity) {
            try {
                const response = await fetch('/api/cart/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        product_id: productId,
                        size: size,
                        quantity: quantity
                    })
                });

                const data = await response.json();
                
                if (response.ok) {
                    updateCartCount(data.cart_count);
                    document.dispatchEvent(new CustomEvent('cartUpdated'));
                    return { success: true, data };
                } else {
                    return { success: false, error: data.mensaje || 'Error al añadir al carrito' };
                }
            } catch (error) {
                console.error('Error adding to cart:', error);
                return { success: false, error: 'Error de conexión' };
            }
        }

        function updateCartCount(count) {
            const cartCountElements = document.querySelectorAll('.nav-links a[href*="carrito"] span');
            cartCountElements.forEach(el => {
                el.textContent = count;
                el.style.display = count > 0 ? 'inline-block' : 'none';
            });
        }

        // Event delegation for add to cart buttons
        document.addEventListener('click', async (e) => {
            const addToCartBtn = e.target.closest('.btn-add-to-cart, .add-to-cart-btn');
            if (addToCartBtn) {
                e.preventDefault();
                currentProductId = addToCartBtn.dataset.productId;
                
                const product = {
                    id: currentProductId,
                    name: addToCartBtn.dataset.productName,
                    price: addToCartBtn.dataset.productPrice,
                    image: addToCartBtn.dataset.productImage
                };

                showProductState(product);
                openModal();
            }
        });

        modalOverlay.addEventListener('click', (e) => {
            if (e.target.closest('.cart-modal-close') || e.target === modalOverlay) {
                closeModal();
                return;
            }
        });

        // Size chip selection
        modalBody.addEventListener('click', (e) => {
            const chip = e.target.closest('.size-chip');
            if (chip) {
                document.querySelectorAll('.size-chip').forEach(c => c.classList.remove('selected'));
                chip.classList.add('selected');
            }
        });

        // Quantity +/- controls
        modalBody.addEventListener('click', (e) => {
            const qtyInput = document.getElementById('qtyValue');
            if (!qtyInput) return;
            
            if (e.target.closest('#qtyPlus')) {
                let val = parseInt(qtyInput.value) || 1;
                if (val < 99) {
                    val++;
                    qtyInput.value = val;
                    document.getElementById('qtyMinus').disabled = val <= 1;
                }
            }
            
            if (e.target.closest('#qtyMinus')) {
                let val = parseInt(qtyInput.value) || 1;
                if (val > 1) {
                    val--;
                    qtyInput.value = val;
                    document.getElementById('qtyMinus').disabled = val <= 1;
                }
            }

            // Update subtotal
            const priceText = document.getElementById('subtotalValue');
            if (priceText && baseUnitPrice > 0) {
                const qty = parseInt(qtyInput.value) || 1;
                const total = baseUnitPrice * qty;
                // Replace first number in the formatted price
                const originalPrice = priceText.textContent;
                priceText.textContent = originalPrice.replace(/[\d,]+\.?\d*/, total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}));
            }
        });

        modalContinue.addEventListener('click', async () => {
            if (!currentProductId) return;
            
            const selectedChip = document.querySelector('.size-chip.selected');
            const size = selectedChip ? selectedChip.dataset.size : 'M';
            const qtyInput = document.getElementById('qtyValue');
            const quantity = qtyInput ? parseInt(qtyInput.value) || 1 : 1;
            
            modalContinue.disabled = true;
            modalContinue.textContent = 'Añadiendo...';
            
            const result = await addToCart(currentProductId, size, quantity);
            
            if (result.success) {
                const productName = document.querySelector('.cart-modal-product-name')?.textContent || 'Producto';
                const productPrice = document.querySelector('.cart-modal-product-price')?.textContent || '';
                const productImage = document.querySelector('.cart-modal-product-image img')?.src || '';
                
                showSuccessState(productName, productPrice, productImage);
                
                setTimeout(() => {
                    closeModal();
                    modalContinue.disabled = false;
                    modalContinue.textContent = 'Seguir comprando';
                    // Peek cart dropdown for 3s after adding
                    setTimeout(() => document.dispatchEvent(new CustomEvent('peekCart')), 100);
                }, 1500);
            } else {
                alert(result.error);
                modalContinue.disabled = false;
                modalContinue.textContent = 'Seguir comprando';
            }
        });

        document.addEventListener('click', async (e) => {
            const viewCartLink = e.target.closest('.cart-modal-viewcart');
            if (viewCartLink && currentProductId) {
                e.preventDefault();
                
                const selectedChip = document.querySelector('.size-chip.selected');
                const size = selectedChip ? selectedChip.dataset.size : 'M';
                const qtyInput = document.getElementById('qtyValue');
                const quantity = qtyInput ? parseInt(qtyInput.value) || 1 : 1;
                
                viewCartLink.textContent = 'Añadiendo...';
                viewCartLink.style.pointerEvents = 'none';
                
                const result = await addToCart(currentProductId, size, quantity);
                
                if (result.success) {
                    window.location.href = viewCartLink.href;
                } else {
                    alert(result.error);
                    viewCartLink.textContent = 'Ver carrito';
                    viewCartLink.style.pointerEvents = 'auto';
                }
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modalOverlay.classList.contains('active')) {
                closeModal();
            }
        });
    })();

    // Cart dropdown logic
    (function initCartDropdown() {
        const container = document.querySelector('.cart-dropdown-container');
        const dropdown = document.getElementById('cartDropdown');
        const itemsContainer = document.getElementById('cartDropdownItems');
        const footer = document.getElementById('cartDropdownFooter');
        const totalEl = document.getElementById('cartDropdownTotal');
        const countEl = document.getElementById('cartDropdownCount');
        let cachedRate = null;
        let hoverTimer = null;

        async function getRate() {
            if (cachedRate) return cachedRate;
            try {
                const resp = await fetch('/api/tasa-cambio');
                const data = await resp.json();
                cachedRate = data.tasa;
                return cachedRate;
            } catch {
                cachedRate = 40;
                return cachedRate;
            }
        }

        function formatPriceUSD(amount) {
            return '$' + amount.toFixed(2);
        }

        function formatPriceBS(amount, rate) {
            const bs = amount * rate;
            return bs.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' Bs';
        }

        async function refreshDropdown() {
            if (!container || !dropdown) return;

            try {
                const resp = await fetch('/api/cart');
                const data = await resp.json();
                const cart = data.cart || [];
                const total = data.total || 0;
                const rate = await getRate();

                countEl.textContent = cart.length;

                if (!cart.length) {
                    itemsContainer.innerHTML = '<div class="cart-dropdown-empty">Tu carrito está vacío</div>';
                    footer.style.display = 'none';
                    return;
                }

                footer.style.display = 'flex';
                totalEl.textContent = formatPriceUSD(total) + ' / ' + formatPriceBS(total, rate);

                itemsContainer.innerHTML = cart.map(item => {
                    const itemTotal = item.price * (item.quantity || 1);
                    const details = item.size ? 'Talla: ' + item.size : (item.details || '');
                    return `
                        <div class="cart-dropdown-item">
                            <div class="cart-dropdown-item-info">
                                <p class="cart-dropdown-item-name">${item.name || 'Producto'}</p>
                                ${details ? '<p class="cart-dropdown-item-details">' + details + '</p>' : ''}
                                <p class="cart-dropdown-item-qty">Cant: ${item.quantity || 1}</p>
                            </div>
                            <div class="cart-dropdown-item-prices">
                                <span class="cart-dropdown-item-price-usd">${formatPriceUSD(itemTotal)}</span>
                                <span class="cart-dropdown-item-price-bs">${formatPriceBS(itemTotal, rate)}</span>
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('Error loading cart dropdown:', e);
            }
        }

        // Refresh dropdown on hover with debounce
        if (container) {
            container.addEventListener('mouseenter', () => {
                clearTimeout(hoverTimer);
                hoverTimer = setTimeout(refreshDropdown, 200);
            });
        }

        // Refresh when cart badge changes (item added via modal)
        document.addEventListener('cartUpdated', refreshDropdown);

        // Also refresh when navigating back to page
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) refreshDropdown();
        });

        // Peek cart dropdown for 3s (triggered after adding item)
        document.addEventListener('peekCart', async () => {
            await refreshDropdown();
            dropdown.classList.add('force-show');
            if (container) container.classList.add('force-hover');
            clearTimeout(window._peekTimer);
            window._peekTimer = setTimeout(() => {
                dropdown.classList.remove('force-show');
                if (container) container.classList.remove('force-hover');
            }, 3000);
        });
    })();
});
