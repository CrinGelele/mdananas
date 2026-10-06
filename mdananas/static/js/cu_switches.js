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
    document.getElementById('root_pd-field').addEventListener('change', function() {
        const newDefinitionField = document.getElementById('new-rus_definition-field');
        if (this.value === 'new') {
            newDefinitionField.style.display = 'flex';
            newDefinitionField.disabled = false;
            this.style.display = 'none';
        } else {
            newDefinitionField.style.display = 'none';
            newDefinitionField.value = null;
        }
    });
    document.getElementById('supplier-field').addEventListener('change', function() {
        const newSupplierField = document.getElementById('new-supplier_name-field');
        const ownershipField = document.getElementById('ownership-field');
        const currencyField = document.getElementById('currency-field');
        if (this.value === 'new') {
            newSupplierField.style.display = 'flex';
            newSupplierField.disabled = false;
            ownershipField.value = null;
            ownershipField.classList.remove('input-inactive');
            currencyField.value = null;
            currencyField.classList.remove('input-inactive');
            this.style.display = 'none';
        } else {
            newSupplierField.style.display = 'none';
            newSupplierField.value = null;
            fetch(`/root/cu/get-supplier-info/?supplier_id=${this.value}`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    ownershipField.value = data.ownership;
                    currencyField.value = data.currency;
                })
            ownershipField.classList.add('input-inactive');
            currencyField.classList.add('input-inactive');
        }
    });
});
