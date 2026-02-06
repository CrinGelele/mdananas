// Глобальные переменные
let selectedNode = null;
let selectedLevel = null;

// Данные дерева (можно заменить на данные из Django)
const treeData = [
    // Уровень 0
    [
        { id: 'L1_1', name: 'Naturally Good Food', level: 0 },
        { id: 'L1_2', name: 'Better Snacking', level: 0 },
        { id: 'L1_3', name: 'Others', level: 0 }
    ],
    // Уровень 1
    [
        { id: 'L2_1', name: 'Baby Toddler Food', level: 1, parentIndex: 0 },
        { id: 'L2_2', name: 'Early life Snacks', level: 1, parentIndex: 1 },
        { id: 'L2_3', name: 'Baby Toddler Milk', level: 1, parentIndex: 2 }
    ],
    // Уровень 2
    [
        { id: 'math', name: 'Математика', level: 2, parentIndex: 0 },
        { id: 'physics', name: 'Физика', level: 2, parentIndex: 0 },
        { id: 'history', name: 'История', level: 2, parentIndex: 1 },
        { id: 'philosophy', name: 'Философия', level: 2, parentIndex: 1 }
    ],
    // Уровень 3
    [
        { id: 'algebra', name: 'Алгебра', level: 3, parentIndex: 0 },
        { id: 'geometry', name: 'Геометрия', level: 3, parentIndex: 0 },
        { id: 'mechanics', name: 'Механика', level: 3, parentIndex: 1 },
        { id: 'thermodynamics', name: 'Термодинамика', level: 3, parentIndex: 1 },
        { id: 'russian_history', name: 'История России', level: 3, parentIndex: 2 },
        { id: 'world_history', name: 'Всемирная история', level: 3, parentIndex: 2 },
        { id: 'ancient_philosophy', name: 'Античная философия', level: 3, parentIndex: 3 },
        { id: 'modern_philosophy', name: 'Современная философия', level: 3, parentIndex: 3 }
    ]
];

// Инициализация дерева
function initTree() {
    const treeContainer = document.getElementById('tree');
    treeContainer.innerHTML = '';
    
    // Создаем каждый уровень
    treeData.forEach((levelNodes, levelIndex) => {
        // Контейнер уровня
        const levelDiv = document.createElement('div');
        levelDiv.className = 'level';
        
        // Добавляем узлы уровня
        levelNodes.forEach((node, nodeIndex) => {
            const nodeElement = createNodeElement(node, nodeIndex);
            levelDiv.appendChild(nodeElement);
        });
        
        treeContainer.appendChild(levelDiv);
        
        // Добавляем соединитель между уровнями (кроме последнего)
        if (levelIndex < treeData.length - 1) {
            const connector = document.createElement('div');
            connector.className = 'connector';
            treeContainer.appendChild(connector);
        }
    });
}

// Создание элемента узла
function createNodeElement(node, nodeIndex) {
    const div = document.createElement('div');
    div.className = 'node';
    div.dataset.id = node.id;
    div.dataset.level = node.level;
    div.dataset.index = nodeIndex;
    
    if (node.parentIndex !== undefined) {
        div.dataset.parentIndex = node.parentIndex;
    }
    
    // Добавляем классы для выделения
    if (selectedNode === node.id) {
        div.classList.add('selected');
    }
    
    // Проверяем, является ли узел родительским для выбранного
    if (selectedNode && isParentOfSelected(node, selectedNode)) {
        div.classList.add('parent');
    }
    
    div.innerHTML = `
        <div style="font-weight: bold;">${node.name}</div>
        <div style="font-size: 0.8em; opacity: 0.9;">Уровень ${node.level + 1}</div>
    `;
    
    div.onclick = (e) => {
        e.stopPropagation();
        selectNode(node.id, node.level, nodeIndex);
    };
    
    return div;
}

// Проверка, является ли узел родителем выбранного
function isParentOfSelected(node, selectedNodeId) {
    // Простая логика для демо - можно усложнить по необходимости
    const selectedNodeData = findNodeById(selectedNodeId);
    if (!selectedNodeData) return false;
    
    // Для уровней 1-3 проверяем родительский индекс
    if (selectedNodeData.level > 0 && selectedNodeData.parentIndex === node.dataset.index) {
        return true;
    }
    
    // Для корневого уровня
    if (selectedNodeData.level === 1 && node.level === 0) {
        return true;
    }
    
    return false;
}

// Поиск узла по ID
function findNodeById(nodeId) {
    for (const level of treeData) {
        for (const node of level) {
            if (node.id === nodeId) {
                return node;
            }
        }
    }
    return null;
}

// Выбор узла
function selectNode(nodeId, level, nodeIndex) {
    selectedNode = nodeId;
    selectedLevel = level;
    
    // Перерисовываем дерево
    initTree();
    
    // Показываем информацию
    showNodeInfo(nodeId, level);
    
    // Отправляем данные на сервер (если нужно)
    sendSelectionToServer(nodeId, level);
}

// Показать информацию о выбранном узле
function showNodeInfo(nodeId, level) {
    const node = findNodeById(nodeId);
    const infoDiv = document.getElementById('info');
    
    // Получаем путь от корня
    const path = getNodePath(nodeId);
    
    infoDiv.innerHTML = `
        <h3>✅ Выбрана классификация</h3>
        <p><strong>Узел:</strong> ${node.name}</p>
        <p><strong>Уровень:</strong> ${level + 1}</p>
        <p><strong>Полный путь:</strong></p>
        <div style="background: #e8f5e9; padding: 10px; border-radius: 5px; margin: 10px 0;">
            ${path.map(n => `<span style="color: #333;">${n.name}</span>`).join(' → ')}
        </div>
        <p>Вся иерархия выше этого узла будет привязана к объекту.</p>
        <button class="btn" onclick="saveSelection()">
            💾 Сохранить выбор
        </button>
        <button class="btn btn-reset" onclick="clearSelection()">
            ❌ Сбросить
        </button>
    `;
}

// Получить путь от корня до узла
function getNodePath(nodeId) {
    const path = [];
    let currentNode = findNodeById(nodeId);
    
    while (currentNode) {
        path.unshift(currentNode);
        
        // Находим родителя
        if (currentNode.level === 0) {
            break; // Достигли корня
        }
        
        // Для простоты - находим родителя по индексу
        if (currentNode.level > 0 && currentNode.parentIndex !== undefined) {
            const parentLevel = treeData[currentNode.level - 1];
            if (parentLevel && parentLevel[currentNode.parentIndex]) {
                currentNode = parentLevel[currentNode.parentIndex];
            } else {
                break;
            }
        } else {
            break;
        }
    }
    
    return path;
}

// Отправить выбор на сервер
function sendSelectionToServer(nodeId, level) {
    // Здесь можно сделать AJAX запрос к Django
    // fetch('/api/save-selection/', {
    //     method: 'POST',
    //     headers: {
    //         'Content-Type': 'application/json',
    //         'X-CSRFToken': getCSRFToken()
    //     },
    //     body: JSON.stringify({
    //         node_id: nodeId,
    //         level: level,
    //         path: getNodePath(nodeId).map(n => n.id)
    //     })
    // });
    
    // Для демо просто логируем
    console.log('Выбрано:', { nodeId, level, path: getNodePath(nodeId) });
}

// Сохранить выбор
function saveSelection() {
    if (!selectedNode) {
        alert('Сначала выберите узел в дереве!');
        return;
    }
    
    const node = findNodeById(selectedNode);
    const path = getNodePath(selectedNode);
    
    alert(`Классификация сохранена!\n\n${path.map(n => n.name).join(' → ')}`);
    
    // Здесь можно выполнить дополнительные действия
    // Например, отправить форму или перенаправить пользователя
}

// Очистить выбор
function clearSelection() {
    selectedNode = null;
    selectedLevel = null;
    initTree();
    
    document.getElementById('info').innerHTML = `
        <h3>📊 Древовидная классификация</h3>
        <p>Кликните на любой прямоугольник, чтобы выбрать его и всю иерархию выше</p>
        <p>При клике на узел 3-го уровня привязывается классификация до 3-го уровня, на 5-й уровень - вся иерархия</p>
    `;
}

// Получить CSRF токен (для AJAX запросов в Django)
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    initTree();
    clearSelection(); // Показываем начальное состояние
});