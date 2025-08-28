import flet as ft
from pages.tovari import tovari_page
from pages.accounts import accounts_page

def home(page: ft.Page):
    # Функция для отображения sidebar с сообщением
    def show_beta_message(e):
        page.snack_bar = ft.SnackBar(
            content=ft.Text("Эта функция недоступна в бета-режиме.", size=20),
            action="OK",
            action_color=ft.colors.WHITE,
            bgcolor=ft.colors.RED_700,
            duration=3000
        )
        page.snack_bar.open = True
        page.update()

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        # Кнопка "Товары"
                        ft.OutlinedButton(
                            content=ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(name=ft.icons.SHOPPING_BASKET_OUTLINED, size=50),
                                        ft.Text(value="Товары", size=50),
                                    ],
                                    alignment=ft.MainAxisAlignment.START,
                                    spacing=10,
                                ),
                                padding=ft.padding.all(20),
                                width=400,  # Фиксированная ширина для всех кнопок
                                on_click=tovari_page
                            ),
                        ),
                        # Кнопка "Учетные записи"
                        ft.OutlinedButton(
                            content=ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(name=ft.icons.PEOPLE_OUTLINE, size=50),
                                        ft.Text(value="Уч. записи", size=50),
                                    ],
                                    alignment=ft.MainAxisAlignment.START,
                                    spacing=10,
                                ),
                                padding=ft.padding.all(20),
                                width=400,
                                on_click=lambda e: accounts_page(page)  # Изменение здесь
                            ),
                        ),
                        # Кнопка "Настройки"
                        ft.OutlinedButton(
                            content=ft.Container(
                                content=ft.Row(
                                    [
                                        ft.Icon(name=ft.icons.SETTINGS_OUTLINED, size=50),
                                        ft.Text(value="Настройки", size=50),
                                    ],
                                    alignment=ft.MainAxisAlignment.START,
                                    spacing=10,
                                ),
                                padding=ft.padding.all(20),
                                width=400,  # Фиксированная ширина для всех кнопок
                                on_click=show_beta_message
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,  # Центровка кнопок внутри колонки
                    spacing=20,  # Расстояние между кнопками
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,  # Центровка колонки внутри строки
        ),
        alignment=ft.alignment.center,  # Центровка всего контейнера на странице
        expand=True,  # Растянуть контейнер на весь экран
    )