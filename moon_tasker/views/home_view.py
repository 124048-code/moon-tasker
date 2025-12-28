"""
ホーム画面
"""
import flet as ft
from ..database import Database
from ..logic.creature_logic import CreatureSystem
from ..logic.moon_cycle import MoonCycleCalculator


class HomeView(ft.Column):
    """ダッシュボード画面"""
    
    def __init__(self, db: Database, page: ft.Page = None):
        super().__init__()
        self.db = db
        self._page = page
        self.creature_system = CreatureSystem(db)
        self.moon_calc = MoonCycleCalculator()
        self.spacing = 20
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        
        self._build()
    
    def _build(self):
        """画面を構築"""
        self.controls.clear()
        
        # 生命体情報を取得
        creature = self.creature_system.get_creature()
        
        # 月の情報
        moon_phase = self.moon_calc.get_moon_phase_name()
        moon_emoji = self.moon_calc.get_moon_emoji()
        
        # タスク統計
        tasks = self.db.get_all_tasks()
        pending_count = len([t for t in tasks if t.status == "pending"])
        completed_count = self.db.get_completed_task_count()
        
        # タイトル
        title = ft.Text(
            "Moon Tasker 🌙",
            size=32,
            weight=ft.FontWeight.BOLD,
            color="#90caf9"
        )
        
        # 🚀 クイックスタートカード（最も目立つ位置）
        quick_start_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.icons.PLAY_CIRCLE, size=40, color="#4caf50"),
                    ft.Column([
                        ft.Text("今すぐ始める", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("25分間の集中タイムを開始", size=14, color="#9e9e9e"),
                    ], spacing=2),
                ], spacing=15),
                ft.ElevatedButton(
                    "⏱️ クイックスタート",
                    bgcolor="#4caf50",
                    color="white",
                    width=250,
                    height=50,
                    on_click=self._start_quick_timer
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
            bgcolor="#1e403080",  # 半透明グラス
            border=ft.border.all(1, "#4caf5080"),
            border_radius=15,
            padding=20,
            shadow=ft.BoxShadow(blur_radius=20, color="#00000040"),
        )
        
        # 月の情報カード
        moon_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(moon_emoji, size=40),
                    ft.Text(moon_phase, size=20, weight=ft.FontWeight.BOLD)
                ], alignment=ft.MainAxisAlignment.CENTER),
            ]),
            bgcolor="#1e3a5f80",  # 半透明グラス
            border=ft.border.all(1, "#ffffff20"),
            border_radius=15,
            padding=20,
            shadow=ft.BoxShadow(blur_radius=15, color="#00000030"),
        )
        
        # 生命体カード（育てている場合のみ表示）
        creature_card = None
        
        # アクティブまたは完了の生命体のみ表示
        if creature and creature.status in ["active", "completed"]:
            creature_visual = ft.Text("🥚", size=70)  # デフォルト
            emotion = {"speech": "", "desc": ""}
            warning = None
            card_bg_color = "#1e3a5f"
            card_border_color = "#64b5f6"
            
            # 放置チェック
            self.creature_system.check_neglect()
            
            emotion = self.creature_system.get_emotion_state(creature)
            warning = self.creature_system.get_warning_message(creature)
            
            # 画像またはフォールバック絵文字
            import os
            image_filename = self.creature_system.get_image_filename(creature)
            image_path = f"moon_tasker/assets/creature/{image_filename}"
            if os.path.exists(image_path):
                creature_visual = ft.Image(src=image_path, width=100, height=100, fit=ft.ImageFit.CONTAIN)
            else:
                creature_visual = ft.Text(self.creature_system.get_creature_emoji(creature), size=70)
            
            # 機嫌に応じた背景色
            if creature.mood >= 70:
                card_bg_color = "#1e3a5f"
                card_border_color = "#64b5f6"
            elif creature.mood >= 40:
                card_bg_color = "#3d3d1f"
                card_border_color = "#ffeb3b"
            elif creature.mood >= 20:
                card_bg_color = "#3d2f1f"
                card_border_color = "#ff9800"
            else:
                card_bg_color = "#3d1f1f"
                card_border_color = "#f44336"
            
            creature_card = ft.Container(
                content=ft.Column([
                    ft.Text("あなたの相棒", size=14, color="#9e9e9e"),
                    creature_visual,
                    ft.Text(creature.name, size=18, weight=ft.FontWeight.BOLD),
                    # セリフ
                    ft.Container(
                        content=ft.Text(f'「{emotion["speech"]}」' if emotion.get("speech") else "", size=16, color="#ffffff"),
                        bgcolor="#424242" if emotion.get("speech") else "transparent",
                        border_radius=10,
                        padding=ft.padding.symmetric(horizontal=15, vertical=8) if emotion.get("speech") else 0
                    ) if emotion.get("speech") else ft.Container(),
                    # 様子
                    ft.Text(f"（{emotion['desc']}）" if emotion.get("desc") else "", size=12, color="#9e9e9e", italic=True),
                    ft.Container(height=5),
                    ft.Text(warning, size=12, color="#f44336", weight=ft.FontWeight.BOLD) if warning else ft.Container(),
                    ft.ProgressBar(
                        value=creature.mood / 100,
                        color="#f06292" if creature.mood >= 30 else "#f44336",
                        bgcolor="#424242"
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=card_bg_color,
                border=ft.border.all(2, card_border_color),
                border_radius=10,
                padding=20
            )
        
        # タスク統計カード
        stats_card = ft.Container(
            content=ft.Column([
                ft.Text("今日のタスク", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    ft.Column([
                        ft.Text(str(pending_count), size=32, weight=ft.FontWeight.BOLD, color="#fff176"),
                        ft.Text("未完了", size=14, color="#9e9e9e"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.VerticalDivider(),
                    ft.Column([
                        ft.Text(str(completed_count), size=32, weight=ft.FontWeight.BOLD, color="#81c784"),
                        ft.Text("完了", size=14, color="#9e9e9e"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                ], alignment=ft.MainAxisAlignment.SPACE_AROUND),
            ]),
            bgcolor="#1e3a5f80",
            border=ft.border.all(1, "#ffffff20"),
            border_radius=15,
            padding=20,
            shadow=ft.BoxShadow(blur_radius=15, color="#00000030"),
        )
        
        # ストリークカード 🔥
        streak_data = self.db.get_streak_data()
        streak_emoji = "🔥" if streak_data["current_streak"] > 0 else "💤"
        streak_color = "#ff9800" if streak_data["current_streak"] > 0 else "#757575"
        
        streak_card = ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text(streak_emoji, size=30),
                ]),
                ft.Column([
                    ft.Text(f'{streak_data["current_streak"]} 日連続達成！' if streak_data["current_streak"] > 0 else "今日から始めよう！", 
                           size=16, weight=ft.FontWeight.BOLD, color=streak_color),
                    ft.Text(f'最高記録: {streak_data["max_streak"]}日 / 累計: {streak_data["total_days"]}日', 
                           size=12, color="#9e9e9e"),
                ], spacing=2),
            ], alignment=ft.MainAxisAlignment.START, spacing=15),
            bgcolor="#1e3a5f80",
            border=ft.border.all(1, "#ffffff20"),
            border_radius=15,
            padding=15,
            shadow=ft.BoxShadow(blur_radius=15, color="#00000030"),
        )
        
        # コンポーネントを追加（クイックスタートを最上部に）
        controls = [title, quick_start_card, moon_card]
        if creature_card:
            controls.append(creature_card)
        controls.extend([stats_card, streak_card])
        self.controls = controls
    
    def _start_quick_timer(self, e):
        """クイックスタートタイマーを開始"""
        if self.page and hasattr(self._page, 'change_view'):
            # タイマー画面に移動し、クイックモードフラグを設定
            self._page.quick_start_mode = True
            if hasattr(self._page, 'navigation_rail'):
                self._page.navigation_rail.selected_index = 1
            self._page.change_view(1)
