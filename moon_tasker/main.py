"""
Moon Tasker - Test Version 3
Using Tabs instead of NavigationRail
"""
import flet as ft
import os


def main(page: ft.Page):
    """Test app with tabs"""
    page.title = "Moon Tasker"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    
    # タブ
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[
            ft.Tab(text="ホーム", icon="home"),
            ft.Tab(text="タイマー", icon="timer"),
            ft.Tab(text="タスク", icon="playlist_play"),
        ],
    )
    
    # コンテンツ
    content = ft.Column([
        ft.Text("🌙 Moon Tasker", size=32, weight=ft.FontWeight.BOLD),
        ft.Text("アプリが動作しています！", size=18),
        tabs,
    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    
    page.add(content)


if __name__ == "__main__":
    port = int(os.environ.get("FLET_SERVER_PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0", view=None)
