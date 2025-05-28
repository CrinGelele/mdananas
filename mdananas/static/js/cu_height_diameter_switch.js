window.addEventListener('load', function() {
    const lengthField = document.getElementById('length-field');
    const widthField = document.getElementById('width-field');
    const diameterField = document.getElementById('diameter-field');
    if (lengthField.value.trim() !== '' || widthField.value.trim() !== '') {
        diameterField.disabled = true;
        diameterField.classList.add('input-inactive');
    }
    if (diameterField.value.trim() !== '') {
        lengthField.disabled = true;
        lengthField.classList.add('input-inactive');
        widthField.disabled = true;
        widthField.classList.add('input-inactive');
    }
    lengthField.addEventListener('input', function() {
        if (lengthField.value.trim() !== '' || widthField.value.trim() !== '') {
            diameterField.disabled = true;
            diameterField.classList.add('input-inactive');
        } else {
            diameterField.disabled = false;
            diameterField.classList.remove('input-inactive');
        }
    });
    widthField.addEventListener('input', function() {
        if (lengthField.value.trim() !== '' || widthField.value.trim() !== '') {
            diameterField.disabled = true;
            diameterField.classList.add('input-inactive');
        } else {
            diameterField.disabled = false;
            diameterField.classList.remove('input-inactive');
        }
        
    });
    diameterField.addEventListener('input', function() {
        if (diameterField.value.trim() !== '') {
            lengthField.disabled = true;
            lengthField.classList.add('input-inactive');
            widthField.disabled = true;
            widthField.classList.add('input-inactive');
        } else {
            lengthField.disabled = false;
            lengthField.classList.remove('input-inactive');
            widthField.disabled = false;
            widthField.classList.remove('input-inactive');
        }
    });
});

