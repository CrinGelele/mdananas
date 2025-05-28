window.addEventListener('load', function() {
    document.getElementById('category-field').addEventListener('change', function() {
        const newCategoryField = document.getElementById('new-category-field');
        if (this.value === 'new') {
            newCategoryField.style.display = 'flex';
            newCategoryField.disabled = false;
            this.style.display = 'none';
        } else {
            newCategoryField.style.display = 'none';
        }
    });
    document.getElementById('groupname-field').addEventListener('change', function() {
        const newGroupnameField = document.getElementById('new-groupname-field');
        if (this.value === 'new') {
            newGroupnameField.style.display = 'flex';
            newGroupnameField.disabled = false;
            this.style.display = 'none';
        } else {
            newGroupnameField.style.display = 'none';
        }
    });
});
