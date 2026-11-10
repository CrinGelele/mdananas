window.addEventListener('load', function() {
    document.querySelectorAll('#kaspi_pivot_sku_table .auto-submit-form').forEach(form => {
        const checkbox = form.querySelector('.competitor-toggle');
        const cu = form.querySelector('[name="root_cu"]');
        const cmp = form.querySelector('[name="root_cmp"]');
        const search = form.querySelector('.cmp-search');
        const status = form.querySelector('.mapping-status');
        const options = document.querySelector('#kaspi-cmp-options').content;

        if (cmp.dataset.selected) {
            const selected = options.querySelector(`option[value="${cmp.dataset.selected}"]`);
            if (selected) {
                cmp.appendChild(selected.cloneNode(true));
                cmp.value = cmp.dataset.selected;
            }
        }

        function filterCmp() {
            const value = cmp.value;
            const selected = cmp.selectedOptions[0].cloneNode(true);
            const query = search.value.trim().toLowerCase();
            cmp.replaceChildren(cmp.options[0].cloneNode(true));
            if (value) {
                cmp.appendChild(selected);
            }
            let count = 0;
            options.querySelectorAll('option').forEach(option => {
                if (count < 50 && option.textContent.toLowerCase().includes(query)) {
                    if (option.value !== value) {
                        cmp.appendChild(option.cloneNode(true));
                    }
                    count++;
                }
            });
            cmp.value = value;
        }

        function toggleSelect() {
            cu.style.display = checkbox.checked ? 'none' : '';
            cu.disabled = checkbox.checked;
            search.style.display = checkbox.checked ? 'block' : 'none';
            cmp.style.display = checkbox.checked ? 'block' : 'none';
            cmp.disabled = !checkbox.checked;
        }

        search.addEventListener('input', filterCmp);
        cmp.addEventListener('focus', filterCmp);
        checkbox.addEventListener('change', toggleSelect);
        toggleSelect();
        form.addEventListener('submit', event => event.preventDefault());

        form.querySelectorAll('.auto-submit-input').forEach(input => {
            input.addEventListener('change', async () => {
                const data = new FormData(form);
                status.classList.remove('error');
                status.textContent = 'Сохраняется…';
                cu.disabled = true;
                cmp.disabled = true;
                checkbox.disabled = true;
                try {
                    const response = await fetch(form.action, { method: 'POST', body: data });
                    const result = await response.json();
                    if (!response.ok || result.status !== 'success') {
                        throw new Error(result.message || 'Не удалось сохранить связь.');
                    }
                    status.textContent = result.mapping_status;
                } catch (error) {
                    status.classList.add('error');
                    status.textContent = error.message;
                } finally {
                    checkbox.disabled = false;
                    toggleSelect();
                }
            });
        });
    });
});
