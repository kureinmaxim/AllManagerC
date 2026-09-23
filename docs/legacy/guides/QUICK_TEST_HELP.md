# 🚀 Быстрый Старт Тестирования

## Команды для тестирования

### Рекомендуемый способ (универсальный скрипт)
```bash
# Быстрые тесты (5 секунд)
python3 tests/run_tests.py --mode quick

# Полные тесты (2-3 минуты)
python3 tests/run_tests.py --mode full

# Ручное тестирование GUI
python3 tests/run_tests.py --mode manual

# Только веб-сервер
python3 tests/run_tests.py --mode server

# Проверка окружения
python3 tests/run_tests.py --mode check

# Все тесты сразу
python3 tests/run_tests.py --all
```

## Что тестируется

### Быстрые тесты (5 секунд)
- ✅ Запуск сервера
- ✅ Главная страница
- ✅ Модуль YubiKey
- ✅ Файлы данных
- ✅ Шифрование

### Комплексные тесты (2-3 минуты)
- ✅ Все веб-страницы
- ✅ YubiKey аутентификация
- ✅ Экспорт/импорт данных
- ✅ Формы и загрузка файлов
- ✅ Безопасность и производительность
- ✅ Обработка ошибок

## Результаты

- **JSON файл**: `test_results_YYYYMMDD_HHMMSS.json`
- **Консольный вывод**: Цветные результаты в реальном времени
- **Код выхода**: 0 = успех, 1 = ошибка

## Требования

```bash
# Активация окружения
source venv/bin/activate

# Установка зависимостей
pip install requests
```

## Устранение проблем

### Сервер не запускается
```bash
# Очистка порта
lsof -ti:5050 | xargs kill -9
```

### Модули не найдены
```bash
# Переустановка зависимостей
pip install --force-reinstall -r requirements.txt
```

### Подробная диагностика
```bash
python3 tests/run_tests.py --mode check
```

## Подробная документация

См. `TROUBLESHOOTING_SUMMARY.md` для итогового отчета по отладке и улучшениям. 