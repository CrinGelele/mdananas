window.addEventListener('load', function() {
    document.querySelectorAll('.competitor-toggle').forEach(checkbox => {
        const cu = checkbox.form.querySelector('[name="root_cu"]');
        const cmp = checkbox.form.querySelector('[name="root_cmp"]');
        const search = checkbox.form.querySelector('.cmp-search');
        const options = document.querySelector('#by-cmp-options').content;

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

        search.addEventListener('input', filterCmp);
        cmp.addEventListener('focus', filterCmp);

        function toggleSelect() {
            cu.style.display = checkbox.checked ? 'none' : '';
            cu.disabled = checkbox.checked;
            search.style.display = checkbox.checked ? '' : 'none';
            cmp.style.display = checkbox.checked ? '' : 'none';
            cmp.disabled = !checkbox.checked;
        }

        checkbox.addEventListener('change', toggleSelect);
        toggleSelect();
    });

    document.querySelectorAll('.auto-submit-input').forEach(input => {
        input.addEventListener('change', async (e) => {
            if (!e.isTrusted) return;
            e.preventDefault();
            const formData = new FormData(input.form);
            await fetch(input.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
});
