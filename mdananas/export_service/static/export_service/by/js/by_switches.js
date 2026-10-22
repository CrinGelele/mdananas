window.addEventListener('load', function() {
    function addSwitch(name) {
        document.querySelectorAll('.' + name + '-select').forEach(field => {
            field.addEventListener('change', function() {
                const newField = this.form.querySelector('.new-' + name + '-field');
                if (this.value === 'new') {
                    newField.style.display = 'flex';
                    newField.disabled = false;
                    this.disabled = true;
                    this.style.display = 'none';
                } else {
                    fetch(this.form.action, {method: 'POST', body: new FormData(this.form)});
                }
            });
        });
        document.querySelectorAll('.new-' + name + '-field').forEach(field => {
            field.addEventListener('change', function() {
                fetch(this.form.action, {method: 'POST', body: new FormData(this.form)});
            });
        });
    }
    addSwitch('chain');
    addSwitch('channel');
});
