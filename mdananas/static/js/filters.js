window.addEventListener('load', function() {
    this.document.getElementById('category-filter').addEventListener('change', function() {
        this.form.submit();
    });
    this.document.getElementById('groupname-filter').addEventListener('change', function() {
        this.form.submit();
    });
    this.document.getElementById('xcode-filter').addEventListener('change', function() {
        this.form.submit();
    });
});
