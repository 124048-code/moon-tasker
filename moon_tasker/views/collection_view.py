"""
星座図鑑画面（ゲーミフィケーション強化版）
"""
import flet as ft
from ..database import Database
from ..logic.badge_logic import BadgeSystem


class CollectionView(ft.Column):
    """星座図鑑画面"""
    
    def __init__(self, db: Database, page: ft.Page = None):
        super().__init__()
        self.db = db
        self._page = page
        self.badge_system = BadgeSystem(db)
        self.spacing = 20
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        
        self._build()
    
    def _build(self):
        """画面を構築"""
        self.controls.clear()
        
        # 図鑑を開いた時に称号達成をチェック（自動解放）
        newly_unlocked = self.badge_system.check_all_badges()
        if newly_unlocked and self._page:
            # 新しく解放された称号があれば演出表示
            self._page.run_task(self._show_unlock_animation_async, newly_unlocked)
        
        title = ft.Text("星座図鑑 ⭐", size=28, weight=ft.FontWeight.BOLD)
        
        # バッジ一覧を取得（チェック後の最新状態）
        badges = self.db.get_all_badges()
        unlocked_count = len([b for b in badges if b.unlocked])
        total_count = len(badges)
        
        # 進捗表示（プログレスバー付き）
        progress_rate = unlocked_count / total_count if total_count > 0 else 0
        
        progress_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🌟 コレクション進捗", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{unlocked_count} / {total_count}", size=18, color="#ffc107"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.ProgressBar(value=progress_rate, color="#ffc107", bgcolor="#424242"),
                ft.Text(f"{progress_rate * 100:.0f}% 達成", size=14, color="#9e9e9e"),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # カテゴリ別に分類
        categories = {
            "🌱 初心者": ["First Steps", "Early Bird"],
            "🏆 タスク達成": ["Task Master", "Scorpius", "Centurion"],
            "🌙 目標サイクル": ["Moon Walker", "Lunar Master", "Gemini Flow"],
            "🔥 継続力": ["Dedicated", "Polaris"],
            "⏰ 時間帯": ["Night Owl", "Morning Star"],
            "⚔️ 難易度": ["Dragon Slayer", "Harmony"],
            "💫 生命体": ["Soul Friend", "Sagittarius"],
        }
        
        category_sections = []
        for category_name, badge_names in categories.items():
            category_badges = [b for b in badges if b.name in badge_names]
            if category_badges:
                section = self._build_category_section(category_name, category_badges)
                category_sections.append(section)
        
        self.controls = [
            title,
            progress_section,
            ft.Divider(),
            *category_sections,
        ]
    
    def _build_category_section(self, category_name: str, badges):
        """カテゴリセクションを構築"""
        badge_cards = []
        
        for badge in badges:
            rarity = self.badge_system.get_rarity_from_condition(badge)
            progress = self.badge_system.get_badge_progress(badge)
            card = self._build_badge_card(badge, rarity, progress)
            badge_cards.append(card)
        
        # グリッド配置
        rows = []
        for i in range(0, len(badge_cards), 2):
            rows.append(ft.Row(
                badge_cards[i:i+2],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            ))
        
        return ft.Container(
            content=ft.Column([
                ft.Text(category_name, size=16, weight=ft.FontWeight.BOLD, color="#64b5f6"),
                *rows,
            ], spacing=10),
            padding=ft.padding.only(bottom=20)
        )
    
    def _build_badge_card(self, badge, rarity: int, progress: tuple):
        """個別のバッジカードを構築"""
        current, target = progress
        
        # レア度に応じた星表示と色
        rarity_stars = "★" * rarity + "☆" * (5 - rarity)
        rarity_colors = {
            1: "#9e9e9e",  # コモン（グレー）
            2: "#4caf50",  # アンコモン（緑）
            3: "#2196f3",  # レア（青）
            4: "#9c27b0",  # エピック（紫）
            5: "#ffc107",  # レジェンダリー（金）
        }
        rarity_color = rarity_colors.get(rarity, "#9e9e9e")
        
        if badge.unlocked:
            # 解放済み
            card = ft.Container(
                content=ft.Column([
                    ft.Text("✨", size=36),
                    ft.Text(badge.constellation_name, size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(badge.name, size=12, color="#64b5f6", italic=True),
                    ft.Text(rarity_stars, size=10, color=rarity_color),
                    ft.Divider(height=5, color="transparent"),
                    ft.Text(badge.description, size=10, color="#9e9e9e", text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                bgcolor="#263238",
                border=ft.border.all(2, rarity_color),
                border_radius=10,
                padding=15,
                width=170,
                height=180,
                on_click=lambda e, b=badge: self._show_badge_detail(b),
            )
        else:
            # 未解放（進捗表示付き）
            progress_rate = current / target if target > 0 else 0
            
            card = ft.Container(
                content=ft.Column([
                    ft.Text("🔒", size=36),
                    ft.Text("???", size=16, weight=ft.FontWeight.BOLD, color="#757575"),
                    ft.Text(rarity_stars, size=10, color="#424242"),
                    ft.Divider(height=5, color="transparent"),
                    ft.Text(f"進捗: {current}/{target}", size=10, color="#757575"),
                    ft.ProgressBar(value=progress_rate, width=120, color=rarity_color, bgcolor="#424242"),
                    ft.Text(badge.description, size=9, color="#616161", text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                bgcolor="#1a1a1a",
                border=ft.border.all(1, "#424242"),
                border_radius=10,
                padding=15,
                width=170,
                height=180,
            )
        
        return card
    
    def _show_badge_detail(self, badge):
        """バッジ詳細ダイアログを表示"""
        if not self.page:
            return
        
        rarity = self.badge_system.get_rarity_from_condition(badge)
        rarity_stars = "★" * rarity + "☆" * (5 - rarity)
        rarity_names = {1: "コモン", 2: "アンコモン", 3: "レア", 4: "エピック", 5: "レジェンダリー"}
        rarity_name = rarity_names.get(rarity, "コモン")
        
        unlocked_text = ""
        if badge.unlocked_at:
            if isinstance(badge.unlocked_at, str):
                unlocked_text = f"🗓️ 獲得日: {badge.unlocked_at[:10]}"
            else:
                unlocked_text = f"🗓️ 獲得日: {badge.unlocked_at.strftime('%Y-%m-%d')}"
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Text("✨", size=32),
                ft.Column([
                    ft.Text(badge.constellation_name, size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(badge.name, size=14, color="#64b5f6", italic=True),
                ], spacing=0),
            ]),
            content=ft.Column([
                ft.Text(rarity_stars, size=16, color="#ffc107"),
                ft.Text(f"レア度: {rarity_name}", size=12, color="#9e9e9e"),
                ft.Divider(),
                ft.Text(badge.description, size=14),
                ft.Container(height=10),
                ft.Text(unlocked_text, size=12, color="#81c784") if unlocked_text else ft.Container(),
            ], tight=True),
            actions=[
                ft.TextButton("閉じる", on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self._page.open(dialog)
    
    def check_and_show_new_badges(self):
        """新しく獲得した称号をチェックして演出表示"""
        newly_unlocked = self.badge_system.check_all_badges()
        
        if newly_unlocked and self._page:
            # 演出ダイアログを表示
            self._show_unlock_animation(newly_unlocked)
        
        return newly_unlocked
    
    def _show_unlock_animation(self, badges):
        """称号獲得演出ダイアログ"""
        if not self.page:
            return
        
        badge = badges[0]  # 最初の1つを表示
        rarity = self.badge_system.get_rarity_from_condition(badge)
        rarity_stars = "★" * rarity + "☆" * (5 - rarity)
        rarity_colors = {
            1: "#9e9e9e", 2: "#4caf50", 3: "#2196f3", 4: "#9c27b0", 5: "#ffc107"
        }
        rarity_color = rarity_colors.get(rarity, "#ffc107")
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
            # 複数獲得の場合は次を表示
            if len(badges) > 1:
                self._show_unlock_animation(badges[1:])
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Column([
                ft.Text("🎊 NEW CONSTELLATION 🎊", size=16, color="#ffc107", 
                       text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD),
                ft.Text("新しい星座を発見！", size=14, color="#9e9e9e", text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
            content=ft.Container(
                content=ft.Column([
                    ft.Container(height=20),
                    ft.Text("✨", size=60, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    ft.Text(badge.constellation_name, size=28, weight=ft.FontWeight.BOLD, 
                           text_align=ft.TextAlign.CENTER, color=rarity_color),
                    ft.Text(badge.name, size=16, color="#64b5f6", italic=True, 
                           text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    ft.Text(rarity_stars, size=20, color=rarity_color, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=15),
                    ft.Container(
                        content=ft.Text(badge.description, size=14, text_align=ft.TextAlign.CENTER),
                        bgcolor="#263238",
                        border_radius=10,
                        padding=15
                    ),
                    ft.Container(height=20),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=280,
            ),
            actions=[
                ft.ElevatedButton(
                    "素晴らしい！ 🌟",
                    bgcolor=rarity_color,
                    color="white",
                    on_click=close_dialog
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self._page.open(dialog)
    
    async def _show_unlock_animation_async(self, badges):
        """非同期で称号獲得演出を表示"""
        import asyncio
        await asyncio.sleep(0.3)  # UI構築を待つ
        self._show_unlock_animation(badges)


def show_badge_unlock_if_any(db: Database, page: ft.Page):
    """称号獲得チェック＆表示のヘルパー関数（タスク完了後に呼び出す）"""
    collection = CollectionView(db, page)
    return collection.check_and_show_new_badges()

