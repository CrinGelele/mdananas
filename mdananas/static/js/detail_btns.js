window.addEventListener('load', function() {
    let elements = document.querySelectorAll('.info-tab');
    elements.forEach((item) => {
        btn = item.querySelector('.info-tab-label-form-save-btn');
        if (btn) {
            if (item.open) {
                btn.style.display = 'block';
            } else {
                btn.style.display = 'none';
            }
            item.addEventListener('toggle', clickEvent = () => {
                btn = item.querySelector('.info-tab-label-form-save-btn');
                if (btn.style.display !== 'none') {
                    btn.style.display = 'none';
                }
                else {
                    btn.style.display = 'block';
                }
            })
        }
    });
});
