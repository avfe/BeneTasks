import streamlit as st
import requests

API_URL = "backend:8000"  # URL вашего FastAPI-приложения

# Инициализация session_state для хранения токена, имени пользователя и текущей «страницы»
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "menu" not in st.session_state:
    st.session_state.menu = "Login"  # Стартовая «страница»

# -----------------------------
# Функции для работы с API
# -----------------------------
def login(username, password):
    data = {"username": username, "password": password}
    response = requests.post(f"{API_URL}/token", data=data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        st.session_state.token = token
        st.session_state.username = username
        st.success("Вход выполнен успешно!")
        # Переходим на страницу "Задачи"
        st.session_state.menu = "Задачи"
    else:
        st.error("Ошибка входа: " + response.json().get("detail", "Неизвестная ошибка"))

def register(username, password):
    json_data = {"username": username, "password": password}
    response = requests.post(f"{API_URL}/register", json=json_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        st.session_state.token = token
        st.session_state.username = username
        st.success("Регистрация прошла успешно!")
    else:
        st.error("Ошибка регистрации: " + response.json().get("detail", "Неизвестная ошибка"))

def get_tasks(sort_by=None, order="asc", search=None):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    params = {}
    if sort_by:
        params["sort_by"] = sort_by
        params["order"] = order
    if search:
        params["search"] = search
    response = requests.get(f"{API_URL}/tasks", headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Ошибка получения задач: " + response.text)
        return []

def create_task(title, description, status, priority):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    json_data = {
        "title": title,
        "description": description,
        "status": status,
        "priority": priority
    }
    response = requests.post(f"{API_URL}/tasks", headers=headers, json=json_data)
    if response.status_code == 200:
        st.success("Задача создана!")
    else:
        st.error("Ошибка создания задачи: " + response.text)

def update_task(task_id, title, description, status, priority):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    json_data = {
        "title": title,
        "description": description,
        "status": status,
        "priority": priority
    }
    response = requests.put(f"{API_URL}/tasks/{task_id}", headers=headers, json=json_data)
    if response.status_code == 200:
        st.success("Задача обновлена!")
    else:
        st.error("Ошибка обновления задачи: " + response.text)

def delete_task(task_id):
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    response = requests.delete(f"{API_URL}/tasks/{task_id}", headers=headers)
    if response.status_code == 200:
        st.success("Задача удалена!")
    else:
        st.error("Ошибка удаления задачи: " + response.text)

def get_top_tasks(n=5, priority=None, all_priorities=False):
    """
    Вызываем эндпоинт /tasks/top/ с нужными query-параметрами:
    - n (сколько задач вывести)
    - priority (если нужен конкретный приоритет)
    - all_priorities (если True, выводим все приоритеты в порядке возрастания)
    """
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    params = {"n": n}

    if all_priorities:
        # Если галочка "Все приоритеты" включена
        params["all_priorities"] = "true"
    elif priority is not None:
        # Если приоритет выбран
        params["priority"] = priority

    # Важно: в серверном коде маршрут /tasks/top/ (со слэшем в конце)
    response = requests.get(f"{API_URL}/tasks/top/", headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Ошибка получения ТОП задач: " + response.text)
        return []

# -----------------------------
# Боковое меню (кнопки)
# -----------------------------
st.sidebar.title("Меню")

if st.sidebar.button("Логин"):
    st.session_state.menu = "Login"

if st.sidebar.button("Регистрация"):
    st.session_state.menu = "Register"

if st.sidebar.button("Задачи"):
    st.session_state.menu = "Задачи"

if st.sidebar.button("Создать задачу"):
    st.session_state.menu = "Создать задачу"

if st.sidebar.button("Топ задач"):
    st.session_state.menu = "TopTasks"

# -----------------------------
# Основной контент
# -----------------------------
st.title("BeneTasks")

if st.session_state.menu == "Login":
    st.header("Вход")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Войти")
        if submitted:
            login(username, password)

elif st.session_state.menu == "Register":
    st.header("Регистрация")
    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Зарегистрироваться")
        if submitted:
            register(username, password)

elif st.session_state.menu == "Задачи":
    st.header("Ваши задачи")
    if st.session_state.token is None:
        st.warning("Сначала необходимо выполнить вход!")
    else:
        col1, col2 = st.columns(2)
        with col1:
            sort_by = st.selectbox("Сортировать по", ["", "title", "status", "created_at", "priority"])
        with col2:
            order = st.selectbox("Порядок", ["asc", "desc"])
        search = st.text_input("Поиск по тексту")

        tasks = get_tasks(
            sort_by if sort_by != "" else None,
            order,
            search if search != "" else None
        )
        if tasks:
            for task in tasks:
                st.write("Заголовок:", task["title"])
                st.write("Описание:", task["description"])
                st.write("Статус:", task["status"])
                st.write("Приоритет:", task["priority"])
                st.write("Создана:", task["created_at"])

                col_del, col_upd = st.columns([1, 2])
                with col_del:
                    if st.button("Удалить", key=f"delete_{task['id']}"):
                        delete_task(task["id"])
                        st.info("Обновите страницу или нажмите «Задачи» заново, чтобы увидеть изменения.")
                with col_upd:
                    with st.expander("Редактировать"):
                        with st.form(f"update_form_{task['id']}"):
                            new_title = st.text_input("Заголовок", value=task["title"])
                            new_description = st.text_area("Описание", value=task["description"])
                            possible_statuses = ["в ожидании", "в работе", "завершено"]
                            status_index = possible_statuses.index(task["status"]) if task["status"] in possible_statuses else 0
                            new_status = st.selectbox("Статус", possible_statuses, index=status_index)
                            new_priority = st.number_input("Приоритет", value=task["priority"], step=1)
                            submitted_update = st.form_submit_button("Обновить")
                        if submitted_update:
                            update_task(task["id"], new_title, new_description, new_status, new_priority)
                            st.info("Обновите страницу или нажмите «Задачи» заново, чтобы увидеть изменения.")
                st.write("---")
        else:
            st.info("Задачи не найдены.")

elif st.session_state.menu == "Создать задачу":
    st.header("Создать новую задачу")
    if st.session_state.token is None:
        st.warning("Сначала необходимо выполнить вход!")
    else:
        with st.form("create_task_form"):
            title = st.text_input("Заголовок")
            description = st.text_area("Описание")
            status = st.selectbox("Статус", ["в ожидании", "в работе", "завершено"])
            priority = st.number_input("Приоритет", min_value=0, step=1)
            submitted = st.form_submit_button("Создать задачу")
            if submitted:
                create_task(title, description, status, priority)

elif st.session_state.menu == "TopTasks":
    st.header("ТОП задач по приоритету")
    if st.session_state.token is None:
        st.warning("Сначала необходимо выполнить вход!")
    else:
        n_value = st.number_input("Сколько задач вывести?", min_value=1, value=5, step=1)
        all_prio = st.checkbox("Все приоритеты", value=False)
        if not all_prio:
            # Если галочка не включена, позволяем выбрать конкретный приоритет
            selected_prio = st.number_input("Выберите приоритет", min_value=0, value=1, step=1)
        else:
            selected_prio = None

        if st.button("Показать ТОП"):
            tasks = get_top_tasks(n=n_value, priority=selected_prio, all_priorities=all_prio)
            if tasks:
                st.write(f"Показаны задачи (n={n_value}). Приоритет: {'все' if all_prio else selected_prio}")
                for task in tasks:
                    st.write("Заголовок:", task["title"])
                    st.write("Описание:", task["description"])
                    st.write("Статус:", task["status"])
                    st.write("Приоритет:", task["priority"])
                    st.write("Создана:", task["created_at"])
                    st.write("---")
            else:
                st.info("Нет задач для отображения или произошла ошибка.")
