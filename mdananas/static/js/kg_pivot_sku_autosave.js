window.addEventListener('load', function() {
    document.querySelectorAll('.auto-submit-form').forEach(form => {
        form.addEventListener('change', async (e) => {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
            });
        });
    });
});
