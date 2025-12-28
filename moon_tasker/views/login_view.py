"""
ログイン画面（Email認証）
"""
import flet as ft
from ..cloud import get_auth


class LoginView(ft.Column):
    """ログイン画面"""
    
    def __init__(self, page: ft.Page, on_login_success):
        super().__init__()
        self.page = page
        self.on_login_success = on_login_success
        self.auth = get_auth()
        self.spacing = 30
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.alignment = ft.MainAxisAlignment.CENTER
        self.expand = True
        
        # 入力フィールド
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
        
        self._build()
    
    def _build(self):
        """画面を構築"""
        # ロゴとタイトル
        logo = ft.Column([
            ft.Text("🌙", size=80),
            ft.Text("Moon Tasker", size=36, weight=ft.FontWeight.BOLD, color="#90caf9"),
            ft.Text("〜月と共に成長するタスク管理〜", size=16, color="#9e9e9e"),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        
        # Supabase設定チェック
        if not self.auth.is_configured:
            warning_card = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.WARNING, color="#ff9800", size=40),
                    ft.Text("クラウド機能が設定されていません", weight=ft.FontWeight.BOLD),
                    ft.Text("開発者にお問い合わせください", size=12, color="#9e9e9e"),
                    ft.ElevatedButton(
                        "オフラインで続行",
                        icon="offline_bolt",
                        on_click=self._continue_offline
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                bgcolor="#1e3a5f",
                border_radius=15,
                padding=30,
            )
            self.controls = [logo, warning_card]
            return
        
        # ログインフォーム
        login_button = ft.ElevatedButton(
            "ログイン",
            icon="login",
            bgcolor="#4caf50",
            color="white",
            width=280,
            height=45,
            on_click=self._login
        )
        
        signup_button = ft.ElevatedButton(
            "新規登録",
            icon="person_add",
            bgcolor="#2196f3",
            color="white",
            width=280,
            height=45,
            on_click=self._signup
        )
        
        offline_button = ft.TextButton(
            "オフラインで使用する",
            on_click=self._continue_offline
        )
        
        # 説明
        info_text = ft.Text(
            "ログインすると、データがクラウドに保存され\nフレンド機能が使えるようになります",
            size=12,
            color="#9e9e9e",
            text_align=ft.TextAlign.CENTER
        )
        
        login_card = ft.Container(
            content=ft.Column([
                self.email_field,
                self.password_field,
                ft.Container(height=10),
                login_button,
                ft.Text("または", size=12, color="#757575"),
                signup_button,
                ft.Container(height=10),
                offline_button,
                ft.Container(height=10),
                info_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
            bgcolor="#1e3a5f80",
            border=ft.border.all(1, "#ffffff20"),
            border_radius=15,
            padding=30,
        )
        
        self.controls = [
            ft.Container(expand=True),
            logo,
            ft.Container(height=30),
            login_card,
            ft.Container(expand=True),
        ]
    
    def _login(self, e):
        """ログイン"""
        email = self.email_field.value
        password = self.password_field.value
        
        if not email or not password:
            self._show_error("メールアドレスとパスワードを入力してください")
            return
        
        success = self.auth.sign_in_with_email(email, password)
        if success:
            self.on_login_success()
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
        
        success = self.auth.sign_up_with_email(email, password)
        if success:
            self._show_success("登録完了！確認メールを送信しました。メールを確認してログインしてください。")
        else:
            self._show_error("登録に失敗しました。別のメールアドレスをお試しください。")
    
    def _continue_offline(self, e):
        """オフラインモードで続行"""
        self.on_login_success()
    
    def _show_error(self, message: str):
        """エラーを表示"""
        snackbar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor="#f44336",
            action="OK"
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
    
    def _show_success(self, message: str):
        """成功メッセージを表示"""
        snackbar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor="#4caf50",
            action="OK"
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
