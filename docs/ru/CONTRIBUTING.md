# Участие в разработке powerful-claw

[English](../../CONTRIBUTING.md) | [简体中文](../zh/CONTRIBUTING.md) | **Русский** | [Français](../fr/CONTRIBUTING.md)

Спасибо за интерес к проекту! Это руководство описывает настройку окружения разработки, запуск тестов и отправку изменений.

---

## Требования

| Требование | Минимальная версия | Примечания |
|------------|--------------------|------------|
| Python | 3.13 | Проверено на Windows 10/11 |
| MinGW (gcc/g++) | 13.x | Только для нативного бэкенда C++ |
| Git | 2.40+ | Контроль версий |

---

## Настройка окружения разработки

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/chen-xin-Liam/powerful-claw.git
cd powerful-claw

# 2. Создайте и активируйте виртуальное окружение
python -m venv venv
venv\Scripts\activate          # Windows PowerShell

# 3. Установите зависимости
pip install -r requirements.txt
pip install pytest             # Запуск тестов
```

**Опционально — сборка нативного бэкенда C++** (нужна для бенчмарков):

```bash
python src/core/native/build_native.py
```

Создаётся `src/core/native/build/nodecalc_native.dll`. При отсутствии DLL бэкенд автоматически переключается на чистый Python.

---

## Запуск приложения

```bash
python src/main.py
```

При первом запуске создаются каталоги `config/` и `logs/`, открывается главное окно.

---

## Запуск тестов

### Быстрый smoke-тест (автономный запуск, без pytest)

```bash
python auto_tests/run_tests.py
```

### Полный набор тестов

```bash
pytest auto_tests/
```

Тесты охватывают:
- Движок выражений (все 44 типа узлов)
- Эквивалентность нативного и Python-бэкенда
- Регрессии производительности (сравнение с `benchmarks/results_native_compute.json`)
- Проверку доступности API
- Импорт конфигураций MCP

---

## Сборка исполняемого файла

```bash
python scripts/build_exe.py
```

Результат — в `dist/AIComputerControl/`. Сборка использует PyInstaller и spec-файл `AIComputerControl.spec`.

Пробный прогон (проверка состава без создания файлов):

```bash
python scripts/build_exe.py --dry-run
```

---

## Структура кода

```
src/
├── core/                  # Движок выражений (Python + нативный C++)
│   ├── node_engine.py     # 44 типа узлов
│   ├── expression_parser.py
│   └── native/            # Исходники C++, скрипт сборки, мост cffi
├── services/              # Фоновые сервисы (WebSocket, API, ИИ, MCP и др.)
├── ui/                    # Главное окно CustomTkinter + диалог настроек PySide6
├── config/                # Настройки, темы, конфигурации расширений
└── system/                # Работа с оборудованием, диалоги подтверждения

auto_tests/                # Набор автотестов (pytest)
benchmarks/                # JSON-базовые показатели производительности
docs/                      # Документация (en/zh/ru/fr)
scripts/                   # Скрипты сборки и обслуживания
```

---

## Соглашения по коду

- **Язык**: Python 3.13 (аннотации типов приветствуются)
- **UI**: CustomTkinter для главного окна, PySide6 для диалога настроек
- **Импорты**: тяжёлые сторонние модули (openai, PIL, pyautogui и т.д.) импортируйте лениво внутри функций, а не на верхнем уровне модуля. Это удерживает холодный старт в пределах 1 секунды.
- **Fallback бэкенда**: модули вычислений должны работать на чистом Python при отсутствии нативной DLL.
- **Комментарии**: пишите комментарии на китайском для единообразия с существующей кодовой базой.
- **Docstring**: модульные docstring обязательны; для публичных API — ещё и строки документирования функций.

---

## Добавление MCP-сервера

Используйте встроенный импортёр:

```python
from src.services.mcp_importer import add_from_template
add_from_template("github", env={"GITHUB_TOKEN": "your_token"})
```

Импорт из стандартного файла `.mcp.json`:

```python
from src.services.mcp_importer import import_mcp_config
report = import_mcp_config("path/to/mcp.json")
```

Доступные шаблоны: `filesystem`, `github`, `fetch`, `memory`, `sqlite`, `puppeteer`.

---

## Проверка доступности API

Перед коммитом изменений, затрагивающих код ИИ-провайдеров, проверьте связь:

```bash
python -m src.services.api_connectivity
```

Команда проверяет все настроенные провайдеры и выводит сводный отчёт.

---

## Отправка изменений

1. **Сделайте форк** репозитория и создайте ветку функции:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Внесите изменения** и добавьте тесты в `auto_tests/` при необходимости.

3. **Запустите полный набор тестов**:
   ```bash
   pytest auto_tests/
   ```

4. **Закоммитьте** с понятным сообщением в существующем стиле (краткий повелительный заголовок, при необходимости — тело):
   ```bash
   git commit -m "Add GPU temperature monitoring to system info"
   ```

5. **Отправьте изменения** и откройте Pull Request в ветку `main`.

---

## Сообщение об ошибках

Откройте issue на GitHub, указав:
- Чёткое описание проблемы
- Шаги воспроизведения
- Ожидаемое и фактическое поведение
- Данные окружения (ОС, версия Python)
- Релевантные логи из `logs/`

---

## Лицензия

Отправляя вклад, вы соглашаетесь с лицензированием ваших изменений под [GNU General Public License v3.0](../../LICENSE).
