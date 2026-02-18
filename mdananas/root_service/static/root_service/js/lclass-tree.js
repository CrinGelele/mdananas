// classification_tree.js - универсальная версия
(function() {
    'use strict';

    // Состояние выбранных узлов на каждом уровне
    let selectedNodes = {
        l1: null,
        l2: null,
        l3: null,
        l4: null,
        l5: null
    };

    // Функция для получения детей узла по пути
    function getChildren(data, path) {
        let current = data;
        for (const key of path) {
            if (current && current[key] && typeof current[key] === 'object') {
                current = current[key];
            } else {
                return null;
            }
        }
        return current;
    }

    // Функция для получения данных для конкретного уровня с учётом выбранного пути
    function getLevelData(data, currentPath, level) {
        if (level === 0) {
            // Для L1 возвращаем всё дерево ВСЕГДА
            return data;
        }
        
        // Для остальных уровней проверяем, выбран ли родитель
        if (currentPath && currentPath.length >= level) {
            const parentPath = currentPath.slice(0, level);
            const parent = getChildren(data, parentPath);
            if (parent && typeof parent === 'object' && !Number.isInteger(parent)) {
                return parent;
            }
        }
        
        // Если нет выбранного родителя, возвращаем null (уровень не показываем)
        return null;
    }

    // Функция для построения горизонтального дерева
    function renderHorizontalTree(container, data, selectedId = null, clickPath = null) {
        const levels = ['l1', 'l2', 'l3', 'l4', 'l5'];
        const levelNames = ['L1', 'L2', 'L3', 'L4', 'L5'];
        
        // Очищаем контейнер
        container.innerHTML = '';
        
        // Создаем контейнер для уровней
        const treeContainer = document.createElement('div');
        treeContainer.className = 'tree-container';
        
        // Определяем текущий путь
        let currentPath = [];
        
        if (clickPath) {
            // Если передан путь от клика, используем его
            currentPath = [...clickPath];
        } else if (selectedId) {
            // Иначе ищем путь по ID
            currentPath = findPathToId(data, selectedId) || [];
        }
        // Если нет selectedId и нет clickPath - currentPath остается пустым []
        // Это значит, что ничего не выбрано, показываем только L1
        
        // Обновляем selectedNodes из пути
        currentPath.forEach((key, index) => {
            if (index < levels.length) {
                selectedNodes[levels[index]] = key;
            }
        });
        
        // Строим каждый уровень
        for (let level = 0; level < levels.length; level++) {
            const levelDiv = document.createElement('div');
            levelDiv.className = 'tree-level';
            levelDiv.dataset.level = levels[level];
            
            // Заголовок уровня
            const header = document.createElement('div');
            header.className = 'tree-level-header';
            header.textContent = levelNames[level];
            levelDiv.appendChild(header);
            
            // Получаем данные для этого уровня с учётом текущего пути
            const levelData = getLevelData(data, currentPath, level);
            
            // Добавляем узлы уровня
            if (levelData && typeof levelData === 'object' && !Number.isInteger(levelData)) {
                // Сортируем ключи для консистентности
                const sortedKeys = Object.keys(levelData).sort();
                
                for (const key of sortedKeys) {
                    const value = levelData[key];
                    const nodeDiv = document.createElement('div');
                    nodeDiv.className = 'tree-node';
                    
                    const isLeaf = Number.isInteger(value);
                    const nodeId = isLeaf ? value : null;
                    
                    // Проверяем, выбран ли этот узел
                    const isSelected = currentPath[level] === key;
                    if (isSelected) {
                        nodeDiv.classList.add('selected');
                    }
                    
                    const labelSpan = document.createElement('span');
                    labelSpan.className = 'tree-node-label';
                    labelSpan.dataset.id = nodeId;
                    labelSpan.dataset.level = levels[level];
                    labelSpan.dataset.key = key;
                    labelSpan.dataset.isLeaf = isLeaf;
                    
                    // Бейдж
                    const badge = document.createElement('span');
                    badge.className = 'level-badge';
                    badge.textContent = levels[level].toUpperCase();
                    
                    labelSpan.appendChild(badge);
                    labelSpan.appendChild(document.createTextNode(key));
                    
                    // Если есть дети, добавляем индикатор
                    if (!isLeaf && value && typeof value === 'object' && Object.keys(value).length > 0) {
                        const arrow = document.createElement('span');
                        arrow.className = 'expand-indicator';
                        arrow.textContent = ' →';
                        arrow.style.marginLeft = 'auto';
                        arrow.style.fontSize = '12px';
                        arrow.style.color = '#999';
                        labelSpan.appendChild(arrow);
                    }
                    
                    // Обработчик клика
                    labelSpan.onclick = function(e) {
                        e.stopPropagation();
                        
                        const level = this.dataset.level;
                        const key = this.dataset.key;
                        const isLeaf = this.dataset.isLeaf === 'true';
                        const nodeId = this.dataset.id;
                        
                        // Находим индекс уровня
                        const levelIndex = levels.indexOf(level);
                        
                        // Создаём новый путь
                        let newPath = [];
                        
                        // Копируем существующий путь до текущего уровня
                        if (currentPath.length > 0) {
                            newPath = currentPath.slice(0, levelIndex);
                        }
                        
                        // Добавляем выбранный ключ
                        newPath[levelIndex] = key;
                        
                        // Если это не лист, очищаем последующие уровни в selectedNodes
                        if (!isLeaf) {
                            for (let i = levelIndex + 1; i < levels.length; i++) {
                                selectedNodes[levels[i]] = null;
                            }
                        }
                        
                        // Если это лист (L5) - отправляем на сервер
                        if (isLeaf && nodeId) {
                            saveSelection(nodeId, key, newPath);
                        } 
                        // Если это не лист - просто показываем следующий уровень
                        else {
                            showNotification(`Выбран уровень ${level.toUpperCase()}: ${key}`, 'info');
                        }
                        
                        // Перестраиваем дерево с новым путём
                        renderHorizontalTree(container, data, nodeId, newPath);
                    };
                    
                    nodeDiv.appendChild(labelSpan);
                    levelDiv.appendChild(nodeDiv);
                }
            } else {
                // Проверяем, нужно ли показывать пустой уровень
                let showEmpty = false;
                
                if (level === 0) {
                    // L1 показываем ВСЕГДА, даже если нет данных? 
                    // Но если нет данных для L1, это ошибка, но покажем сообщение
                    showEmpty = true;
                } else if (currentPath.length > level - 1 && currentPath[level - 1]) {
                    // Показываем пустой уровень только если предыдущий уровень выбран
                    showEmpty = true;
                }
                
                if (showEmpty) {
                    const emptyDiv = document.createElement('div');
                    emptyDiv.className = 'tree-node empty';
                    
                    if (level === 0 && !levelData) {
                        emptyDiv.textContent = 'Нет данных классификации';
                    } else {
                        emptyDiv.textContent = '—';
                    }
                    
                    emptyDiv.style.padding = '8px';
                    emptyDiv.style.color = '#999';
                    emptyDiv.style.textAlign = 'center';
                    levelDiv.appendChild(emptyDiv);
                }
            }
            
            treeContainer.appendChild(levelDiv);
            
            // Если на текущем уровне ничего не выбрано и это не L1, не показываем следующие уровни
            if (level > 0 && (!currentPath[level - 1] || currentPath.length < level)) {
                break;
            }
        }
        
        container.appendChild(treeContainer);
        
        // Скроллим к выбранному элементу (если есть)
        setTimeout(() => {
            const selected = container.querySelector('.tree-node.selected');
            if (selected) {
                selected.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest',
                    inline: 'center'
                });
            }
        }, 100);
    }

    // Функция для поиска пути к ID в дереве
    function findPathToId(data, targetId, currentPath = []) {
        for (const [key, value] of Object.entries(data)) {
            if (Number.isInteger(value) && value === targetId) {
                return [...currentPath, key];
            }
            if (value && typeof value === 'object' && !Number.isInteger(value)) {
                const result = findPathToId(value, targetId, [...currentPath, key]);
                if (result) {
                    return result;
                }
            }
        }
        return null;
    }

    // Функция для сохранения выбора
    function saveSelection(classificationId, nodeName, path) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        showNotification(`Сохранение: ${nodeName}...`, 'info', 1000);
        
        // Используем относительный URL
        fetch('set-classification/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                classification_id: classificationId
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            console.log('Classification updated successfully');
            
            // Формируем полный путь для отображения
            const fullPath = path ? path.join(' / ') : nodeName;
            
            // Обновляем старую форму, если она есть
            updateLegacyForm(path);
            
            showNotification(`✓ Сохранено: ${fullPath}`, 'success');
            
            // Отправляем событие
            document.dispatchEvent(new CustomEvent('classificationChanged', {
                detail: {
                    id: classificationId,
                    name: nodeName,
                    path: path,
                    fullPath: fullPath
                }
            }));
        })
        .catch(error => {
            console.error('Error updating classification:', error);
            showNotification('✗ Ошибка при сохранении', 'error');
        });
    }

    // Функция для обновления старой формы
    function updateLegacyForm(path) {
        if (!path) return;
        
        const levelMap = {
            0: 'l1_class',
            1: 'l2_class', 
            2: 'l3_class',
            3: 'l4_class',
            4: 'l5_class'
        };
        
        path.forEach((value, index) => {
            const input = document.querySelector(`input[name="${levelMap[index]}"]`);
            if (input) {
                input.value = value || '';
            }
        });
    }

    // Функция для показа уведомлений
    function showNotification(message, type = 'success', duration = 3000) {
        // Удаляем старые уведомления
        const oldNotifications = document.querySelectorAll('.tree-notification');
        oldNotifications.forEach(n => n.remove());
        
        const notification = document.createElement('div');
        notification.className = 'tree-notification';
        notification.textContent = message;
        
        const colors = {
            success: '#4caf50',
            error: '#f44336',
            info: '#2196f3',
            warning: '#ff9800'
        };
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 10px 20px;
            background: ${colors[type] || colors.info};
            color: white;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 9999;
            font-size: 13px;
            animation: slideIn 0.3s ease;
            max-width: 300px;
            word-wrap: break-word;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, duration);
    }

    // Добавляем стили для уведомлений и анимаций
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .expand-indicator {
            opacity: 0.5;
            transition: opacity 0.2s;
        }
        
        .tree-node-label:hover .expand-indicator {
            opacity: 1;
            color: #2196f3;
        }
        
        .tree-node.empty {
            cursor: default;
        }
        
        .tree-notification {
            font-family: system-ui, sans-serif;
        }
    `;
    document.head.appendChild(style);

    // Инициализация при загрузке страницы
    document.addEventListener('DOMContentLoaded', function() {
        const container = document.getElementById('classificationTree');
        
        if (container && window.TREE_DATA) {
            container.classList.add('loading');
            
            setTimeout(() => {
                renderHorizontalTree(
                    container, 
                    window.TREE_DATA, 
                    window.CURRENT_SELECTION_ID,  // может быть null
                    null
                );
                container.classList.remove('loading');
            }, 100);
        }
    });

})();