window.addEventListener('load', function() {
    document.getElementById('add_new_to_compositions_table').addEventListener('click', clickEvent = () => {
        document.getElementById('compositions_table_body').appendChild(Object.assign(document.createElement('tr'), {innerHTML: new_compositions_table_row}))
    })
});
