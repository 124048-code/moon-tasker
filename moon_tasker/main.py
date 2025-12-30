"""
Moon Tasker - Minimal Test Version
This is a simplified version to test if Flet works on Render
"""
import flet as ft


def main(page: ft.Page):
    """Minimal test app"""
    page.title = "Moon Tasker Test"
    page.theme_mode = ft.ThemeMode.DARK
    
    # Simple layout
    page.add(
        ft.Column([
            ft.Text("🌙 Moon Tasker", size=32, weight=ft.FontWeight.BOLD),
            ft.Text("アプリが正常に動作しています！", size=18),
            ft.ElevatedButton("テストボタン", on_click=lambda e: print("Clicked!")),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("FLET_SERVER_PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0", view=None)
