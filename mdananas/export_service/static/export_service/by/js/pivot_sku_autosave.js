window.addEventListener('load', function() {
    document.querySelectorAll('.auto-submit-input').forEach(input => {
        input.addEventListener('change', async (e) => {
            if (!e.isTrusted) return;
            e.preventDefault();
            const formData = new FormData(input.form);
            await fetch(input.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
});
