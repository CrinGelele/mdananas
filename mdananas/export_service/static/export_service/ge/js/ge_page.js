const gePage = document.querySelector('.ge-page');

function updateMappingButton(select) {
    const button = select.form.querySelector('button[type=submit]');
    button.hidden = !select.value;
    button.disabled = button.hidden;
}

function filterCompetitors(search) {
    const select = search.form.querySelector('select');
    const query = search.value.trim().toLowerCase();
    if (select.dataset.query === query) return;
    const placeholder = select.options[0];
    select.replaceChildren(placeholder);
    const options = document.getElementById(select.dataset.options).content;
    for (const option of options.children) {
        if (option.textContent.toLowerCase().includes(query)) select.append(option.cloneNode(true));
    }
    placeholder.textContent = select.options.length === 1 ? 'Совпадений нет' : '—';
    select.value = '';
    select.dataset.query = query;
    updateMappingButton(select);
}

function loadSelectOptions(event) {
    const select = event.target.closest('select[data-options]');
    if (!select) return;
    const search = select.form.querySelector('[data-cmp-search]');
    if (search) {
        filterCompetitors(search);
    } else if (select.options.length === 1) {
        select.append(document.getElementById(select.dataset.options).content.cloneNode(true));
    }
}

gePage.addEventListener('focusin', loadSelectOptions);
gePage.addEventListener('pointerdown', loadSelectOptions);

gePage.addEventListener('input', event => {
    if (event.target.matches('[data-cmp-search]')) filterCompetitors(event.target);
});

window.addEventListener('pageshow', () => {
    for (const select of gePage.querySelectorAll('.ge-mapping select')) {
        select.value = '';
        updateMappingButton(select);
    }
});

gePage.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.isComposing && event.target.matches('[data-cmp-search]')) {
        event.preventDefault();
    }
});

gePage.addEventListener('change', event => {
    const input = event.target;
    if (input.matches('.ge-mapping select')) {
        updateMappingButton(input);
    } else if (input.matches('input[type=file]') && input.files.length) {
        input.form.requestSubmit();
    }
});

const uploads = gePage.querySelector('.ge-uploads');
uploads.addEventListener('submit', async event => {
    event.preventDefault();
    const form = event.target;
    const data = new FormData(form);
    const uploadId = crypto.getRandomValues(new Uint32Array(2)).join('-');
    data.set('ge_upload_id', uploadId);
    const progressUrl = uploads.dataset.progressUrl + '?upload_id=' + uploadId;
    const icon = form.querySelector('.plus-icon');
    const status = uploads.querySelector('.ge-status');
    const inputs = uploads.querySelectorAll('input[type=file]');

    inputs.forEach(input => { input.disabled = true; });
    form.classList.add('is-loading');
    icon.textContent = '0%';
    status.classList.remove('error');
    status.textContent = 'Загрузка…';

    let loading = true;
    async function updateProgress() {
        try {
            const response = await fetch(progressUrl, {cache: 'no-store'});
            const result = await response.json();
            if (loading && response.ok) icon.textContent = result.upload_progress + '%';
        } catch {
            // Ошибка опроса не прерывает загрузку.
        }
        if (loading) timer = setTimeout(updateProgress, 500);
    }
    let timer = setTimeout(updateProgress, 500);

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {'X-Requested-With': 'XMLHttpRequest'},
            body: data
        });
        const result = await response.json();
        if (response.ok && result.status === 'success') {
            icon.textContent = '100%';
            status.textContent = result.message;
            window.location.assign(form.action);
            return;
        }
        status.classList.add('error');
        status.textContent = result.message || 'Не удалось загрузить файл.';
    } catch {
        status.classList.add('error');
        status.textContent = 'Не удалось получить ответ сервера.';
    } finally {
        loading = false;
        clearTimeout(timer);
    }
    form.classList.remove('is-loading');
    form.reset();
    icon.textContent = '';
    inputs.forEach(input => { input.disabled = false; });
});

for (const button of gePage.querySelectorAll('[data-dialog]')) {
    const dialog = document.getElementById(button.dataset.dialog);
    button.addEventListener('click', () => dialog.showModal());
    dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
    dialog.querySelector('select[name^=edit_]')?.addEventListener('change', event => event.target.form.requestSubmit());
    const reportSku = dialog.querySelector('[data-report-sku]');
    if (reportSku) {
        const updateFields = () => {
            const newCard = reportSku.value && !reportSku.selectedOptions[0].hasAttribute('data-existing-card');
            dialog.querySelectorAll('[data-card-field]').forEach(label => {
                label.style.display = newCard ? '' : 'none';
                label.querySelector('input').disabled = !newCard;
            });
            reportSku.form.querySelector('[type=submit]').textContent = newCard ? 'Добавить и сопоставить' : 'Сопоставить';
        };
        reportSku.addEventListener('change', updateFields);
        updateFields();
    }
    if (dialog.dataset.returnUrl) {
        dialog.addEventListener('close', () => window.location.replace(dialog.dataset.returnUrl));
    }
    if (dialog.hasAttribute('data-open') && !document.querySelector('dialog[open]')) dialog.showModal();
}
