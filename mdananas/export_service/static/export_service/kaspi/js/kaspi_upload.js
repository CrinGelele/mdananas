const form = document.getElementById('kaspi-upload-form');
const input = document.getElementById('kaspi-file-input');
const label = form.querySelector('.plus-upload-btn');
const icon = form.querySelector('.plus-icon');
const status = form.querySelector('.kaspi-status');

input.addEventListener('change', () => {
    if (input.files.length) {
        form.requestSubmit();
    }
});

label.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        input.click();
    }
});

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(form);
    input.disabled = true;
    form.classList.add('is-loading');
    icon.textContent = '0%';
    status.classList.remove('error');
    status.textContent = '';
    const timer = setInterval(() => {
        fetch('get-progress/')
            .then(response => response.json())
            .then(result => {
                if (input.disabled) icon.textContent = result.kaspi_sales_file_progress + '%';
            })
            .catch(() => {});
    }, 500);

    try {
        const response = await fetch(form.action, { method: 'POST', body: data });
        const result = await response.json();
        if (response.ok && result.status === 'success') {
            icon.textContent = '100%';
            window.location.href = result.redirect_url;
        } else {
            status.classList.add('error');
            status.textContent = result.message || 'Не удалось загрузить файл.';
        }
    } catch {
        status.classList.add('error');
        status.textContent = 'Не удалось получить ответ сервера. Повторите загрузку.';
    } finally {
        clearInterval(timer);
        input.disabled = false;
        input.value = '';
        form.classList.remove('is-loading');
        icon.textContent = '+';
    }
});
