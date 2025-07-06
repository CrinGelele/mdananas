function trackSalesFileProcessingProgress() {
    const percentElement = document.getElementById('sales-file-upload-form').querySelector('#progress-percent');
    const inputElement = document.getElementById('sales-file-upload-form').querySelector('#sales-file-input');
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

function trackCompetitorsFileProcessingProgress() {
    const percentElement = document.getElementById('competitors-file-upload-form').querySelector('#progress-percent');
    const inputElement = document.getElementById('competitors-file-upload-form').querySelector('#competitors-file-input');
    percentElement.textContent = '0%';
    percentElement.style.fontSize = '20px';
    inputElement.disabled = true;
    const progressInterval = setInterval(() => {
        fetch('sales-file-processing-progress/')
            .then(response => response.json())
            .then(data => {
                if (!data.competitors_file_processing_active) {
                    clearInterval(progressInterval);
                } else {
                    percentElement.textContent = data.competitors_file_processing_progress + '%';
                }
            });
    }, 500);
    return progressInterval
}

window.addEventListener('load', function() {
    const sales_file_form = document.getElementById('sales-file-upload-form');
    const competitors_file_form = document.getElementById('competitors-file-upload-form');
    fetch('sales-file-processing-progress/')
        .then(response => response.json())
        .then(data => {
            if (data.sales_file_processing_active) {
                trackSalesFileProcessingProgress();
            }
            if (data.competitors_file_processing_active) {
                trackCompetitorsFileProcessingProgress();
            }
        });
    sales_file_form.querySelector('#sales-file-input').addEventListener('change', function(e) {
        if (this.files.length > 0) {
            competitors_file_form.querySelector('#competitors-file-input').disabled = true;
            fetch(sales_file_form.action, {method: 'POST', body: new FormData(sales_file_form)})
            .then(response => response.json())
            .then(data => { 
                if (data.status === 'success') {
                    window.location.href = data.redirect_url;
                }
            });
            setTimeout(() => {
                trackSalesFileProcessingProgress();
            }, 1000);
        }
    });
    competitors_file_form.querySelector('#competitors-file-input').addEventListener('change', function(e) {
        if (this.files.length > 0) {
            sales_file_form.querySelector('#sales-file-input').disabled = true;
            fetch(competitors_file_form.action, {method: 'POST', body: new FormData(competitors_file_form)})
            .then(response => response.json())
            .then(data => { 
                if (data.status === 'success') {
                    window.location.href = data.redirect_url;
                }
            });
            setTimeout(() => {
                trackCompetitorsFileProcessingProgress();
            }, 1000);
        }
    });
});
