"""
Moon Tasker - メインアプリケーション（Render互換版）
NavigationRailの代わりにボタンベースナビゲーションを使用
"""
import flet as ft
import os
from .database import Database
from .views.home_view import HomeView
from .views.timer_view import TimerView
from .views.creature_view import CreatureView
from .views.collection_view import CollectionView
from .views.moon_cycle_view import MoonCycleView
from .views.playlist_view import PlaylistView
from .views.friend_view import FriendView


def main(page: ft.Page):
    """アプリケーションエントリーポイント"""
    
    # ページ設定
    page.title = "Moon Tasker"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.bgcolor = "#0f0f1a"
    
    # カスタムテーマ
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#7c4dff",
            secondary="#00bcd4",
            surface="#1a1a2e",
        ),
    )
    
    # データベース初期化
    db = Database()
    
    # ナビゲーション状態
    current_view = {"index": 0}
    
    # コンテンツエリア
    content_area = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    
    def change_view(index):
        """画面を切り替え"""
        current_view["index"] = index
        content_area.controls.clear()
        
        # ナビボタンの色を更新
        for i, btn in enumerate(nav_buttons):
            if i == index:
                btn.bgcolor = "#7c4dff"
                btn.color = "white"
            else:
                btn.bgcolor = "#1e3a5f"
                btn.color = "#90caf9"
        
        # ビューを表示
        if index == 0:
            content_area.controls.append(HomeView(db, page))
        elif index == 1:
            content_area.controls.append(TimerView(db, page))
        elif index == 2:
            content_area.controls.append(PlaylistView(db, page))
        elif index == 3:
            content_area.controls.append(MoonCycleView(db, page))
        elif index == 4:
            content_area.controls.append(CollectionView(db, page))
        elif index == 5:
            content_area.controls.append(CreatureView(db, page))
        elif index == 6:
            content_area.controls.append(FriendView(page))
        
        page.update()
    
    def on_nav_click(e):
        """ナビゲーションボタンクリック"""
        index = e.control.data
        change_view(index)
    
    # ナビゲーションボタン
    nav_items = [
        ("🏠", "ホーム", 0),
        ("⏱️", "タイマー", 1),
        ("📝", "タスク", 2),
        ("🌙", "月サイクル", 3),
        ("⭐", "星座図鑑", 4),
        ("🐾", "生命体", 5),
        ("👥", "フレンド", 6),
    ]
    
    nav_buttons = []
    for emoji, label, idx in nav_items:
        btn = ft.ElevatedButton(
            content=ft.Column([
                ft.Text(emoji, size=20),
                ft.Text(label, size=10),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
            data=idx,
            on_click=on_nav_click,
            bgcolor="#7c4dff" if idx == 0 else "#1e3a5f",
            color="white" if idx == 0 else "#90caf9",
            width=70,
            height=60,
        )
        nav_buttons.append(btn)
    
    # サイドナビゲーション
    side_nav = ft.Container(
        content=ft.Column(
            nav_buttons,
            spacing=5,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#1e3a5f",
        padding=10,
        width=90,
    )
    
    # 初期画面を表示
    content_area.controls.append(HomeView(db, page))
    
    # タイマーからchange_viewにアクセスできるようにpageに保存
    page.change_view = change_view
    
    # レイアウト
    layout = ft.Row([
        side_nav,
        ft.VerticalDivider(width=1, color="#2a2a4a"),
        ft.Container(
            content=content_area,
            expand=True,
            padding=20,
        ),
    ], expand=True)
    
    page.add(layout)
    
    # 初回起動チェック（データがない場合はオンボーディング表示）
    if db.get_completed_task_count() == 0:
        show_onboarding(page)


def show_onboarding(page):
    """初回起動時のオンボーディングダイアログを表示"""
    def close_dialog(e):
        dialog.open = False
        page.update()
    
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("🌙 Moon Taskerへようこそ！", size=22, weight=ft.FontWeight.BOLD),
        content=ft.Container(
            content=ft.Column([
                ft.Text("月の満ち欠けとともにタスクを管理し、\n生命体を育てるアプリです。", size=14),
                ft.Divider(),
                ft.Row([ft.Text("1️⃣", size=20), ft.Text("ホームで「クイックスタート」をタップして\n25分間の集中タイムを体験！", size=13)]),
                ft.Row([ft.Text("2️⃣", size=20), ft.Text("「生命体」画面で相棒を育て始めよう", size=13)]),
                ft.Row([ft.Text("3️⃣", size=20), ft.Text("「プレイリスト」でタスクを管理", size=13)]),
                ft.Container(height=10),
                ft.Text("頑張った分だけ相棒も成長します！✨", size=14, color="#ffc107", weight=ft.FontWeight.BOLD),
            ], spacing=10),
            width=300,
        ),
        actions=[
            ft.ElevatedButton(
                "始める 🚀",
                bgcolor="#4caf50",
                color="white",
                on_click=close_dialog
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER
    )
    page.dialog = dialog
    dialog.open = True
    page.update()


if __name__ == "__main__":
    port = int(os.environ.get("FLET_SERVER_PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0", view=None)
