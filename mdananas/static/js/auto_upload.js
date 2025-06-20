window.addEventListener('load', function() {
        document.getElementById('file-input').addEventListener('change', function(e) {
        if (this.files.length > 0) {
            document.getElementById('file-upload-form').submit();
        }
    });
});
