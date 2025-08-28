import flet as ft
import requests
import os
import uuid
from plugins.card_styles import create_card  # Импортируем универсальную карточку

class TovariPage:
    def __init__(self, page: ft.Page):
        self.page = page
        self.categories = []
        self.selected_category = None
        self.selected_unit_index = 0
        self.parameter_field = None
        self.add_button = None
        self.image_picker = ft.FilePicker()
        self.page.overlay.append(self.image_picker)
        self.IMAGES_DIR = r"C:\serverShiDari\Imgs"
        os.makedirs(self.IMAGES_DIR, exist_ok=True)
        self.category_list_view = ft.ListView(controls=[], expand=True)
        self.tovari_interface()

    def tovari_interface(self):
        self.page.clean()
        self.page.add(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.TextField(label="Поиск товаров", on_change=self.search_items, expand=True),
                            ft.ElevatedButton(
                                "Добавить категорию" if not self.selected_category else "Добавить товар",
                                on_click=self.show_add_dialog
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    self.category_list_view,  # Используем сохранённый ListView
                ],
                expand=True
            )
        )
        self.load_categories()

    def load_categories(self):
        # Добавляем анимацию загрузки
        progress_bar = ft.ProgressBar()
        self.page.add(progress_bar)
        self.page.update()

        try:
            response = requests.get("http://localhost:8000/categories")
            response.raise_for_status()
            self.categories = response.json()
            self.update_category_list()
        except requests.exceptions.RequestException as e:
            self.show_snackbar(f"Ошибка при загрузке категорий: {str(e)}")
        finally:
            # Убираем анимацию загрузки, если она есть
            if progress_bar in self.page.controls:
                self.page.controls.remove(progress_bar)
            self.page.update()
            
    def create_category_card(self, category):
        """Используем универсальную карточку для категорий"""
        return create_card(
            title=category['name'],
            subtitle=f"Параметр: {category['parameter'] or 'Не указан'}",
            description=f"Ед. измерения: {category['unit']}",
            on_click_handler=lambda e, cat=category: self.show_category_items(cat),
            description_color=ft.colors.BLUE_800
        )

    def update_category_list(self):
        """Обновление списка категорий на интерфейсе."""
        self.category_list_view.controls = [
            self.create_category_card(category) for category in self.categories
        ]
        self.page.update()

    def show_category_items(self, category):
        """Отображение товаров выбранной категории."""
        self.selected_category = category
        self.page.clean()
        self.page.add(
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.ElevatedButton("Назад", on_click=lambda e: self.tovari_interface()),
                            ft.TextField(label="Поиск товаров", on_change=self.search_items, expand=True),
                            ft.ElevatedButton("Добавить товар", on_click=lambda e: self.show_add_item_dialog(category))
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.ListView(controls=[], expand=True),
                ],
                expand=True
            )
        )
        self.load_category_items(category)

    def load_category_items(self, category):
        # Добавляем анимацию загрузки
        progress_bar = ft.ProgressBar()
        self.page.add(progress_bar)
        self.page.update()

        try:
            response = requests.get(f"http://localhost:8000/items?category_id={category['id']}")
            if response.status_code == 200:
                items = response.json()
                self.update_item_list(items)
        except Exception as e:
            self.show_snackbar(f"Ошибка при загрузке товаров: {str(e)}")
        finally:
            # Убираем анимацию загрузки, если она есть
            if progress_bar in self.page.controls:
                self.page.controls.remove(progress_bar)
            self.page.update()

    def update_item_list(self, items):
        item_list = self.page.controls[0].controls[1]
        item_list.controls = [
            self.create_item_card(item) for item in items
        ]
        self.page.update()

    def create_item_card(self, item):
        """Используем универсальную карточку для товаров"""
        # Определяем изображение: если image_id отсутствует или None, используем "default"
        image_src = item['image_id'] if item.get('image_id') else "default"

        return create_card(
            title=item['name'],
            subtitle=f"{self.selected_category['parameter'] or 'Параметр'}: {item['parameter_value']}",
            description=f"Ед. измерения: {item['unit']}",
            image=image_src,
            title_size=18,
            subtitle_size=14,
            image_width=120,
            image_height=120
        )

    def search_items(self, e):
        """Поиск товаров по запросу."""
        query = e.control.value
        if not query:
            if self.selected_category:
                self.load_category_items(self.selected_category)
            else:
                self.load_categories()
            return

        self.page.add(ft.ProgressBar())
        self.page.update()

        try:
            response = requests.get(f"http://localhost:8000/items/search?query={query}")
            if response.status_code == 200:
                items = response.json()
                self.update_item_list(items)
        except Exception as e:
            self.show_snackbar(f"Ошибка при поиске товаров: {str(e)}")
        finally:
            self.page.controls.pop()
            self.page.update()

    def show_add_dialog(self, e):
        """Показ диалога добавления категории или товара."""
        if self.selected_category:
            self.show_add_item_dialog(e, self.selected_category)
        else:
            self.show_add_category_dialog(e)

    def show_add_category_dialog(self, e):
        """Диалог добавления категории."""
        self.parameter_field = None
        self.selected_unit_index = 0
        
        self.add_button = ft.ElevatedButton(
            "+",
            on_click=self.add_parameter_field,
            visible=True
        )
        
        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Добавить категорию"),
            content=ft.Column(
                controls=[
                    ft.TextField(label="Название категории"),
                    ft.Text("Уникальный параметр:"),
                    self.add_button,
                    ft.CupertinoSlidingSegmentedButton(
                        selected_index=self.selected_unit_index,
                        thumb_color=ft.colors.BLUE,
                        on_change=self.on_unit_change,
                        controls=[
                            ft.Text("шт."),
                            ft.Text("блок"),
                            ft.Text("метр"),
                            ft.Text("разн.")
                        ]
                    ),
                    ft.ElevatedButton("Создать", on_click=self.create_category)
                ]
            )
        )
        self.page.dialog.open = True
        self.page.update()

    def on_unit_change(self, e):
        """Обработка изменения единицы измерения."""
        self.selected_unit_index = int(e.data)

    def add_parameter_field(self, e):
        """Добавление поля для параметра."""
        self.parameter_field = ft.TextField(label="Параметр")
        content = self.page.dialog.content
        content.controls.insert(2, self.parameter_field)
        self.add_button.visible = False
        self.page.update()

    def create_category(self, e):
        """Создание новой категории."""
        try:
            name = self.page.dialog.content.controls[0].value
            parameter = self.parameter_field.value if self.parameter_field else None
            unit = ["шт.", "блок", "метр", "разн."][self.selected_unit_index]
            
            response = requests.post(
                "http://localhost:8000/categories",
                json={
                    "name": name,
                    "parameter": parameter or "Без параметра",
                    "unit": unit
                }
            )
            
            if response.ok:
                self.load_categories()
                self.show_snackbar("Категория создана!")
            else:
                self.show_snackbar(f"Ошибка: {response.text}")
            
            self.page.dialog.open = False
            self.parameter_field = None
            self.add_button = None
            
        except Exception as ex:
            self.show_snackbar(f"Ошибка: {str(ex)}")
        
        self.page.update()

    def show_add_item_dialog(self, e, category=None):
        """Диалог добавления товара."""
        target_category = category or self.selected_category
        if not target_category:
            return

        self.selected_image_path = None

        def pick_image(e):
            self.image_picker.pick_files(allow_multiple=False, allowed_extensions=["jpg", "png", "jpeg"])

        def on_image_picked(e: ft.FilePickerResultEvent):
            if e.files:
                self.selected_image_path = e.files[0].path
                image_name.value = self.selected_image_path.split("/")[-1]
                self.page.update()

        self.image_picker.on_result = on_image_picked

        image_name = ft.Text("Файл не выбран", color=ft.colors.GREY)

        self.page.dialog = ft.AlertDialog(
            title=ft.Text("Добавить товар"),
            content=ft.Column(
                controls=[
                    ft.TextField(label="Название товара"),
                    ft.Text(f"Категория: {target_category['name']}"),
                    ft.TextField(label=f"{target_category['parameter'] or 'Параметр'}"),
                    ft.Text(f"Единица измерения: {target_category['unit']}"),
                    ft.ElevatedButton("Выбрать изображение", on_click=pick_image),
                    image_name,
                    ft.ElevatedButton("Создать", on_click=lambda e: self.create_item(target_category))
                ]
            )
        )
        self.page.dialog.open = True
        self.page.update()

    def create_item(self, e, category=None):
        """Создание нового товара."""
        try:
            target_category = category or self.selected_category
            if not target_category:
                raise ValueError("Категория не выбрана")

            name = self.page.dialog.content.controls[0].value
            parameter_value = self.page.dialog.content.controls[2].value

            if self.selected_image_path:
                with open(self.selected_image_path, "rb") as image_file:
                    files = {"image": (os.path.basename(self.selected_image_path), image_file)}
                    upload_response = requests.post("http://localhost:8000/upload_image", files=files)
                    if upload_response.status_code != 200:
                        raise ValueError("Ошибка при загрузке изображения")
                    image_id = upload_response.json()["image_id"]
            else:
                image_id = None

            data = {
                "name": name,
                "category_id": target_category['id'],
                "parameter_value": parameter_value,
                "unit": target_category['unit'],
                "image_id": image_id
            }

            response = requests.post("http://localhost:8000/items", json=data)
            if response.status_code == 200:
                self.load_category_items(target_category)
            else:
                self.show_snackbar(f"Ошибка: {response.text}")

        except Exception as ex:
            self.show_snackbar(f"Ошибка: {str(ex)}")
        finally:
            self.page.dialog.open = False
            self.page.update()

    def show_snackbar(self, message):
        """Показ уведомления."""
        self.page.snack_bar = ft.SnackBar(content=ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()

def tovari_page(e: ft.ControlEvent):
    """Инициализация страницы товаров."""
    page = e.page
    TovariPage(page)