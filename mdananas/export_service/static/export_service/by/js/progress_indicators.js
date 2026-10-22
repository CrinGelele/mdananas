window.addEventListener('load', function() {
    const form = document.getElementById('sales-file-upload-form');
    const input = document.getElementById('sales-file-input');
    const percent = document.getElementById('sales-progress-percent');
    const message = document.getElementById('by-upload-message');
    input.addEventListener('change', function() {
        if (!input.files.length) return;
        const formData = new FormData(form);
        input.disabled = true;
        percent.textContent = '0%';
        percent.style.fontSize = '20px';
        const timer = setInterval(() => {
            fetch('get-progress/')
                .then(response => response.json())
                .then(data => {percent.textContent = data.by_sales_file_progress + '%';});
        }, 500);
        fetch(form.action, {method: 'POST', body: formData})
            .then(async response => {
                const data = await response.json();
                if (!response.ok || data.status === 'error') throw new Error(data.message || 'Ошибка загрузки');
                if (data.status === 'success') {
                    window.location.href = data.redirect_url;
                } else {
                    percent.textContent = '100%';
                    message.textContent = data.message + ' Строк: ' + data.rows;
                }
            })
            .catch(error => {message.textContent = error.message; percent.textContent = '+';})
            .finally(() => {clearInterval(timer); input.disabled = false;});
    });
});
