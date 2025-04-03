// Функция для форматирования валюты
function formatCurrency(amount, currency = 'KZT') {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: currency,
        maximumFractionDigits: 0
    }).format(amount);
}

// Функция для обработки ошибок API
function handleApiError(error) {
    console.error('API Error:', error);
    const errorMessage = error.response?.data?.error || 'Произошла ошибка при выполнении запроса';
    alert(errorMessage);
}

// Функция для проверки авторизации
function checkAuth() {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        window.location.href = '/login';
    }
    return token;
}

// Функция для обновления активного пункта меню
function updateActiveMenuItem() {
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.nav-link');
    
    menuItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    updateActiveMenuItem();
    
    // Обработка форм
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            try {
                const formData = new FormData(form);
                const response = await fetch(form.action, {
                    method: form.method,
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const data = await response.json();
                if (data.redirect) {
                    window.location.href = data.redirect;
                }
            } catch (error) {
                handleApiError(error);
            }
        });
    });
}); 