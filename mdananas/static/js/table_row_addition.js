window.addEventListener('load', function() {
    const totalFormsInput = document.getElementById('id_mixcomposition_set-TOTAL_FORMS');
    let formCount = parseInt(totalFormsInput.value);
    const tableBody = document.querySelector('#components-table tbody');

    function isRowFilled(row) {
        const cuSelect = row.querySelector('select[name*="root_cu"]');  // Изменили на root_cu
        const quantityInput = row.querySelector('input[name*="quantity"]');
        return cuSelect && cuSelect.value !== '' && quantityInput && quantityInput.value !== '';
    }

    function removeRow(row) {
        const deleteInput = row.querySelector('input[name*="DELETE"]');
        if (deleteInput) {
            deleteInput.value = 'on';
        }
        row.style.display = 'none';
    }

    function setupRowEventListeners(row) {
        const removeBtn = row.querySelector('.remove-row-btn');
        if (removeBtn) {
            removeBtn.addEventListener('click', function() {
                removeRow(row);
            });
        }

        const inputs = row.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.addEventListener('change', function() {
                if (isRowFilled(row)) {
                    const rows = tableBody.querySelectorAll('tr.component-row');
                    if (row === rows[rows.length - 1]) {
                        addNewRow();
                    }
                }
            });
        });
    }

    function updateTotalForms() {
        const rows = tableBody.querySelectorAll('tr.component-row');
        totalFormsInput.value = rows.length;
    }

    function addNewRow() {
        const newRow = document.createElement('tr');
        newRow.className = 'component-row';
        const templateRow = tableBody.querySelector('tr');
        newRow.innerHTML = templateRow.innerHTML;
        
        // Обновляем индексы
        const newIndex = formCount++;
        newRow.innerHTML = newRow.innerHTML.replace(/form-(\d+)/g, `form-${newIndex}`);
        // Очищаем значения
        newRow.querySelectorAll('input, select').forEach(input => {
            if (input.name.includes('root_cu')) input.value = '';
            if (input.name.includes('quantity')) input.value = '';
            if (input.name.includes('DELETE')) {
                input.value = ''; // Сбрасываем значение DELETE
                input.type = 'hidden'; // Делаем скрытым
            }
            input.required = false;
        });
        
        tableBody.appendChild(newRow);
        updateTotalForms();
        setupRowEventListeners(newRow);
    }

    // Инициализация
    document.querySelectorAll('tr.component-row').forEach(row => {
        setupRowEventListeners(row);
    });

    // Добавляем новую строку, если последняя заполнена
    const lastRow = tableBody.querySelector('tr.component-row:last-child');
    if (!lastRow || isRowFilled(lastRow)) {
        addNewRow();
    }
});