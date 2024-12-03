window.onload = function() {
    let elements = document.querySelectorAll('.info-tab');
    elements.forEach((item) => {
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
}
