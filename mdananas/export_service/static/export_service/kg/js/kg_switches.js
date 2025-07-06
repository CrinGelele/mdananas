window.addEventListener('load', function() {
    document.querySelectorAll('.chain-field').forEach(field => {
        field.addEventListener('change', function() {
            const newChainField = field.closest('td').querySelector('#new-chain-field');
            field.closest('tr').querySelector('#form_changed').setAttribute('value', '1');
            if (this.value === 'new') {
                newChainField.style.display = 'flex';
                newChainField.disabled = false;
                this.style.display = 'none';
            } else {
                newChainField.style.display = 'none';
            }
        });
    });
    document.querySelectorAll('.type-field').forEach(field => {
        field.addEventListener('change', function() {
            const newTypeField = field.closest('td').querySelector('#new-type-field');
            field.closest('tr').querySelector('#form_changed').setAttribute('value', '1');
            if (this.value === 'new') {
                newTypeField.style.display = 'flex';
                newTypeField.disabled = false;
                this.style.display = 'none';
            } else {
                newTypeField.style.display = 'none';
            }
        });
    });
    document.querySelectorAll('.groupname-field').forEach(field => {
        field.addEventListener('change', function() {
            const newGroupnameField = field.closest('td').querySelector('#new-groupname-field');
            field.closest('tr').querySelector('#form_changed').setAttribute('value', '1');
            if (this.value === 'new') {
                newGroupnameField.style.display = 'flex';
                newGroupnameField.disabled = false;
                this.style.display = 'none';
            } else {
                newGroupnameField.style.display = 'none';
            }
        });
    });
    document.querySelectorAll('.category-field').forEach(field => {
        field.addEventListener('change', function() {
            const newCategoryField = field.closest('td').querySelector('#new-category-field');
            field.closest('tr').querySelector('#form_changed').setAttribute('value', '1');
            if (this.value === 'new') {
                newCategoryField.style.display = 'flex';
                newCategoryField.disabled = false;
                this.style.display = 'none';
            } else {
                newCategoryField.style.display = 'none';
            }
        });
    });
});
