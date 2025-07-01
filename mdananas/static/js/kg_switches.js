window.addEventListener('load', function() {
    document.getElementById('chain-field').addEventListener('change', function() {
        const newChainField = document.getElementById('new-chain-field');
        if (this.value === 'new') {
            newChainField.style.display = 'flex';
            newChainField.disabled = false;
            this.style.display = 'none';
        } else {
            newChainField.style.display = 'none';
        }
    });
    document.getElementById('type-field').addEventListener('change', function() {
        const newTypeField = document.getElementById('new-type-field');
        if (this.value === 'new') {
            newTypeField.style.display = 'flex';
            newTypeField.disabled = false;
            this.style.display = 'none';
        } else {
            newTypeField.style.display = 'none';
        }
    });
});
