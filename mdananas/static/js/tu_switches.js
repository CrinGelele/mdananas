window.addEventListener('load', function() {
    document.getElementById('status-field').addEventListener('change', function() {
        const newStatusField = document.getElementById('new-status-field');
        if (this.value === 'new') {
            newStatusField.style.display = 'flex';
            newStatusField.disabled = false;
            this.style.display = 'none';
        } else {
            newStatusField.style.display = 'none';
        }
    });
    document.getElementById('type-field').addEventListener('change', function() {
        const newStatusField = document.getElementById('new-type-field');
        if (this.value === 'new') {
            newStatusField.style.display = 'flex';
            newStatusField.disabled = false;
            this.style.display = 'none';
        } else {
            newStatusField.style.display = 'none';
        }
    });
    document.getElementById('is_shared-field').addEventListener('change', function() {
        const newIsSharedField = document.getElementById('new-is_shared-field');
        if (this.value === 'new') {
            newIsSharedField.style.display = 'flex';
            newIsSharedField.disabled = false;
            this.style.display = 'none';
        } else {
            newIsSharedField.style.display = 'none';
        }
    });
});
