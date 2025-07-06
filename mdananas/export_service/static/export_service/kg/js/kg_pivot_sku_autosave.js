window.addEventListener('load', function() {
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }
    const scrollableDiv = document.getElementById('kg_pivot_sku_table');

    document.querySelectorAll('.auto-submit-form').forEach(form => {
        form.addEventListener('change', async (e) => {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
            });
        });
    });
    document.querySelectorAll('.predict-form').forEach(form => {
        form.addEventListener('submit', async (e) => {
            const scrollPos = scrollableDiv.scrollTop;
            e.target.querySelector('.scroll-position-input').value = scrollPos;
        });
    });
    const scrollPos = getCookie('scroll_pos');
    if (scrollPos) {
        scrollableDiv.scrollTop = parseInt(scrollPos);
        document.cookie = 'scroll_pos=; Max-Age=0; path=/'; // Удаляем cookie
    }
});
