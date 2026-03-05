let cart = [];
let taxRate = 0.15;

document.addEventListener('DOMContentLoaded', function () {
    const taxVal = document.getElementById('taxRateValue');
    if (taxVal) {
        taxRate = parseFloat(taxVal.value) / 100;
    }
    renderCart();

    // Search filter
    const searchInput = document.getElementById('productSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function (e) {
            const term = e.target.value.toLowerCase();
            const cards = document.querySelectorAll('#productList .col');
            cards.forEach(card => {
                const name = card.querySelector('h6').innerText.toLowerCase();
                if (name.includes(term)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
        // Keyboard shortcuts
        document.addEventListener('keydown', function (e) {
            if (e.key === 'F10') {
                e.preventDefault();
                finalizeSale('cash');
            }
            if (e.key === 'F9') {
                e.preventDefault();
                finalizeSale('card');
            }
            if (e.key === 'F2') {
                e.preventDefault();
                if (searchInput) searchInput.focus();
            }
        });
    }
});

function addToCart(id, name, price, stock) {
    console.log(`Adding to cart: ID=${id}, Name=${name}, Price=${price}, Stock=${stock}`);
    stock = parseInt(stock) || 0;
    const existingItem = cart.find(item => item.id === id);
    const currentQty = existingItem ? existingItem.quantity : 0;

    if (currentQty + 1 > stock) {
        Swal.fire({
            title: 'نقص في المخزون',
            text: `الكمية المطلوبة تتجاوز المتوفر (${stock}) لهذا الكتاب`,
            icon: 'warning',
            timer: 2000,
            showConfirmButton: false
        });
        return;
    }

    if (existingItem) {
        existingItem.quantity += 1;
    } else {
        cart.push({ id, name, price, quantity: 1, maxStock: stock });
    }
    renderCart();
    showRecommendations(id);
}

function removeFromCart(id) {
    cart = cart.filter(item => item.id !== id);
    renderCart();
}

function updateQuantity(id, qty) {
    const item = cart.find(item => item.id === id);
    if (item) {
        item.quantity = parseInt(qty) || 0;
        if (item.quantity <= 0) {
            removeFromCart(id);
        }
    }
    renderCart();
}

function clearCart() {
    Swal.fire({
        title: 'هل أنت متأكد؟',
        text: "سيتم حذف جميع العناصر من السلة",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'نعم، احذف',
        cancelButtonText: 'إلغاء'
    }).then((result) => {
        if (result.isConfirmed) {
            cart = [];
            renderCart();
        }
    })
}

function renderCart() {
    const cartContainer = document.getElementById('cartItems');
    const cartCount = document.getElementById('cartCount');

    if (cart.length === 0) {
        cartContainer.innerHTML = `
            <div class="text-center py-5 text-muted empty-cart-msg">
                <i class="fas fa-shopping-basket fa-3x mb-3 opacity-25"></i>
                <p>السلة فارغة</p>
            </div>
        `;
        cartCount.innerText = '0';
        updateTotals(0);
        return;
    }

    cartCount.innerText = cart.reduce((acc, item) => acc + item.quantity, 0);

    let html = '';
    let subtotal = 0;

    cart.forEach(item => {
        const itemTotal = item.price * item.quantity;
        subtotal += itemTotal;
        html += `
            <div class="cart-item">
                <div class="flex-grow-1">
                    <h6 class="mb-1">${item.name}</h6>
                    <small class="text-primary">${item.price} SAR</small>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <input type="number" class="form-control form-control-sm quantity-input" 
                           value="${item.quantity}" onchange="updateQuantity(${item.id}, this.value)">
                    <button class="btn btn-sm btn-link text-danger p-0" onclick="removeFromCart(${item.id})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;
    });

    cartContainer.innerHTML = html;
    updateTotals(subtotal);
}

function updateTotals(subtotal) {
    const tax = subtotal * taxRate;
    const total = subtotal + tax;

    document.getElementById('subtotal').innerText = subtotal.toFixed(2) + ' SAR';
    document.getElementById('tax').innerText = tax.toFixed(2) + ' SAR';
    document.getElementById('total').innerText = total.toFixed(2) + ' SAR';
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function finalizeSale(paymentMethod) {
    if (cart.length === 0) {
        Swal.fire('خطأ', 'السلة فارغة!', 'error');
        return;
    }

    const customerId = document.getElementById('customerSelect').value;

    const data = {
        customer_id: customerId,
        payment_method: paymentMethod,
        items: cart.map(item => ({
            product_id: item.id,
            quantity: item.quantity,
            price: item.price
        }))
    };

    Swal.fire({
        title: 'جاري إتمام العملية...',
        didOpen: () => {
            Swal.showLoading();
        }
    });

    fetch('/sales/pos/finalize/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(data)
    })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                Swal.fire({
                    title: 'تمت العملية بنجاح!',
                    text: `رقم الفاتورة: ${result.invoice_number}`,
                    icon: 'success',
                    showCancelButton: true,
                    confirmButtonText: 'طباعة الفاتورة',
                    cancelButtonText: 'متابعة البيع'
                }).then((selection) => {
                    if (selection.isConfirmed) {
                        window.open(`/sales/invoices/${result.invoice_id}/pdf/`, '_blank');
                    }
                    cart = [];
                    renderCart();
                });
            } else {
                Swal.fire('فشل العملية', result.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            Swal.fire('خطأ غير متوقع', 'حدث خطأ أثناء محاولة حفظ الفاتورة', 'error');
        });
}

function openWhatsApp(phone, text) {
    if (!phone) {
        Swal.fire('تنبيه', 'لا يوجد رقم جوال مسجل لهذا العميل', 'info');
        return;
    }
    const cleanPhone = phone.replace(/\D/g, '');
    const url = `https://wa.me/${cleanPhone}/?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

function showRecommendations(productId) {
    fetch(`/sales/pos/recommend/${productId}/`)
        .then(res => res.json())
        .then(data => {
            if (data.recommended && data.recommended.length > 0) {
                let html = '<div class="row g-2">';
                data.recommended.forEach(book => {
                    html += `
                        <div class="col-6">
                            <div class="card p-2 text-center" style="cursor:pointer;" onclick="addToCart(${book.id}, '${book.name}', ${book.price}, ${book.stock}); Swal.close();">
                                <small class="fw-bold text-truncate d-block">${book.name}</small>
                                <span class="text-primary small">${book.price} SAR</span>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';

                Swal.fire({
                    title: 'قد يعجبك أيضاً ✨',
                    html: html,
                    showConfirmButton: false,
                    position: 'bottom-end',
                    showCloseButton: true,
                    backdrop: false,
                    timer: 15000,
                    width: '300px'
                });
            }
        });
}
