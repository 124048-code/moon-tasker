"""
Moon Tasker - Test Version 2
Adding Database and basic navigation
"""
import flet as ft
import os


def main(page: ft.Page):
    """Test app with navigation"""
    page.title = "Moon Tasker"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    
    # ナビゲーション状態
    current_index = {"value": 0}
    
    # コンテンツエリア
    content_area = ft.Column([
        ft.Text("ホーム画面", size=24),
        ft.Text("ここにコンテンツが表示されます", size=16),
    ], expand=True)
    
    def on_nav_change(e):
        idx = e.control.selected_index
        current_index["value"] = idx
        content_area.controls.clear()
        
        if idx == 0:
            content_area.controls.append(ft.Text("🏠 ホーム", size=24))
        elif idx == 1:
            content_area.controls.append(ft.Text("⏱️ タイマー", size=24))
        elif idx == 2:
            content_area.controls.append(ft.Text("📝 タスク管理", size=24))
        
        page.update()
    
    # ナビゲーションレール
    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        destinations=[
            ft.NavigationRailDestination(
                icon="home_outlined",
                selected_icon="home",
                label="ホーム"
            ),
            ft.NavigationRailDestination(
                icon="timer_outlined",
                selected_icon="timer",
                label="タイマー"
            ),
            ft.NavigationRailDestination(
                icon="playlist_play_outlined",
                selected_icon="playlist_play",
                label="タスク"
            ),
        ],
        on_change=on_nav_change,
        bgcolor="#1e3a5f",
    )
    
    # レイアウト
    layout = ft.Row([
        nav_rail,
        ft.VerticalDivider(width=1),
        ft.Container(
            content=content_area,
            expand=True,
            padding=20,
            bgcolor="#0f0f1a",
        ),
    ], expand=True)
    
    page.add(layout)


if __name__ == "__main__":
    port = int(os.environ.get("FLET_SERVER_PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0", view=None)
