function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith(name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

window.addEventListener('load', function() {
    const save_btn = this.document.getElementById('ref-stores-save-btn');
    save_btn.addEventListener('click', function() {
        result = []
        document.querySelectorAll('.ref-stores-form').forEach(form => {
            formData = new FormData(form);
            if (formData.get('form_changed') === "1") {
            data = {}
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            result.push(data);
        }
        });
        fetch('save-stores/', {  // Укажите ваш URL
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),  // Необходимо для CSRF
                },
                body: JSON.stringify({ forms: result }),
        })
        .then(response => response.json())
        .then(data => { 
            if (data.status === 'success') {
                window.location.href = data.redirect_url;
            }
        });
    });
});
