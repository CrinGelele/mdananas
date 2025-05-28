window.addEventListener('load', function() {
    let elements = document.querySelectorAll('.info-tab');
    elements.forEach((item) => {
        if (item.open) {
            item.querySelector('.info-tab-label-form-save-btn').style.display = 'block';
        } else {
            item.querySelector('.info-tab-label-form-save-btn').style.display = 'none';
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
    });
});
