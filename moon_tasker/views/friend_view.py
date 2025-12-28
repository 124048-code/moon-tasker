"""
フレンド画面
"""
import flet as ft
from ..cloud import get_auth, get_cloud_db
from ..database import Database
from ..logic.creature_logic import CreatureSystem


class FriendView(ft.Column):
    """フレンド画面"""
    
    def __init__(self, page: ft.Page):
        super().__init__()
        self._page = page
        self.db = Database()
        self.creature_system = CreatureSystem(self.db)
        self.auth = get_auth()
        self.cloud_db = get_cloud_db()
        self.spacing = 20
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        
        self._build()
    
    def _build(self):
        """画面を構築"""
        # 既存のコントロールをクリア（重複防止）
        self.controls.clear()
        
        title = ft.Text("フレンド 👥", size=28, weight=ft.FontWeight.BOLD)
        
        # ログインチェック
        if not self.auth.is_authenticated:
            # ログインフォームを表示
            self.email_field = ft.TextField(
                label="メールアドレス",
                width=280,
                keyboard_type=ft.KeyboardType.EMAIL,
            )
            self.password_field = ft.TextField(
                label="パスワード",
                width=280,
                password=True,
                can_reveal_password=True,
            )
            
            login_card = ft.Container(
                content=ft.Column([
                    ft.Icon("people", size=50, color="#64b5f6"),
                    ft.Text("ログインしてフレンド機能を使おう！", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text("データがクラウドに保存されます", size=12, color="#9e9e9e"),
                    ft.Container(height=10),
                    self.email_field,
                    self.password_field,
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "ログイン",
                        icon="login",
                        bgcolor="#4caf50",
                        color="white",
                        width=200,
                        on_click=self._login
                    ),
                    ft.Text("または", size=12, color="#757575"),
                    ft.ElevatedButton(
                        "新規登録",
                        icon="person_add",
                        bgcolor="#2196f3",
                        color="white",
                        width=200,
                        on_click=self._signup
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                bgcolor="#1e3a5f80",
                border=ft.border.all(1, "#ffffff20"),
                border_radius=15,
                padding=30,
            )
            self.controls = [title, login_card]
            return
        
        # プロフィールカード
        user = self.auth.user
        profile = self.cloud_db.get_profile(self.auth.user_id) if self.auth.user_id else None
        
        # ローカル生命体情報を取得
        creature_info = ""
        try:
            creature = self.creature_system.get_creature()
            if creature and hasattr(creature, 'status') and creature.status in ["active", "completed"]:
                # 進化段階を1-5で表示
                stage_map = {"egg": 1, "baby": 2, "child": 3, "adult": 4, "completed": 5}
                stage_num = stage_map.get(getattr(creature, 'stage', 'egg'), 1)
                
                # 機嫌を絵文字で表示
                mood = getattr(creature, 'mood', 50)
                if mood >= 80:
                    mood_emoji = "😊"
                    mood_text = "ごきげん"
                elif mood >= 50:
                    mood_emoji = "🙂"
                    mood_text = "ふつう"
                elif mood >= 30:
                    mood_emoji = "😐"
                    mood_text = "すこし不満"
                else:
                    mood_emoji = "😢"
                    mood_text = "かなしい"
                
                creature_name = getattr(creature, 'name', '生命体')
                creature_info = f"🌟 {creature_name} | {mood_emoji} {mood_text} | 進化Lv.{stage_num}"
        except Exception as e:
            print(f"生命体情報取得エラー: {e}")
            creature_info = ""
        
        profile_card = ft.Container(
            content=ft.Column([
                ft.Text("マイプロフィール", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    ft.CircleAvatar(
                        foreground_image_src=user.get("avatar") if user else None,
                        content=ft.Text(user.get("name", "?")[0] if user else "?"),
                        radius=30,
                    ),
                    ft.Column([
                        ft.Text(
                            profile.get("nickname") if profile else user.get("name", "未設定"),
                            size=16,
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Text(
                            f"⭐ {profile.get('constellation_badge', '称号なし')}" if profile else "称号なし",
                            size=12,
                            color="#ffc107"
                        ),
                    ], spacing=2),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon="edit",
                        tooltip="プロフィール編集",
                        on_click=self._edit_profile
                    ),
                ], spacing=15),
                # 生命体情報を表示
                ft.Container(
                    content=ft.Text(creature_info if creature_info else "🥚 生命体を育てていません", size=12, color="#90caf9"),
                    bgcolor="#2a3a5f",
                    border_radius=8,
                    padding=10,
                ) if creature_info or True else None,
            ]),
            bgcolor="#1e3a5f80",
            border=ft.border.all(1, "#ffffff20"),
            border_radius=15,
            padding=20,
        )
        
        # フレンド一覧
        friends = self.cloud_db.get_friends(self.auth.user_id) if self.auth.user_id else []
        
        friend_cards = []
        if friends:
            for friend in friends:
                friend_profile = friend.get("profiles", {})
                creature = self.cloud_db.get_friend_creature(friend.get("friend_id"))
                
                friend_card = self._build_friend_card(friend_profile, creature)
                friend_cards.append(friend_card)
        else:
            friend_cards.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text("😢 まだフレンドがいません", size=16, color="#9e9e9e"),
                        ft.Text("フレンドコードを交換して追加しましょう！", size=12, color="#757575"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                )
            )
        
        friend_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("フレンド一覧", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "フレンド追加",
                        icon="person_add",
                        bgcolor="#4caf50",
                        color="white",
                        on_click=self._add_friend
                    ),
                ]),
                ft.Divider(),
                *friend_cards,
            ]),
            bgcolor="#1e3a5f80",
            border=ft.border.all(1, "#ffffff20"),
            border_radius=15,
            padding=20,
        )
        
        # フレンドコードセクション
        my_code = self.auth.user_id or "取得できませんでした"
        friend_code_section = ft.Container(
            content=ft.Column([
                ft.Text("あなたのフレンドコード", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.Text(my_code, size=12, selectable=True),
                    bgcolor="#2a3a5f",
                    border_radius=8,
                    padding=15,
                ),
                ft.Text("※コードをフレンドと共有してつながろう！", size=11, color="#9e9e9e"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            bgcolor="#1e3a5f80",
            border=ft.border.all(1, "#ffffff20"),
            border_radius=15,
            padding=20,
        )
        
        self.controls = [title, profile_card, friend_code_section, friend_section]
    
    def _build_friend_card(self, profile: dict, creature: dict = None):
        """フレンドカードを構築"""
        creature_display = "🥚"
        creature_name = ""
        
        if creature:
            stage = creature.get("stage", "egg")
            if stage == "adult":
                creature_display = "🐱"  # 成体アイコン
            elif stage == "child":
                creature_display = "🐣"  # 幼体アイコン
            creature_name = creature.get("name", "")
        
        return ft.Container(
            content=ft.Row([
                ft.Text(creature_display, size=40),
                ft.Column([
                    ft.Text(profile.get("nickname", "名無し"), weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"⭐ {profile.get('constellation_badge', '称号なし')}",
                        size=12,
                        color="#ffc107"
                    ),
                    ft.Text(
                        f"生命体: {creature_name}" if creature_name else "生命体なし",
                        size=12,
                        color="#9e9e9e"
                    ),
                ], spacing=2, expand=True),
            ], spacing=15),
            bgcolor="#2a3a5f",
            border_radius=10,
            padding=15,
        )
    
    def _edit_profile(self, e):
        """プロフィール編集ダイアログ"""
        profile = self.cloud_db.get_profile(self.auth.user_id) if self.auth.user_id else None
        
        nickname_field = ft.TextField(
            label="ニックネーム",
            value=profile.get("nickname", "") if profile else "",
            width=250,
        )
        
        def save_profile(e):
            if self.auth.user_id:
                self.cloud_db.upsert_profile(
                    self.auth.user_id,
                    nickname_field.value,
                    profile.get("constellation_badge", "") if profile else ""
                )
            dialog.open = False
            self._build()
            self._page.update()
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("プロフィール編集"),
            content=ft.Column([
                nickname_field,
                ft.Text("※称号はタスク完了で獲得できます", size=12, color="#9e9e9e"),
            ], tight=True),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.ElevatedButton("保存", on_click=save_profile),
            ],
        )
        
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()
    
    def _add_friend(self, e):
        """フレンド追加ダイアログ"""
        friend_code_field = ft.TextField(
            label="フレンドコード (ユーザーID)",
            width=300,
            hint_text="フレンドのIDを入力",
        )
        
        def send_request(e):
            if self.auth.user_id and friend_code_field.value:
                success = self.cloud_db.send_friend_request(
                    self.auth.user_id,
                    friend_code_field.value
                )
                if success:
                    snackbar = ft.SnackBar(content=ft.Text("フレンド申請を送信しました！"))
                    self._page.overlay.append(snackbar)
                    snackbar.open = True
            dialog.open = False
            self._page.update()
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        # 自分のフレンドコードを表示
        my_code = self.auth.user_id or "ログインが必要です"
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("フレンド追加"),
            content=ft.Column([
                ft.Text("あなたのフレンドコード:", weight=ft.FontWeight.BOLD),
                ft.Container(
                    content=ft.SelectableText(my_code, size=12),
                    bgcolor="#2a3a5f",
                    border_radius=5,
                    padding=10,
                ),
                ft.Divider(),
                ft.Text("フレンドを追加:", weight=ft.FontWeight.BOLD),
                friend_code_field,
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.ElevatedButton("申請送信", on_click=send_request),
            ],
        )
        
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()
    
    def _login(self, e):
        """ログイン"""
        email = self.email_field.value
        password = self.password_field.value
        
        if not email or not password:
            self._show_error("メールアドレスとパスワードを入力してください")
            return
        
        success = self.auth.sign_in_with_email(email, password)
        if success:
            self._show_success("ログインしました！")
            self._build()
            self._page.update()
        else:
            self._show_error("ログインに失敗しました。メールアドレスとパスワードを確認してください。")
    
    def _signup(self, e):
        """新規登録"""
        email = self.email_field.value
        password = self.password_field.value
        
        if not email or not password:
            self._show_error("メールアドレスとパスワードを入力してください")
            return
        
        if len(password) < 6:
            self._show_error("パスワードは6文字以上にしてください")
            return
        
        # 英数混合チェック
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        if not (has_letter and has_digit):
            self._show_error("パスワードは半角英数混合にしてください")
            return
        
        success = self.auth.sign_up_with_email(email, password)
        if success:
            self._show_success("登録完了！そのままログインしてください。")
        else:
            self._show_error("登録に失敗しました。別のメールアドレスをお試しください。")
    
    def _show_error(self, message: str):
        """エラーを表示"""
        snackbar = ft.SnackBar(content=ft.Text(message), bgcolor="#f44336")
        self._page.overlay.append(snackbar)
        snackbar.open = True
        self._page.update()
    
    def _show_success(self, message: str):
        """成功メッセージを表示"""
        snackbar = ft.SnackBar(content=ft.Text(message), bgcolor="#4caf50")
        self._page.overlay.append(snackbar)
        snackbar.open = True
        self._page.update()
