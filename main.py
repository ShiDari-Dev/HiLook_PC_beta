import flet as ft
from plugins.theme_manager import create_theme_button
from pages.home_page import home
import requests
import multiprocessing
import os
import json
import sys
import time
import atexit

# Получаем путь к текущей директории, где находится этот скрипт
current_dir = os.path.dirname(os.path.abspath(__file__))
# Формируем путь к папке /backend
backend_dir = os.path.join(current_dir, "backend")

# Формируем путь к файлу /backend/db.json
config_path = os.path.join(backend_dir, "db.json")

API_URL = "http://127.0.0.1:8000/"  # URL к бэкенду

# Глобальная переменная для хранения процесса сервера
server_process = None

# Глобальная переменная для отслеживания текущей страницы
current_page = "home"

# Глобальная переменная для отслеживания, запущен ли сервер
server_started = False

navigation_stack = ["home"]

def run_server():
    """Функция, которая будет запускать сервер в отдельном процессе."""
    os.chdir(backend_dir)
    os.system(f"{sys.executable} server.py")

def start_server():
    global server_process, server_started

    # Если сервер уже запущен, не запускаем его снова
    if server_started:
        print("Сервер уже запущен.")
        return server_process

    try:
        # Создаем новый процесс для запуска сервера
        server_process = multiprocessing.Process(target=run_server)
        server_process.start()

        # Устанавливаем флаг, что сервер запущен
        server_started = True
        print("Сервер успешно запущен.")

    except Exception as e:
        print(f"Ошибка при запуске сервера: {e}")
    return server_process

def stop_server():
    global server_process, server_started

    if server_process:
        server_process.terminate()
        server_process.join()  # Дождитесь завершения процесса
        server_process = None
        server_started = False  # Сбрасываем флаг
        print("Сервер остановлен.")

def wait_for_server():
    """Улучшенное ожидание запуска сервера"""
    max_attempts = 10
    for _ in range(max_attempts):
        try:
            response = requests.get(f"{API_URL}/docs", timeout=20)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            time.sleep(1)
    raise Exception("Сервер не запустился")

# Регистрируем остановку сервера при завершении программы
atexit.register(stop_server)

def login(page: ft.Page):
    global current_page
    current_page = "login"
    page.title = "Login"

    def ent_click_1(e):
        user_pass.current.focus()
        page.update()

    def ent_click_2(e):
        btn_login.current.on_click(e)
        page.update()

    # Функция валидации полей
    def validate(e):
        btn_login.current.disabled = not (user_login.current.value and user_pass.current.value)
        page.update()

    # Функция входа (логика авторизации)
    def login(e):
        # Проверяем, заполнены ли поля
        if not user_login.current.value or not user_pass.current.value:
            page.open(
                ft.SnackBar(
                    content=ft.Text("Пожалуйста, введите логин и пароль."),
                    bgcolor="red"
                )
            )
            return

        # Проверка на вход с логином и паролем "admin"
        if user_login.current.value == "admin" and user_pass.current.value == "admin":
            page.open(
                ft.SnackBar(
                    content=ft.Text("Успешный вход как администратор!"),
                    bgcolor="green"
                )
            )
            mechanic(page)  # Перенаправление после успешного входа
            return

        # Отправка данных для авторизации через API
        try:
            response = requests.post(f"{API_URL}/login", data={
                "username": user_login.current.value,
                "password": user_pass.current.value
            })
            if response.status_code == 200:
                # Успешная авторизация
                page.open(
                    ft.SnackBar(
                        content=ft.Text("Успешный вход!"),
                        bgcolor="green"
                    )
                )
                mechanic(page)  # Перенаправление после успешного входа
            else:
                # Ошибка авторизации
                page.open(
                    ft.SnackBar(
                        content=ft.Text("Ошибка: Неправильный логин или пароль."),
                        bgcolor="red"
                    )
                )
        except requests.exceptions.RequestException as ex:
            # Обработка ошибок сети
            page.open(
                ft.SnackBar(
                    content=ft.Text(f"Ошибка подключения: {ex}"),
                    bgcolor="red"
                )
            )

    # Функция для выбора файла
    def pick_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file = e.files[0].path
            # Указываем путь к папке C:\serverShiDari
            save_dir = r"C:\serverShiDari"
            # Проверяем, существует ли папка, и создаем ее, если нет
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            # Формируем путь к файлу JSON
            config_path = os.path.join(save_dir, "db.json")
            # Сохраняем путь к файлу в JSON
            with open(config_path, "w") as f:
                json.dump({"db_file_path": selected_file}, f)
            # Обновляем текстовое поле с текущим выбранным файлом
            current_db_file.current.value = selected_file
            page.open(
                ft.SnackBar(
                    content=ft.Text(f"Выбран файл: {selected_file}. Перезапуск сервера..."),
                    bgcolor="green"
                )
            )
            page.update()
            # Перезапуск сервера
            stop_server()  # Останавливаем сервер перед перезапуском
            start_server()
            wait_for_server()
            page.open(
                ft.SnackBar(
                    content=ft.Text("Сервер перезапущен."),
                    bgcolor="green"
                )
            )
            page.update()

    # Инициализация FilePicker
    file_picker = ft.FilePicker(on_result=pick_file_result)
    page.overlay.append(file_picker)

    user_login = ft.Ref[ft.TextField]()
    user_pass = ft.Ref[ft.TextField]()
    btn_login = ft.Ref[ft.OutlinedButton]()
    current_db_file = ft.Ref[ft.TextField]()

    # Проверяем, существует ли JSON-файл и содержит ли он путь к файлу базы данных
    db_file_path = "Файл не выбран"
    save_dir = r"C:\serverShiDari"
    config_path = os.path.join(save_dir, "db.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                if "db_file_path" in config_data and config_data["db_file_path"]:
                    db_file_path = config_data["db_file_path"]
        except Exception as e:
            print(f"Ошибка при чтении файла конфигурации: {e}")

    # Создаем кнопку и сразу блокируем её
    btn_login_control = ft.OutlinedButton(
        text="Запуск... Ожидайте",
        width=300,
        on_click=login,  # Синхронный обработчик
        disabled=True,
        ref=btn_login
    )

    # Добавляем элементы на страницу
    page.add(
        ft.Container(
            content=ft.Column(
                [
                    ft.Text("Авторизация", size=24),
                    ft.TextField(label="Логин", width=250, on_change=validate, on_submit=ent_click_1, ref=user_login),
                    ft.TextField(label="Пароль", width=250, password=True, on_change=validate, on_submit=ent_click_2,
                                 ref=user_pass),
                    btn_login_control,  # Используем созданную кнопку
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            alignment=ft.alignment.center,
            expand=True,
        ),
        ft.Row(
            [
                ft.Text("Файл ДБ:"),
                ft.TextField(
                    width=300,
                    read_only=True,
                    ref=current_db_file,
                    value=db_file_path,  # Устанавливаем значение из JSON или "Файл не выбран"
                ),
                ft.ElevatedButton(
                    "Выбрать файл",
                    on_click=lambda _: file_picker.pick_files(
                        allowed_extensions=["db"],
                        allow_multiple=False
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )

    # Запуск сервера при старте приложения
    if not server_started:
        start_server()
        wait_for_server()

    # После успешного запуска сервера проверяем, заполнены ли поля, и только затем разблокируем кнопку
    if user_login.current.value and user_pass.current.value:
        btn_login.current.disabled = False
    btn_login.current.text = "Войти"
    page.update()

def mechanic(page: ft.Page):
    global current_page
    current_page = "mechanic"
    # Загружаем тему из файла
    theme_settings_path = r"C:\serverShiDari\theme_settings.json"
    if os.path.exists(theme_settings_path):
        try:
            with open(theme_settings_path, "r") as f:
                theme_data = json.load(f)
                page.theme_mode = theme_data.get("theme", "dark")  # По умолчанию "dark"
        except Exception as e:
            print(f"Ошибка при чтении файла темы: {e}")
            page.theme_mode = "dark"  # Если произошла ошибка, используем тему по умолчанию
    else:
        page.theme_mode = "dark"  # Если файла нет, используем тему по умолчанию

    # Функция для обработки нажатия на кнопку "Назад"
    def go_back(e):
        if current_page != "home":
            page.clean()
            page.add(home(page))
            page.update()

    # Создаем объект AppBar с кнопкой "Назад"
    appbar = ft.AppBar(
        title=ft.Row(
            controls=[ft.Text("ShiDari Informator")],
            expand=True,
            alignment=ft.MainAxisAlignment.START,
        ),
        actions=[
            ft.IconButton(ft.icons.HOME, on_click=go_back) if current_page != "home" else None,
            create_theme_button(page)
        ],
        bgcolor=ft.colors.BLUE_500,
        toolbar_height=80
    )
    # Назначаем AppBar для страницы
    page.appbar = appbar

    # Добавляем контент на страницу
    page.clean()
    page.add(home(page))
    page.update()

def main(page: ft.Page):
    login(page)

if __name__ == '__main__':
    # Добавляем freeze_support() для совместимости с Windows
    multiprocessing.freeze_support()
    
    # Запуск приложения Flet
    ft.app(target=main)