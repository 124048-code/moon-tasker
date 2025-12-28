"""
Moon Tasker - メインアプリケーション
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
    page.padding = 0  # 背景画像用
    
    # カスタムテーマ（洗練されたカラーパレット + フォント）
    page.fonts = {
        "ZenKaku": "moon_tasker/assets/fonts/ZenKakuGothicNew-Regular.ttf",
        "ZenKakuMedium": "moon_tasker/assets/fonts/ZenKakuGothicNew-Medium.ttf",
    }
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="#7c4dff",
            secondary="#00bcd4",
            surface="#1a1a2e",
        ),
        font_family="ZenKaku",
    )
    
    # 背景画像パス
    bg_image_path = "moon_tasker/assets/background/main_bg.png"
    has_bg_image = os.path.exists(bg_image_path)
    

    
    # データベース初期化
    db = Database()
    
    # ナビゲーション状態
    current_view = {"index": 0}
    
    def change_view(index):
        """画面を切り替え"""
        current_view["index"] = index
        
        # コンテンツをクリア
        content_area.controls.clear()
        
        # 選択された画面を表示（6項目：ホーム→タイマー→タスク管理→月のサイクル→星座図鑑→生命体）
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
    
    def on_nav_change(e):
        """ナビゲーション変更イベント"""
        change_view(e.control.selected_index)
    
    def show_onboarding():
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
    
    # タイマーからchange_viewにアクセスできるようにpageに保存
    page.change_view = change_view
    
    # ナビゲーションレール（6項目：ホーム→タイマー→タスク管理→月のサイクル→星座図鑑→生命体）
    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
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
                label="タスク管理"
            ),
            ft.NavigationRailDestination(
                icon="nightlight_outlined",
                selected_icon="nightlight",
                label="月のサイクル"
            ),
            ft.NavigationRailDestination(
                icon="stars_outlined",
                selected_icon="stars",
                label="星座図鑑"
            ),
            ft.NavigationRailDestination(
                icon="pets_outlined",
                selected_icon="pets",
                label="生命体"
            ),
            ft.NavigationRailDestination(
                icon="people_outlined",
                selected_icon="people",
                label="フレンド"
            ),
        ],
        on_change=on_nav_change,
        bgcolor="#1e3a5f",
    )
    
    # タイマーからナビゲーションを制御できるようにpageに保存
    page.navigation_rail = nav_rail
    
    # コンテンツエリア
    content_area = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )
    
    # 初期画面を表示
    content_area.controls.append(HomeView(db, page))
    
    # レイアウト（ナビ + コンテンツ）
    main_content = ft.Row(
        [
            nav_rail,
            ft.VerticalDivider(width=1, color="#2a2a4a"),
            ft.Container(
                content=content_area,
                expand=True,
                padding=20,
            ),
        ],
        expand=True,
    )
    
    # 背景画像があればスタックで重ねる
    if has_bg_image:
        layout = ft.Stack([
            ft.Container(
                content=ft.Image(
                    src=bg_image_path,
                    fit="cover",
                    width=2000,  # 十分大きな幅
                    height=2000,  # 十分大きな高さ
                ),
                expand=True,
            ),
            ft.Container(
                content=main_content,
                bgcolor="#0f0f1a80",  # 半透明オーバーレイ
                expand=True,
            ),
        ], expand=True)
    else:
        layout = ft.Container(
            content=main_content,
            bgcolor="#0f0f1a",
            expand=True,
        )
    
    page.add(layout)
    
    # 初回起動チェック（データがない場合はオンボーディング表示）
    if db.get_completed_task_count() == 0:
        show_onboarding()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("FLET_SERVER_PORT", 8080))
    ft.app(target=main, port=port, host="0.0.0.0")
