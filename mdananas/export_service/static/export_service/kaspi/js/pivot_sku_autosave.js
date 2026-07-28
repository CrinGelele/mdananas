window.addEventListener('load', function() {
    document.querySelectorAll('.auto-submit-input').forEach(input => {
        input.addEventListener('change', async (e) => {
            if (!e.isTrusted) {  // isTrusted = false для программных событий
                return;
            }
            e.preventDefault();
            if (input.type == 'checkbox') {
                if (input.checked) {
                    input.closest('tr').querySelector('.mix-select').style.display = 'flex';
                    input.closest('tr').querySelector('.cu-select').style.display = 'none';
                    input.closest('tr').querySelector('.mix-select').disabled = false;
                    input.closest('tr').querySelector('.cu-select').disabled = true;
                } else {
                    input.closest('tr').querySelector('.mix-select').style.display = 'none';
                    input.closest('tr').querySelector('.cu-select').style.display = 'flex';
                    input.closest('tr').querySelector('.mix-select').disabled = true;
                    input.closest('tr').querySelector('.cu-select').disabled = false;
                }
            }
            const formData = new FormData(input.form);
            const response = await fetch(input.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
});
