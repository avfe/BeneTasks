# BeneTasks

**BeneTasks** — это простое веб-приложение для управления задачами. Состоит из backend-а на **FastAPI** и frontend-а на **Streamlit**. Пользователи могут регистрироваться, входить в систему и управлять своими задачами: создавать, просматривать, редактировать и удалять.

Каждая задача содержит:
- заголовок
- описание
- статус ("в ожидании", "в работе", "завершено")
- дату создания
- приоритет (целое число)

---

## Возможности

- ✅ Регистрация и вход с использованием JWT-токенов
- ✅ Создание, просмотр, редактирование и удаление задач
- ✅ Сортировка задач по заголовку, статусу, дате или приоритету
- ✅ Поиск задач по подстроке в заголовке или описании
- ✅ Получение **топ-N задач по приоритету**
  - возможность указать конкретный приоритет
  - возможность показать задачи по всем приоритетам по возрастанию
- ✅ Кэширование запросов (на уровне памяти)

---

## Технологии

- **Backend**: FastAPI, SQLAlchemy, SQLite, JWT, Uvicorn
- **Frontend**: Streamlit, requests

---

## Установка и запуск

### 🔧 Зависимости

Убедитесь, что установлен Python 3.8+

Создайте виртуальное окружение и активируйте его:
```bash
python -m venv venv
source venv/bin/activate    # для Linux/Mac
venv\Scripts\activate       # для Windows
```

Установите зависимости:
```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
fastapi
uvicorn
sqlalchemy
passlib[bcrypt]
PyJWT
streamlit
requests
```

---

### ▶️ Запуск приложения

#### 1. Backend (FastAPI)
```bash
uvicorn main:app --reload
```
Доступно по адресу: [http://127.0.0.1:8000](http://127.0.0.1:8000)

Документация API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

🛡️ При первом запуске автоматически создаётся пользователь **admin / admin**

#### 2. Frontend (Streamlit)
```bash
streamlit run streamlit_app.py
```
Откроется браузер с интерфейсом BeneTasks.

---

## Использование

### 🔐 Аутентификация
- **/register** — регистрация нового пользователя
- **/token** — получение JWT-токена

### ✅ Операции с задачами
- **GET /tasks** — список задач с возможностью сортировки и поиска
- **POST /tasks** — создать задачу
- **PUT /tasks/{id}** — обновить задачу
- **DELETE /tasks/{id}** — удалить задачу

### 📊 Топ-N задач
- **GET /tasks/top/** — топ N задач по приоритету
  - `n`: количество задач
  - `priority`: конкретный приоритет (опционально)
  - `all_priorities`: булев параметр — если `true`, задачи сортируются по приоритету от меньшего к большему

---

## Интерфейс Streamlit

Меню (слева):
- **Login** — вход
- **Register** — регистрация
- **Задачи** — просмотр, редактирование, удаление задач
- **Создать задачу** — форма создания новой задачи
- **ТОП задач** — выбор количества задач, приоритета или просмотр всех приоритетов

После входа вы автоматически переходите к списку задач.

---

## Структура проекта

```
├── main.py             # Backend FastAPI
├── streamlit_app.py    # Frontend Streamlit
├── requirements.txt    # Зависимости
└── README.md           # Документация
```

---

## Примечания

- Пользователь **admin** создаётся автоматически при запуске backend-сервера
- Для демонстрации кэширования используется in-memory cache
- Для продакшн-среды рекомендуется:
  - использовать PostgreSQL или другую СУБД
  - внедрить Redis для кэширования
  - подключить полноценную систему аутентификации (OAuth2)

---

## Авторы

- 🤖 Создано с использованием FastAPI + Streamlit
- 📌 Проектное название: **BeneTasks**
