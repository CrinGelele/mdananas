window.addEventListener('load', function() {
        document.querySelectorAll('.new-general-field').forEach(field => {
        field.addEventListener('change', function() {
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.general-select').forEach(field => {
        field.addEventListener('change', function() {
            const newGeneralField = field.closest('td').querySelector('.new-general-field');
            if (this.value === 'new') {
                newGeneralField.style.display = 'flex';
                newGeneralField.disabled = false;
                this.style.display = 'none';
            } else {
                newGeneralField.style.display = 'none';
            }
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.new-channel-field').forEach(field => {
        field.addEventListener('change', function() {
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.channel-select').forEach(field => {
        field.addEventListener('change', function() {
            const newChannelField = field.closest('td').querySelector('.new-channel-field');
            if (this.value === 'new') {
                newChannelField.style.display = 'flex';
                newChannelField.disabled = false;
                this.style.display = 'none';
            } else {
                newChannelField.style.display = 'none';
            }
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.new-brand-field').forEach(field => {
        field.addEventListener('change', function() {
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.brand-select').forEach(field => {
        field.addEventListener('change', function() {
            const newBrandField = field.closest('td').querySelector('.new-brand-field');
            if (this.value === 'new') {
                newBrandField.style.display = 'flex';
                newBrandField.disabled = false;
                this.style.display = 'none';
            } else {
                newBrandField.style.display = 'none';
            }
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.new-group-field').forEach(field => {
        field.addEventListener('change', function() {
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.group-select').forEach(field => {
        field.addEventListener('change', function() {
            const newGroupField = field.closest('td').querySelector('.new-group-field');
            if (this.value === 'new') {
                newGroupField.style.display = 'flex';
                newGroupField.disabled = false;
                this.style.display = 'none';
            } else {
                newGroupField.style.display = 'none';
            }
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
        document.querySelectorAll('.new-subgroup-field').forEach(field => {
        field.addEventListener('change', function() {
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
    document.querySelectorAll('.subgroup-select').forEach(field => {
        field.addEventListener('change', function() {
            const newSubgroupField = field.closest('td').querySelector('.new-subgroup-field');
            if (this.value === 'new') {
                newSubgroupField.style.display = 'flex';
                newSubgroupField.disabled = false;
                this.style.display = 'none';
            } else {
                newSubgroupField.style.display = 'none';
            }
            const formData = new FormData(this.form);
            fetch(this.form.action, {
                method: 'POST',
                body: formData,
            });
        });
    });
});
