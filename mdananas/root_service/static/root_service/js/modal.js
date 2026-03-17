// Переменные для хранения выбранного ТУ
let selectedTUId = null;
let selectedTUName = '';
let selectedCard = null;

function openCreateModal() {
    document.getElementById('createModal').style.display = 'block';
    console.log(1);
}

function closeCreateModal() {
    document.getElementById('createModal').style.display = 'none';
}

function createNew() {
    window.location.href = '/root/tu/create/';
}

function openExistingModal() {
    closeCreateModal(); 
    document.getElementById('existingModal').style.display = 'block';
    // Сбрасываем выделение при открытии
    resetSelection();
}

// Закрытие модального окна с существующими ТУ
function closeExistingModal() {
    document.getElementById('existingModal').style.display = 'none';
    // Очищаем поиск при закрытии
    document.getElementById('searchExisting').value = '';
    // Сбрасываем выделение
    resetSelection();
    filterExistingTU();
}

// Сброс выделения
function resetSelection() {
    // Убираем класс selected со всех карточек
    document.querySelectorAll('.existing-item-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // Скрываем панель подтверждения
    const confirmationBar = document.getElementById('confirmationBar');
    if (confirmationBar) {
        confirmationBar.style.display = 'none';
    }
    
    // Сбрасываем переменные
    selectedTUId = null;
    selectedTUName = '';
    selectedCard = null;
}

// Выбор существующего ТУ (обновленная версия с галочкой)
function selectExistingTU(tuId) {
    // Находим текущую карточку
    const currentCard = document.querySelector(`.existing-item-card[data-id="${tuId}"]`);
    if (!currentCard) return;
    
    // Если кликнули по той же карточке - снимаем выделение
    if (selectedCard === currentCard) {
        currentCard.classList.remove('selected');
        selectedTUId = null;
        selectedTUName = '';
        selectedCard = null;
        
        // Скрываем панель подтверждения
        const confirmationBar = document.getElementById('confirmationBar');
        if (confirmationBar) {
            confirmationBar.style.display = 'none';
        }
        return;
    }
    
    // Убираем выделение с предыдущей карточки
    if (selectedCard) {
        selectedCard.classList.remove('selected');
    }
    
    // Выделяем новую карточку
    currentCard.classList.add('selected');
    
    // Получаем название ТУ
    const itemName = currentCard.querySelector('.item-name').textContent;
    
    // Сохраняем выбранное ТУ
    selectedTUId = tuId;
    selectedTUName = itemName;
    selectedCard = currentCard;
    
    // Показываем панель подтверждения
    showConfirmationBar(itemName);
}

// Показать панель подтверждения
function showConfirmationBar(tuName) {
    const confirmationBar = document.getElementById('confirmationBar');
    if (confirmationBar) {
        confirmationBar.style.display = 'flex';
        confirmationBar.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Подтверждение выбора
function confirmSelection() {
    if (selectedTUId) {
        window.location.href = "/root/tu/" + selectedTUId + "/copy/";
    } else {
        alert('Пожалуйста, выберите ТУ');
    }
}

// Отмена выбора
function cancelSelection() {
    resetSelection();
}

// Фильтрация списка ТУ (обновленная с сохранением выделения)
function filterExistingTU() {
    var searchText = document.getElementById('searchExisting').value.toLowerCase();
    var items = document.querySelectorAll('.existing-item-card');
    let visibleCount = 0;
    let selectedStillVisible = false;
    
    items.forEach(function(item) {
        var itemName = item.querySelector('.item-name').textContent.toLowerCase();
        var itemDesc = item.querySelector('.item-description') ? 
                      item.querySelector('.item-description').textContent.toLowerCase() : '';
        var itemCode = item.querySelector('.item-code') ? 
                      item.querySelector('.item-code').textContent.toLowerCase() : '';
        
        const matches = itemName.includes(searchText) || 
                        itemDesc.includes(searchText) || 
                        itemCode.includes(searchText);
        
        item.style.display = matches ? 'flex' : 'none';
        
        if (matches) {
            visibleCount++;
            // Проверяем, виден ли выбранный элемент
            if (selectedCard === item) {
                selectedStillVisible = true;
            }
        }
    });
    
    // Если выбранный элемент стал невидимым из-за поиска, сбрасываем выделение
    if (selectedCard && !selectedStillVisible) {
        resetSelection();
    }
    
    // Обновляем счетчик, если он есть
    const countElement = document.getElementById('itemsCount');
    if (countElement) {
        countElement.textContent = `Найдено: ${visibleCount}`;
    }
}

// Закрытие модальных окон при клике вне их
window.onclick = function(event) {
    var createModal = document.getElementById('createModal');
    var existingModal = document.getElementById('existingModal');
    
    if (event.target == createModal) {
        createModal.style.display = 'none';
    }
    if (event.target == existingModal) {
        existingModal.style.display = 'none';
        document.getElementById('searchExisting').value = '';
        resetSelection(); // Сбрасываем выделение при клике вне
        filterExistingTU();
    }
}

// Закрытие по клавише Escape
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeCreateModal();
        closeExistingModal();
    }
});

// Добавляем обработчик для Enter
document.addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        const confirmationBar = document.getElementById('confirmationBar');
        if (confirmationBar && confirmationBar.style.display === 'flex') {
            confirmSelection();
        }
    }
});