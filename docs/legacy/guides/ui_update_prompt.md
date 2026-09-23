### **Промпт для комплексного обновления интерфейса карточек сервисов**

**Цель:** Модифицировать три ключевых раздела в карточках сервисов (`templates/card_content.html` и `static/css/style.css`): "Ключевые особенности", "Дополнительная информация" и "Подписка", чтобы улучшить их внешний вид, читаемость и функциональность.

---

#### **Задача 1: Обновление раздела "Ключевые особенности"**

**Описание:** Необходимо изменить способ отображения ссылок. Вместо полного URL нужно показывать название функции и сокращенный домен ссылки в скобках (например, `Название функции (example.com...)`). Все элементы должны иметь одинаковый стиль, включая фон, отступы и обработку длинного текста.

**Действия:**

1.  **В файле `templates/card_content.html`:**
    *   Найдите цикл `{% for feature in features_list %}`.
    *   Внутри цикла добавьте логику для парсинга URL и текста из каждой "особенности".
    *   Создайте переменную `display_text`, которая будет содержать название и усеченный до 15 символов домен.
    *   Оберните каждый элемент в `div` с классом `feature-item`. Используйте CSS-переменную `--feature-bg` для установки фона из `server.gradient_color`.

    **Код для `templates/card_content.html` (секция "Ключевые особенности"):**
    ```html
    <div class="mb-3">
        <small class="text-muted">Ключевые особенности:</small>
        <div class="mt-1 d-flex flex-wrap gap-2">
            {% set features_list = server.features.split(',') if server.features is string else server.features %}
            {% for feature in features_list %}
                {% set feature_clean = feature.strip() %}
                {% set url_found = namespace(value=None) %}
                {% set text_parts = [] %}
                {% for part in feature_clean.split(' ') %}
                    {% if part.startswith('http://') or part.startswith('https://') %}
                        {% set url_found.value = part %}
                    {% else %}
                        {% do text_parts.append(part) %}
                    {% endif %}
                {% endfor %}
                {% set link_text = text_parts | join(' ') %}
                {% set display_text = link_text %}
                {% if url_found.value %}
                    {% set domain = url_found.value | regex_replace('^https?://', '') | replace('www.', '') | truncate(15, True, '…') %}
                    {% set display_text = display_text + ' (' + domain + ')' %}
                {% endif %}
                <div class="feature-item" style="--feature-bg: {{ server.gradient_color or '#667eea' }};">
                    {% if url_found.value %}
                        <a href="{{ url_found.value|e }}" target="_blank" title="{{ url_found.value|e }}">
                            {{ display_text }}
                        </a>
                    {% else %}
                        {{ feature_clean }}
                    {% endif %}
                </div>
            {% endfor %}
        </div>
    </div>
    ```

2.  **В файле `static/css/style.css`:**
    *   Добавьте новый класс `.feature-item` со стилями для фона (через `var(--feature-bg)`), цвета текста, отступов, скругления углов, размера шрифта и обработки переполнения (`white-space: nowrap`, `overflow: hidden`, `text-overflow: ellipsis`).
    *   Добавьте стиль для ссылок внутри `.feature-item`, чтобы они были белыми и без подчеркивания.

    **Код для `static/css/style.css`:**
    ```css
    .feature-item {
        background-color: var(--feature-bg, #6c757d);
        color: white;
        padding: 0.3em 0.6em;
        border-radius: 0.25rem;
        font-size: 0.9em;
        font-weight: 500;
        text-decoration: none;
        display: inline-block;
        max-width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        vertical-align: middle;
    }
    .feature-item a {
        color: white;
        text-decoration: none;
    }
    .feature-item:hover {
        text-decoration: underline;
    }
    ```

---

#### **Задача 2: Обновление раздела "Дополнительная информация"**

**Описание:** Сделать текст в этом блоке выделяемым и копируемым, но без автоматического преобразования в ссылки. Также необходимо убрать лишние отступы и уменьшить размер шрифта. Выделение текста должно работать только для активной (центральной) карточки в карусели.

**Действия:**

1.  **В файле `templates/card_content.html`:**
    *   Найдите блок "Дополнительная информация".
    *   Замените `div` или `p` для вывода текста на тег `<pre>` с классом `additional-info-content`.

    **Код для `templates/card_content.html` (секция "Дополнительная информация"):**
    ```html
    <div class="mb-3">
        <small class="text-muted">Дополнительная информация:</small>
        <pre class="additional-info-content mt-1">{% if server.credentials.additional_info_decrypted %}{{ server.credentials.additional_info_decrypted }}{% else %}<span class="text-muted">Нет дополнительной информации</span>{% endif %}</pre>
    </div>
    ```

2.  **В файле `static/css/style.css`:**
    *   Добавьте стили для `pre.additional-info-content`, чтобы убрать отступы, рамки, фон и уменьшить шрифт (`font-size: 0.85rem`).
    *   Установите `user-select: none;` по умолчанию, чтобы запретить выделение.
    *   Добавьте правило `.card-carousel-card.active pre.additional-info-content { user-select: text; }`, чтобы разрешить выделение только для активной карточки.

    **Код для `static/css/style.css`:**
    ```css
    pre.additional-info-content {
        margin: 0;
        padding: 0;
        border: none;
        background: transparent;
        font-family: inherit;
        font-size: 0.85rem;
        color: var(--bs-body-color);
        white-space: pre-wrap;
        word-wrap: break-word;
        user-select: none; /* Отключаем выделение для неактивных карточек */
    }
    .card-carousel-card.active pre.additional-info-content {
        user-select: text; /* Включаем выделение только для активной карточки */
    }
    ```

---

#### **Задача 3: Обновление раздела "Подписка"**

**Описание:** Уменьшить размер шрифта и межстрочные интервалы. Изменить стиль значков статуса автопродления. "Автопродление выключено" должно иметь желтоватый фон и рамку. "Автопродление включено" — аналогичный стиль, но в зеленых тонах.

**Действия:**

1.  **В файле `templates/card_content.html`:**
    *   Найдите `accordion-body` для подписки и добавьте ему класс `subscription-details`. Классы для значков (`bg-success`, `bg-warning`) остаются без изменений.

    **Код для `templates/card_content.html` (начало секции "Подписка"):**
    ```html
    <div id="collapse-subscription-{{ server.id }}" class="accordion-collapse collapse" data-bs-parent="#accordion-{{ server.id }}">
        <div class="accordion-body py-2 subscription-details">
            <!-- остальное содержимое подписки -->
    ```

2.  **В файле `static/css/style.css`:**
    *   Добавьте класс `.subscription-details` для уменьшения `font-size`.
    *   Уменьшите `margin-bottom` и `line-height` для тегов `p` внутри `.subscription-details`.
    *   Добавьте общие стили для `.subscription-details .badge` (скругление, отступы, рамка).
    *   Добавьте отдельные стили для `.badge.bg-warning` и `.badge.bg-success` внутри `.subscription-details`, используя `rgba()` для полупрозрачного фона и рамки, чтобы создать эффект свечения.

    **Код для `static/css/style.css`:**
    ```css
    .subscription-details {
        font-size: 0.9rem;
    }
    .subscription-details p {
        margin-bottom: 0.3rem;
        line-height: 1.3;
    }
    .subscription-details .badge {
        border-radius: 6px !important;
        padding: 0.3rem 0.6rem !important;
        font-weight: 500 !important;
        text-transform: none !important;
        border: 1px solid;
    }
    .subscription-details .badge.bg-warning { /* "Автопродление выключено" */
        background-color: rgba(255, 193, 7, 0.15) !important;
        color: #ffc107 !important;
        border-color: rgba(255, 193, 7, 0.4) !important;
    }
    .subscription-details .badge.bg-success { /* "Автопродление включено" */
        background-color: rgba(3, 166, 133, 0.15) !important;
        color: #03a685 !important;
        border-color: rgba(3, 166, 133, 0.4) !important;
    }
    ``` 