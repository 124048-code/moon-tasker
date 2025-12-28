"""
プレイリスト管理画面
"""
import flet as ft
from ..database import Database
from ..models import Task, Playlist, LifestyleSettings
from ..logic.schedule_ai import ScheduleOptimizer, GeneticScheduleOptimizer


class PlaylistView(ft.Column):
    """プレイリスト管理画面"""
    
    def __init__(self, db: Database, page: ft.Page):
        super().__init__()
        self.db = db
        self.page = page
        self.optimizer = ScheduleOptimizer()
        self.spacing = 20
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        
        # 選択中のプレイリスト
        self.selected_playlist_id = None
        
        # UIコンポーネント
        self.playlist_dropdown = ft.Dropdown(
            label="プレイリストを選択",
            width=250,
            on_change=self.on_playlist_change
        )
        self.playlist_name_field = ft.TextField(
            label="新規プレイリスト名",
            width=200,
            hint_text="例: 朝のルーティン"
        )
        self.task_dropdown = ft.Dropdown(
            label="追加するタスク",
            width=250
        )
        
        # プレイリスト内タスク表示
        self.playlist_tasks_column = ft.Column()
        
        # タスク作成用
        self.task_name_field = ft.TextField(label="タスク名", width=200)
        self.difficulty_dropdown = ft.Dropdown(
            label="難易度",
            width=100,
            options=[
                ft.dropdown.Option("1", "簡単"),
                ft.dropdown.Option("2", "普通"),
                ft.dropdown.Option("3", "中程度"),
                ft.dropdown.Option("4", "難しい"),
                ft.dropdown.Option("5", "超難"),
            ],
            value="2"
        )
        self.duration_field = ft.TextField(label="作業時間（分）", width=150, value="25", keyboard_type=ft.KeyboardType.NUMBER)
        self.break_field = ft.TextField(label="休憩時間（分）", width=150, value="5", keyboard_type=ft.KeyboardType.NUMBER)
        
        # 未使用タスク一覧
        self.available_tasks_column = ft.Column()
        
        self._load_data()
        self._build()
    
    def _load_data(self):
        """データを読み込み（updateなし）"""
        # プレイリスト一覧
        playlists = self.db.get_all_playlists()
        self.playlist_dropdown.options = [
            ft.dropdown.Option(key=str(p.id), text=p.name)
            for p in playlists
        ]
        
        # タスク一覧
        tasks = self.db.get_all_tasks()
        pending_tasks = [t for t in tasks if t.status == "pending"]
        self.task_dropdown.options = [
            ft.dropdown.Option(key=str(t.id), text=f"{t.title} ({t.duration}分)")
            for t in pending_tasks
        ]
        
        # プレイリスト内タスクと未使用タスク
        self._build_playlist_tasks()
        self._build_available_tasks()
    
    def _build_playlist_tasks(self):
        """選択中プレイリストのタスク一覧を構築"""
        self.playlist_tasks_column.controls.clear()
        
        if not self.selected_playlist_id:
            self.playlist_tasks_column.controls.append(
                ft.Text("プレイリストを選択してください", color="#9e9e9e")
            )
            return
        
        tasks = self.db.get_playlist_tasks(self.selected_playlist_id)
        
        if not tasks:
            self.playlist_tasks_column.controls.append(
                ft.Text("タスクがありません。下から追加してください。", color="#9e9e9e")
            )
            return
        
        for i, task in enumerate(tasks):
            row = ft.Row([
                ft.Text(f"{i+1}.", size=16, width=30),
                ft.Text(task.title, size=16, expand=True),
                ft.Text(f"{task.duration}分", size=14, color="#9e9e9e"),
                ft.IconButton(
                    icon="arrow_upward",
                    tooltip="上へ移動",
                    on_click=lambda e, idx=i: self.move_task_up(idx),
                    disabled=i == 0
                ),
                ft.IconButton(
                    icon="arrow_downward",
                    tooltip="下へ移動",
                    on_click=lambda e, idx=i: self.move_task_down(idx),
                    disabled=i == len(tasks) - 1
                ),
                ft.IconButton(
                    icon="remove_circle",
                    tooltip="プレイリストから削除",
                    icon_color="#ff5722",
                    on_click=lambda e, tid=task.id: self.remove_from_playlist(tid)
                ),
            ])
            self.playlist_tasks_column.controls.append(row)
    
    def _build_available_tasks(self):
        """未使用タスク一覧を構築"""
        self.available_tasks_column.controls.clear()
        
        tasks = self.db.get_all_tasks()
        pending_tasks = [t for t in tasks if t.status == "pending"]
        
        if not pending_tasks:
            self.available_tasks_column.controls.append(
                ft.Text("タスクがありません", color="#9e9e9e")
            )
            return
        
        for task in pending_tasks:
            row = ft.Row([
                ft.Text(task.title, size=16, expand=True),
                ft.Text(f"{task.duration}分 + 休憩{task.break_duration}分", size=14, color="#9e9e9e"),
                ft.IconButton(
                    icon="add_circle",
                    tooltip="プレイリストに追加",
                    icon_color="#4caf50",
                    on_click=lambda e, tid=task.id: self.add_to_playlist(tid),
                    disabled=not self.selected_playlist_id
                ),
                ft.IconButton(
                    icon="delete",
                    tooltip="タスクを完全に削除",
                    icon_color="#f44336",
                    on_click=lambda e, tid=task.id: self.delete_task(tid)
                ),
            ])
            self.available_tasks_column.controls.append(row)
    
    def _build(self):
        """画面を構築"""
        self.controls.clear()
        
        title = ft.Text("プレイリスト管理 🎵", size=28, weight=ft.FontWeight.BOLD)
        
        # プレイリスト選択・作成セクション
        playlist_section = ft.Container(
            content=ft.Column([
                ft.Text("プレイリスト", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    self.playlist_dropdown,
                    ft.IconButton(
                        icon="delete",
                        tooltip="プレイリストを削除",
                        icon_color="#f44336",
                        on_click=self.delete_playlist
                    ),
                ]),
                ft.Row([
                    self.playlist_name_field,
                    ft.ElevatedButton(
                        "作成",
                        icon="add",
                        bgcolor="#00bcd4",  # シアンで見やすく
                        color="white",
                        on_click=self.create_playlist
                    ),
                ]),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # プレイリスト内タスク一覧
        playlist_tasks_section = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("📋 プレイリストの内容", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.ElevatedButton(
                        "✨ AI最適化",
                        icon="auto_awesome",
                        bgcolor="#b388ff",  # 明るい紫
                        color="white",
                        on_click=self.show_ai_dialog,
                        tooltip="AIがタスクの順序を最適化します"
                    ),
                ]),
                ft.Divider(),
                self.playlist_tasks_column,
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # タスク作成セクション
        task_create_section = ft.Container(
            content=ft.Column([
                ft.Text("新規タスク作成", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row([
                    self.task_name_field,
                    self.difficulty_dropdown,
                ]),
                ft.Row([
                    self.duration_field,
                    self.break_field,
                ]),
                ft.ElevatedButton(
                    "タスク作成", 
                    icon="add", 
                    bgcolor="#00bcd4",  # シアン
                    color="white",
                    on_click=self.create_task
                ),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 利用可能タスク一覧
        available_tasks_section = ft.Container(
            content=ft.Column([
                ft.Text("📝 利用可能なタスク", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("＋ボタンでプレイリストに追加", size=12, color="#9e9e9e"),
                ft.Divider(),
                self.available_tasks_column,
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        self.controls = [
            title,
            playlist_section,
            playlist_tasks_section,
            task_create_section,
            available_tasks_section,
        ]
    
    def _refresh_ui(self):
        """UI全体を更新"""
        self._load_data()
        self.page.update()
    
    def on_playlist_change(self, e):
        """プレイリスト選択変更"""
        if self.playlist_dropdown.value:
            self.selected_playlist_id = int(self.playlist_dropdown.value)
        else:
            self.selected_playlist_id = None
        
        self._build_playlist_tasks()
        self._build_available_tasks()
        self.page.update()
    
    def create_playlist(self, e):
        """プレイリスト作成"""
        name = self.playlist_name_field.value
        if not name or name.strip() == "":
            self.playlist_name_field.error_text = "名前を入力してください"
            self.playlist_name_field.update()
            return
        
        playlist = Playlist(name=name.strip(), description="")
        playlist_id = self.db.create_playlist(playlist)
        
        self.playlist_name_field.value = ""
        self.playlist_name_field.error_text = ""
        self.selected_playlist_id = playlist_id
        
        self._load_data()
        self.playlist_dropdown.value = str(playlist_id)
        self.page.update()
    
    def delete_playlist(self, e):
        """プレイリスト削除"""
        if not self.selected_playlist_id:
            return
        
        self.db.delete_playlist(self.selected_playlist_id)
        self.selected_playlist_id = None
        self.playlist_dropdown.value = None
        self._refresh_ui()
    
    def add_to_playlist(self, task_id: int):
        """タスクをプレイリストに追加"""
        if not self.selected_playlist_id:
            return
        
        self.db.add_task_to_playlist(self.selected_playlist_id, task_id)
        self._build_playlist_tasks()
        self._build_available_tasks()
        self.page.update()
    
    def remove_from_playlist(self, task_id: int):
        """タスクをプレイリストから削除"""
        if not self.selected_playlist_id:
            return
        
        self.db.remove_task_from_playlist(self.selected_playlist_id, task_id)
        self._build_playlist_tasks()
        self._build_available_tasks()
        self.page.update()
    
    def move_task_up(self, index: int):
        """タスクを上に移動"""
        if not self.selected_playlist_id or index <= 0:
            return
        
        tasks = self.db.get_playlist_tasks(self.selected_playlist_id)
        task_ids = [t.id for t in tasks]
        task_ids[index], task_ids[index - 1] = task_ids[index - 1], task_ids[index]
        
        self.db.reorder_playlist_tasks(self.selected_playlist_id, task_ids)
        self._build_playlist_tasks()
        self.page.update()
    
    def move_task_down(self, index: int):
        """タスクを下に移動"""
        if not self.selected_playlist_id:
            return
        
        tasks = self.db.get_playlist_tasks(self.selected_playlist_id)
        if index >= len(tasks) - 1:
            return
        
        task_ids = [t.id for t in tasks]
        task_ids[index], task_ids[index + 1] = task_ids[index + 1], task_ids[index]
        
        self.db.reorder_playlist_tasks(self.selected_playlist_id, task_ids)
        self._build_playlist_tasks()
        self.page.update()
    
    def create_task(self, e):
        """タスク作成"""
        task_name = self.task_name_field.value
        if not task_name or task_name.strip() == "":
            self.task_name_field.error_text = "タスク名を入力してください"
            self.task_name_field.update()
            return
        
        difficulty = int(self.difficulty_dropdown.value) if self.difficulty_dropdown.value else 2
        
        try:
            duration = int(self.duration_field.value) if self.duration_field.value else 25
            break_duration = int(self.break_field.value) if self.break_field.value else 5
        except ValueError:
            duration = 25
            break_duration = 5
        
        new_task = Task(
            title=task_name.strip(),
            category="",
            difficulty=difficulty,
            duration=duration,
            break_duration=break_duration,
            priority=0,
            status="pending"
        )
        
        self.db.create_task(new_task)
        
        self.task_name_field.value = ""
        self.task_name_field.error_text = ""
        self.duration_field.value = "25"
        self.break_field.value = "5"
        self.difficulty_dropdown.value = "2"
        
        self._refresh_ui()
    
    def delete_task(self, task_id: int):
        """タスクを完全に削除"""
        self.db.delete_task(task_id)
        self._refresh_ui()
    def show_ai_dialog(self, e):
        """AI最適化ダイアログを表示"""
        if not self.selected_playlist_id:
            return
        
        tasks = self.db.get_playlist_tasks(self.selected_playlist_id)
        if len(tasks) < 2:
            snackbar = ft.SnackBar(
                content=ft.Text("最適化には2つ以上のタスクが必要です"),
                action="OK"
            )
            self.page.overlay.append(snackbar)
            snackbar.open = True
            self.page.update()
            return
        
        # 現在の生活設定を取得
        lifestyle = self.db.get_lifestyle_settings()
        
        available_time_field = ft.TextField(
            label="使用可能時間（分）",
            hint_text="例: 120（空欄で全タスク）",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        def apply_balanced(e):
            dialog.open = False
            self.apply_ai_optimization("balanced", None)
        
        def apply_time_limited(e):
            dialog.open = False
            try:
                time_limit = int(available_time_field.value) if available_time_field.value else None
            except ValueError:
                time_limit = None
            self.apply_ai_optimization("priority", time_limit)
        
        def apply_genetic(e):
            dialog.open = False
            self.apply_ai_optimization("genetic", None)
        
        def show_lifestyle_settings(e):
            dialog.open = False
            self.page.update()
            self.show_lifestyle_dialog()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("✨ AI スケジュール最適化"),
            content=ft.Column([
                ft.Text("AIがタスクの順序を最適化します。"),
                ft.Divider(),
                ft.Text("🔄 バランス型", weight=ft.FontWeight.BOLD),
                ft.Text("難しいタスクと簡単なタスクを交互に配置", size=12, color="#9e9e9e"),
                ft.Divider(),
                ft.Text("⏰ 時間制限型", weight=ft.FontWeight.BOLD),
                ft.Text("指定時間内で優先度の高いタスクを選択", size=12, color="#9e9e9e"),
                available_time_field,
                ft.Divider(),
                ft.Text("🧬 遺伝的アルゴリズム（生活最適化）", weight=ft.FontWeight.BOLD),
                ft.Text(f"起床{lifestyle.wake_time} / 就寝{lifestyle.sleep_time} を考慮", size=12, color="#9e9e9e"),
                ft.TextButton("⚙️ 生活設定を変更", on_click=show_lifestyle_settings),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.ElevatedButton("🔄 バランス型", on_click=apply_balanced),
                ft.ElevatedButton("⏰ 時間制限", on_click=apply_time_limited),
                ft.ElevatedButton("🧬 GA最適化", on_click=apply_genetic),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def show_lifestyle_dialog(self):
        """生活設定ダイアログを表示"""
        lifestyle = self.db.get_lifestyle_settings()
        
        wake_field = ft.TextField(label="起床時間", value=lifestyle.wake_time, width=100, hint_text="07:00")
        sleep_field = ft.TextField(label="就寝時間", value=lifestyle.sleep_time, width=100, hint_text="23:00")
        bath_field = ft.TextField(label="入浴時間", value=lifestyle.bath_time, width=100, hint_text="21:00")
        bath_dur_field = ft.TextField(label="入浴（分）", value=str(lifestyle.bath_duration), width=80)
        breakfast_field = ft.TextField(label="朝食時間", value=lifestyle.breakfast_time, width=100)
        lunch_field = ft.TextField(label="昼食時間", value=lifestyle.lunch_time, width=100)
        dinner_field = ft.TextField(label="夕食時間", value=lifestyle.dinner_time, width=100)
        meal_dur_field = ft.TextField(label="食事（分）", value=str(lifestyle.meal_duration), width=80)
        
        def close_dialog(e):
            dialog.open = False
            self.page.update()
        
        def save_settings(e):
            try:
                new_settings = LifestyleSettings(
                    wake_time=wake_field.value,
                    sleep_time=sleep_field.value,
                    bath_time=bath_field.value,
                    bath_duration=int(bath_dur_field.value),
                    breakfast_time=breakfast_field.value,
                    lunch_time=lunch_field.value,
                    dinner_time=dinner_field.value,
                    meal_duration=int(meal_dur_field.value)
                )
                self.db.update_lifestyle_settings(new_settings)
                dialog.open = False
                
                snackbar = ft.SnackBar(content=ft.Text("✅ 生活設定を保存しました！"), action="OK")
                self.page.overlay.append(snackbar)
                snackbar.open = True
                self.page.update()
            except ValueError:
                pass
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("⚙️ 生活時間設定"),
            content=ft.Column([
                ft.Text("遺伝的アルゴリズムはこの設定を考慮してスケジュールを最適化します。"),
                ft.Divider(),
                ft.Row([wake_field, sleep_field]),
                ft.Text("食事", weight=ft.FontWeight.BOLD),
                ft.Row([breakfast_field, lunch_field, dinner_field, meal_dur_field]),
                ft.Text("入浴", weight=ft.FontWeight.BOLD),
                ft.Row([bath_field, bath_dur_field]),
            ], tight=True, spacing=10),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.ElevatedButton("保存", on_click=save_settings),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def apply_ai_optimization(self, mode: str, time_limit: int = None):
        """AI最適化を適用"""
        if not self.selected_playlist_id:
            return
        
        tasks = self.db.get_playlist_tasks(self.selected_playlist_id)
        
        if mode == "balanced":
            optimized = self.optimizer.generate_balanced_schedule(tasks)
        elif mode == "genetic":
            # 遺伝的アルゴリズム
            lifestyle = self.db.get_lifestyle_settings()
            ga_optimizer = GeneticScheduleOptimizer(lifestyle)
            optimized = ga_optimizer.optimize(tasks)
        else:
            if time_limit:
                optimized = self.optimizer.optimize_schedule(tasks, time_limit)
            else:
                optimized = sorted(tasks, key=lambda t: (t.difficulty, t.priority), reverse=True)
        
        optimized_ids = [t.id for t in optimized]
        self.db.reorder_playlist_tasks(self.selected_playlist_id, optimized_ids)
        
        self._build_playlist_tasks()
        self.page.update()
        
        mode_names = {"balanced": "バランス型", "genetic": "遺伝的アルゴリズム", "priority": "優先度"}
        snackbar = ft.SnackBar(
            content=ft.Text(f"🧬 {mode_names.get(mode, mode)}で{len(optimized)}個のタスクを最適化しました！"),
            action="OK"
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
