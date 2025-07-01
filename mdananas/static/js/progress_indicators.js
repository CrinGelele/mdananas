function trackSalesFileProcessingProgress() {
    const percentElement = document.getElementById('sales-file-upload-form').querySelector('#progress-percent');
    const inputElement = document.getElementById('sales-file-upload-form').querySelector('#file-input');
    percentElement.textContent = '0%';
    percentElement.style.fontSize = '20px';
    inputElement.disabled = true;
    const progressInterval = setInterval(() => {
        fetch('sales-file-processing-progress/')
            .then(response => response.json())
            .then(data => {
                if (!data.sales_file_processing_active) {
                    clearInterval(progressInterval);
                } else {
                    percentElement.textContent = data.sales_file_processing_progress + '%';
                }
            });
    }, 500);
    return progressInterval
}

function clearSalesFileProcessingProgress() {
    const percentElement = document.getElementById('sales-file-upload-form').querySelector('#progress-percent');
    const inputElement = document.getElementById('sales-file-upload-form').querySelector('#file-input');
    percentElement.textContent = '+';
    percentElement.style.fontSize = '36px';
    inputElement.disabled = false;
}

window.addEventListener('load', function() {
    const sales_file_form = document.getElementById('sales-file-upload-form');
    fetch('sales-file-processing-progress/')
        .then(response => response.json())
        .then(data => {
            if (data.sales_file_processing_active) {
                trackSalesFileProcessingProgress();
            }
        });
    sales_file_form.querySelector('#file-input').addEventListener('change', function(e) {
        if (this.files.length > 0) {
            fetch(sales_file_form.action, {method: 'POST', body: new FormData(sales_file_form)})
            .then(response => response.json())
            .then(data => { 
                if (data.status === 'success') {
                    window.location.href = data.redirect_url;
                    clearSalesFileProcessingProgress();
                }
            });
            setTimeout(() => {
                trackSalesFileProcessingProgress();
            }, 1000);
        }
    });
});
