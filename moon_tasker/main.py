"""
Moon Tasker - Test Version 4
Super simple with buttons
"""
import flet as ft
import os


def main(page: ft.Page):
    """Test app with buttons"""
    page.title = "Moon Tasker"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.bgcolor = "#0f0f1a"
    
    # 状態
    current_view = ft.Text("🏠 ホーム画面", size=24)
    
    def change_view(name):
        current_view.value = name
        page.update()
    
    # レイアウト
    page.add(
        ft.Column([
            ft.Text("🌙 Moon Tasker", size=32, weight=ft.FontWeight.BOLD, color="#90caf9"),
            ft.Divider(),
            ft.Row([
                ft.ElevatedButton("🏠 ホーム", on_click=lambda e: change_view("🏠 ホーム画面")),
                ft.ElevatedButton("⏱️ タイマー", on_click=lambda e: change_view("⏱️ タイマー画面")),
                ft.ElevatedButton("📝 タスク", on_click=lambda e: change_view("📝 タスク管理画面")),
            ]),
            ft.Divider(),
            current_view,
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )


if __name__ == "__main__":
    port = int(os.environ.get("FLET_SERVER_PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0", view=None)
