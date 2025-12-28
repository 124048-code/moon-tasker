"""
タイマー画面（集中モード対応・生活時間連携機能付き）
"""
import flet as ft
from datetime import datetime, timedelta
from ..database import Database
from ..models import Task
from ..logic.timer_logic import TimerController
from ..logic.creature_logic import CreatureSystem
from ..logic.badge_logic import BadgeSystem


class TimerView(ft.Column):
    """タイマー画面"""
    
    def __init__(self, db: Database, page: ft.Page):
        super().__init__()
        self.db = db
        self._page = page
        self.timer = TimerController()
        self.creature_system = CreatureSystem(db)
        self.spacing = 20
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        
        # 集中モードフラグ
        self.is_focus_mode = False
        self.stop_warning_count = 0  # 中止警告カウント
        
        # スケジュール関連
        self.schedule_items = []
        self.estimated_end_time = None
        
        # UIコンポーネント
        self.timer_display = ft.Text("00:00", size=96, weight=ft.FontWeight.BOLD, font_family="Consolas")
        self.status_text = ft.Text("プレイリストを選択してください", size=20, color="#9e9e9e")
        self.progress_text = ft.Text("", size=18, color="#64b5f6")
        self.next_task_text = ft.Text("", size=16, color="#9e9e9e")
        self.end_time_text = ft.Text("", size=16, color="#ffc107")
        self.notification_text = ft.Text("", size=14, color="#ff9800")
        
        self.playlist_dropdown = ft.Dropdown(
            label="プレイリストを選択",
            width=300,
            options=[],
            on_change=self.on_playlist_select
        )
        
        self.start_button = ft.ElevatedButton(
            "開始", 
            on_click=self.start_timer, 
            icon="play_arrow",
            style=ft.ButtonStyle(
                bgcolor="#4caf50",
                color="white",
            )
        )
        
        # スケジュール表示用（通常時のみ）
        self.schedule_column = ft.Column(spacing=5)
        
        # タイマーコールバック設定
        self.timer.on_tick = self.on_timer_tick
        self.timer.on_complete = self.on_task_complete
        self.timer.on_break_start = self.on_break_start
        self.timer.on_task_start = self.on_task_start
        self.timer.on_resume = self.on_resume_callback
        self.timer.on_playlist_complete = self.on_playlist_complete
        self.timer.on_next_task_start = self.on_next_task_start
        
        self._load_playlists_data()
        self._build()
        
        # クイックスタートモードのチェック
        if hasattr(page, 'quick_start_mode') and page.quick_start_mode:
            page.quick_start_mode = False  # フラグをリセット
            self._start_quick_mode()
    
    def _build(self):
        """画面を構築"""
        self.controls.clear()
        
        if self.is_focus_mode:
            self._build_focus_mode()
        else:
            self._build_normal_mode()
    
    def _build_focus_mode(self):
        """集中モードの画面を構築（タイマーのみ表示）"""
        # 大きなタイマーカード
        timer_card = ft.Container(
            content=ft.Column([
                self.progress_text,
                ft.Container(height=20),
                self.timer_display,
                ft.Container(height=10),
                self.status_text,
                ft.Container(height=20),
                self.next_task_text,
                self.end_time_text,
                self.notification_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e3a5f",
            border_radius=15,
            padding=60,
            alignment=ft.alignment.center,
            expand=True
        )
        
        # 目立たないオプションメニュー（右下の小さなアイコン）
        menu_button = ft.PopupMenuButton(
            icon="more_horiz",
            icon_size=18,
            icon_color="#5a5a5a",
            tooltip="オプション",
            items=[
                ft.PopupMenuItem(
                    text="一時停止 / 再開",
                    icon="pause",
                    on_click=self.pause_timer
                ),
                ft.PopupMenuItem(),
                ft.PopupMenuItem(
                    text="中止...",
                    icon="stop",
                    on_click=self.confirm_stop_timer
                ),
            ],
        )
        
        menu_row = ft.Row([
            ft.Container(expand=True),
            menu_button,
        ])
        
        self.controls = [
            timer_card,
            menu_row,
        ]
    
    def _build_normal_mode(self):
        """通常モードの画面を構築"""
        title = ft.Text("タイマー ⏱️", size=28, weight=ft.FontWeight.BOLD)
        
        # プレイリストがあるかチェック
        playlists = self.db.get_all_playlists()
        has_playlists = len(playlists) > 0
        
        # タイマー表示カード
        timer_card = ft.Container(
            content=ft.Column([
                self.progress_text,
                self.timer_display,
                self.status_text,
                self.next_task_text,
                self.end_time_text,
                self.notification_text,
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=40,
            alignment=ft.alignment.center
        )
        
        # プレイリストがない場合の案内カード
        if not has_playlists:
            guide_card = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.HELP_OUTLINE, size=40, color="#ffc107"),
                    ft.Text("プレイリストがありません", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("まずプレイリストを作成して、タスクを追加しましょう！", size=14, color="#9e9e9e"),
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "📝 プレイリストを作成する",
                        bgcolor="#ffc107",
                        color="black",
                        on_click=self._go_to_playlist_view
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                bgcolor="#3d3d1f",
                border=ft.border.all(2, "#ffc107"),
                border_radius=15,
                padding=25
            )
            
            self.controls = [title, timer_card, guide_card]
            return
        
        # プレイリスト選択
        playlist_selection = ft.Container(
            content=ft.Column([
                ft.Text("プレイリスト選択", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("選択したプレイリストのタスクを順番に実行します", size=12, color="#9e9e9e"),
                self.playlist_dropdown,
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 今日のスケジュール表
        schedule_section = ft.Container(
            content=ft.Column([
                ft.Text("📅 今日のスケジュール", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                self.schedule_column,
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # メインボタン
        main_controls = ft.Row([
            self.start_button,
        ], alignment=ft.MainAxisAlignment.CENTER)
        
        self.controls = [
            title,
            timer_card,
            playlist_selection,
            schedule_section,
            main_controls,
        ]
    
    def _load_playlists_data(self):
        """プレイリスト一覧を読み込み"""
        playlists = self.db.get_all_playlists()
        self.playlist_dropdown.options = [
            ft.dropdown.Option(key=str(p.id), text=p.name)
            for p in playlists
        ]
    
    def _load_playlists(self):
        """プレイリスト一覧を読み込み（page追加後用）"""
        self._load_playlists_data()
        self.playlist_dropdown.update()
    
    def _start_quick_mode(self):
        """クイックスタートモードを開始（25分集中タイマー）"""
        # 仮のタスクを作成して即座に開始
        from ..models import Task
        quick_task = Task(
            id=-1,  # 仮ID
            title="クイック集中タイム",
            duration=25,
            break_duration=5,
            difficulty=3
        )
        
        # 集中モードに切り替え
        self.is_focus_mode = True
        self._build_focus_mode()
        
        # タイマー開始
        self.timer.start_single_task(quick_task)
        self.timer.on_complete = self._on_quick_task_complete
        self.status_text.value = "🚀 クイック集中タイム！"
        self._page.update()
    
    def _on_quick_task_complete(self, task):
        """クイックタスク完了コールバック"""
        self.db.log_activity(-1, "completed")  # アクティビティログに記録
        self.creature_system.on_task_completed(task.difficulty)
        
        # プレゼントチェック
        if self.creature_system.last_present:
            if not hasattr(self, '_pending_presents'):
                self._pending_presents = []
            self._pending_presents.append(self.creature_system.last_present)
        
        # 進化チェック
        self._check_evolution_after_task()
        
        # 完了処理
        self._exit_focus_mode()
        self._page.run_task(self._show_completion_dialog_async, 1)
    
    def _go_to_playlist_view(self, e):
        """プレイリスト管理画面に移動"""
        if hasattr(self._page, 'navigation_rail'):
            self._page.navigation_rail.selected_index = 2
        if hasattr(self._page, 'change_view'):
            self._page.change_view(2)
    
    def on_playlist_select(self, e):
        """プレイリスト選択時にスケジュール表を生成"""
        if not self.playlist_dropdown.value:
            self.schedule_column.controls.clear()
            self.schedule_column.controls.append(ft.Text("プレイリストを選択してください", color="#9e9e9e"))
            self._page.update()
            return
        
        playlist_id = int(self.playlist_dropdown.value)
        tasks = self.db.get_playlist_tasks(playlist_id)
        lifestyle = self.db.get_lifestyle_settings()
        
        self._generate_schedule(tasks, lifestyle)
        self._page.update()
    
    def _generate_schedule(self, tasks, lifestyle):
        """今日のスケジュールを生成"""
        self.schedule_column.controls.clear()
        self.schedule_items = []
        
        if not tasks:
            self.schedule_column.controls.append(ft.Text("タスクがありません", color="#9e9e9e"))
            return
        
        current_time = datetime.now()
        
        def parse_time(time_str):
            t = datetime.strptime(time_str, "%H:%M")
            return current_time.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        
        lunch = parse_time(lifestyle.lunch_time)
        dinner = parse_time(lifestyle.dinner_time)
        bath = parse_time(lifestyle.bath_time)
        sleep = parse_time(lifestyle.sleep_time)
        
        # 日の開始時間（4:00）を考慮した就寝時間の補正
        # 就寝時間が4:00より前（例: 0:00, 1:00など）の場合は翌日として扱う
        day_start_hour = 4
        if sleep.hour < day_start_hour:
            sleep = sleep + timedelta(days=1)
        
        schedule = []
        time_cursor = current_time
        
        for task in tasks:
            task_end = time_cursor + timedelta(minutes=task.duration + task.break_duration)
            
            if time_cursor < lunch <= task_end:
                schedule.append({
                    "type": "meal", "name": "🍴 昼食",
                    "start": lunch, "duration": lifestyle.meal_duration
                })
                time_cursor = lunch + timedelta(minutes=lifestyle.meal_duration)
            
            if time_cursor < dinner <= task_end:
                schedule.append({
                    "type": "meal", "name": "🍴 夕食",
                    "start": dinner, "duration": lifestyle.meal_duration
                })
                time_cursor = dinner + timedelta(minutes=lifestyle.meal_duration)
            
            if time_cursor < bath <= task_end:
                schedule.append({
                    "type": "bath", "name": "🛁 入浴",
                    "start": bath, "duration": lifestyle.bath_duration
                })
                time_cursor = bath + timedelta(minutes=lifestyle.bath_duration)
            
            schedule.append({
                "type": "task", "name": f"📝 {task.title}",
                "start": time_cursor, "duration": task.duration,
                "break_duration": task.break_duration
            })
            time_cursor += timedelta(minutes=task.duration + task.break_duration)
        
        self.estimated_end_time = time_cursor
        
        for item in schedule:
            start_str = item["start"].strftime("%H:%M")
            end_time = item["start"] + timedelta(minutes=item["duration"])
            if item["type"] == "task" and item.get("break_duration", 0) > 0:
                end_time += timedelta(minutes=item["break_duration"])
            end_str = end_time.strftime("%H:%M")
            
            if item["type"] == "meal":
                color = "#ffeb3b"
            elif item["type"] == "bath":
                color = "#64b5f6"
            else:
                color = "#ffffff"
            
            row = ft.Row([
                ft.Text(f"{start_str}", size=12, width=50, color="#9e9e9e"),
                ft.Text(item["name"], size=14, color=color, expand=True),
                ft.Text(f"~{end_str}", size=12, color="#9e9e9e"),
            ])
            self.schedule_column.controls.append(row)
        
        # 予想終了時刻を表示（就寝時刻警告は削除）
        info = ft.Text(
            f"✅ 予想終了: {self.estimated_end_time.strftime('%H:%M')}",
            color="#4caf50", size=14
        )
        self.schedule_column.controls.append(info)
        
        self.schedule_items = schedule

    def start_timer(self, e):
        """タイマー開始"""
        if not self.playlist_dropdown.value:
            return
        
        playlist_id = int(self.playlist_dropdown.value)
        tasks = self.db.get_playlist_tasks(playlist_id)
        
        if not tasks:
            self.status_text.value = "プレイリストにタスクがありません"
            self._page.update()
            return
        
        # 集中モードに切り替え
        self.is_focus_mode = True
        self.stop_warning_count = 0
        
        # ナビゲーションを非表示にする
        if hasattr(self._page, 'navigation_rail'):
            self._page.navigation_rail.visible = False
        
        # 進捗を表示
        self.progress_text.value = f"1 / {len(tasks)}"
        
        # 予想終了時刻を表示
        if self.estimated_end_time:
            self.end_time_text.value = f"⏰ 予想終了: {self.estimated_end_time.strftime('%H:%M')}"
        
        # 次のタスクをプレビュー
        if len(tasks) > 1:
            self.next_task_text.value = f"次: {tasks[1].title}"
        else:
            self.next_task_text.value = ""
        
        # UIを再構築
        self._build()
        self._page.update()
        
        # プレイリスト連続タイマー開始
        self._page.run_task(self.timer.start_playlist, tasks)
    
    def pause_timer(self, e):
        """タイマー一時停止/再開"""
        if self.timer.is_running:
            self.timer.pause()
            self.status_text.value = "⏸️ 一時停止中..."
        else:
            self.timer.resume()
        self._page.update()
    
    def on_resume_callback(self):
        """タイマー再開コールバック"""
        if self.timer.current_task:
            if self.timer.is_break:
                self.status_text.value = f"休憩中 ☕ ({self.timer.current_task.break_duration}分)"
            else:
                self.status_text.value = f"作業中: {self.timer.current_task.title}"
        self._page.run_task(self.timer.resume_countdown)
        self._page.update()
    
    def confirm_stop_timer(self, e):
        """タイマー中止確認ダイアログ（2段階警告）"""
        self.stop_warning_count += 1
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        def proceed_to_second_warning(e):
            dialog.open = False
            self._page.update()
            # 少し遅延して第2警告を表示
            self._page.run_task(self._show_second_warning)
        
        def actually_stop(e):
            dialog.open = False
            self.stop_timer(None)
            self._page.update()
        
        if self.stop_warning_count == 1:
            # 第1警告
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("⚠️ 本当に中止しますか？"),
                content=ft.Column([
                    ft.Text(
                        "中止すると、残りのタスクの進捗は記録されません。",
                        size=14
                    ),
                    ft.Container(height=10),
                    ft.Text(
                        "🔥 ここまで頑張ってきたのに、もったいないですよ！\n"
                        "もう少しだけ頑張ってみませんか？",
                        size=14, color="#ffc107"
                    ),
                ], tight=True),
                actions=[
                    ft.TextButton("続ける 💪", on_click=close_dialog),
                    ft.TextButton("それでも中止する", on_click=proceed_to_second_warning),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        else:
            # 第2警告（最終確認）
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("⛔ 最終確認"),
                content=ft.Column([
                    ft.Text(
                        "本当に中止しますか？\n\n"
                        "📉 途中で諦めると、次も諦めやすくなります。\n"
                        "🌙 目標サイクルの進捗にも影響します。\n"
                        "😢 生命体も悲しみます...",
                        size=14
                    ),
                    ft.Container(height=10),
                    ft.Container(
                        content=ft.Text(
                            "💡 あと少しです。最後まで頑張りましょう！",
                            size=14, weight=ft.FontWeight.BOLD
                        ),
                        bgcolor="#263238",
                        padding=15,
                        border_radius=5
                    ),
                ], tight=True),
                actions=[
                    ft.ElevatedButton(
                        "続ける！ 🔥",
                        bgcolor="#4caf50",
                        color="white",
                        on_click=close_dialog
                    ),
                    ft.TextButton("中止する", on_click=actually_stop),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()
    
    async def _show_second_warning(self):
        """第2警告を表示"""
        import asyncio
        await asyncio.sleep(0.3)
        self.confirm_stop_timer(None)
    
    def stop_timer(self, e):
        """タイマー停止"""
        self.timer.stop()
        self._exit_focus_mode()
        self.status_text.value = "中止しました"
        self._page.update()
    
    def _exit_focus_mode(self):
        """集中モードを終了"""
        self.is_focus_mode = False
        self.stop_warning_count = 0
        
        # ナビゲーションを再表示
        if hasattr(self._page, 'navigation_rail'):
            self._page.navigation_rail.visible = True
        
        self._reset_ui()
        self._build()
    
    def _reset_ui(self):
        """UIをリセット"""
        self.timer_display.value = "00:00"
        self.progress_text.value = ""
        self.next_task_text.value = ""
        self.end_time_text.value = ""
        self.notification_text.value = ""
        self.start_button.disabled = False
        self.playlist_dropdown.disabled = False
    
    def _check_lifestyle_notifications(self):
        """生活時間通知をチェック"""
        lifestyle = self.db.get_lifestyle_settings()
        now = datetime.now()
        
        def parse_time(time_str):
            t = datetime.strptime(time_str, "%H:%M")
            return now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        
        events = [
            (parse_time(lifestyle.lunch_time), "🍴 昼食の時間が近づいています！"),
            (parse_time(lifestyle.dinner_time), "🍴 夕食の時間が近づいています！"),
            (parse_time(lifestyle.bath_time), "🛁 入浴の時間が近づいています！"),
            (parse_time(lifestyle.sleep_time), "😴 就寝の時間が近づいています！"),
        ]
        
        for event_time, message in events:
            time_until = (event_time - now).total_seconds() / 60
            if 0 < time_until <= 5:
                self.notification_text.value = message
                return
        
        self.notification_text.value = ""
    
    def on_timer_tick(self, remaining_seconds: int, is_break: bool):
        """タイマー更新コールバック"""
        self.timer_display.value = self.timer.get_formatted_time()
        self._check_lifestyle_notifications()
        self._page.update()
    
    def on_task_start(self, task: Task):
        """タスク開始コールバック"""
        current, total = self.timer.get_progress()
        self.progress_text.value = f"{current} / {total}"
        self.status_text.value = f"作業中: {task.title}"
        self.db.update_task_status(task.id, "in_progress")
        
        next_task = self.timer.get_next_task()
        if next_task:
            self.next_task_text.value = f"次: {next_task.title}"
        else:
            self.next_task_text.value = "🎯 最後のタスクです！"
        
        self._page.update()
    
    def on_break_start(self, task: Task):
        """休憩開始コールバック"""
        self.status_text.value = f"休憩中 ☕ ({task.break_duration}分)"
        self._page.update()
    
    def on_task_complete(self, task: Task):
        """個別タスク完了コールバック"""
        self.db.update_task_status(task.id, "completed")
        self.db.log_activity(task.id, "completed")  # アクティビティログに記録
        self.creature_system.on_task_completed(task.difficulty)
        
        # サイクルに紐付けられていれば進捗を更新
        cycle_id = self.db.is_task_in_active_cycle(task.id)
        if cycle_id:
            self.db.complete_cycle_task(cycle_id, task.id)
        
        # プレゼントがあれば保存
        if self.creature_system.last_present:
            if not hasattr(self, '_pending_presents'):
                self._pending_presents = []
            self._pending_presents.append(self.creature_system.last_present)
        
        # 進化チェック
        self._check_evolution_after_task()
    
    def on_next_task_start(self, task: Task, index: int, total: int):
        """次のタスク開始コールバック"""
        self.progress_text.value = f"{index + 1} / {total}"
        self._page.update()
    
    def on_playlist_complete(self):
        """プレイリスト全完了コールバック"""
        # 完了タスク数を先に取得（_exit_focus_modeでクリアされる前に）
        completed_count = len(self.timer.playlist_tasks) if self.timer.playlist_tasks else 0
        self._exit_focus_mode()
        # 非同期でダイアログ表示（ページ更新タイミングを確保）
        self._page.run_task(self._show_completion_dialog_async, completed_count)
    
    async def _show_completion_dialog_async(self, completed_count: int):
        """達成ダイアログを非同期で表示"""
        import asyncio
        await asyncio.sleep(0.1)  # ページ更新を待つ
        self._show_completion_dialog(completed_count)
    
    def _show_completion_dialog(self, completed_count: int):
        """達成ダイアログを表示"""
        def go_home(e):
            self._page.close(dialog)
            # ホーム画面に戻る
            if hasattr(self._page, 'navigation_rail'):
                self._page.navigation_rail.selected_index = 0
            if hasattr(self._page, 'change_view'):
                self._page.change_view(0)
            self._page.update()
            # プレゼント演出
            self._show_pending_presents()
            # 進化演出
            self._show_pending_evolutions()
        
        # ランダムな励ましメッセージ
        import random
        encouragements = [
            ("素晴らしい集中力でした！\nお疲れ様でした 💪", "#81c784"),
            ("自分を誇りに思ってください！\n今日も一歩前進です 🌟", "#64b5f6"),
            ("難しいことを成し遂げましたね！\nあなたは強い ✨", "#f06292"),
            ("継続は力なり！\nこの調子で頑張りましょう 🔥", "#ff9800"),
            ("未来の自分に感謝されますよ！\n素敵な時間でした 🌙", "#ce93d8"),
            ("やり遂げた自分を褒めてあげて！\nよく頑張りました 🎊", "#fff176"),
        ]
        message, color = random.choice(encouragements)
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Text("🎉", size=40),
                ft.Text("達成しました！", size=24, weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.CENTER),
            content=ft.Column([
                ft.Container(height=20),
                ft.Text(
                    f"✨ {completed_count}個のタスクを完了しました！",
                    size=18,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=10),
                ft.Text(
                    message,
                    size=16,
                    color=color,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True),
            actions=[
                ft.ElevatedButton(
                    "ホームに戻る",
                    icon="home",
                    bgcolor="#4caf50",
                    color="white",
                    on_click=go_home
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )
        
        self._page.open(dialog)
        self._load_playlists()
        self._page.update()
    
    
    def _check_evolution_after_task(self):
        """タスク完了後に進化をチェック"""
        creature = self.creature_system.get_creature()
        if not creature:
            return
        
        # タスク完了前の進化段階を記録
        if not hasattr(self, '_last_evolution_stage'):
            self._last_evolution_stage = creature.evolution_stage
        
        # 現在の進化段階と比較
        if creature.evolution_stage > self._last_evolution_stage:
            # 進化した！
            if not hasattr(self, '_pending_evolutions'):
                self._pending_evolutions = []
            self._pending_evolutions.append({
                'from_stage': self._last_evolution_stage,
                'to_stage': creature.evolution_stage,
                'creature_name': creature.name
            })
            self._last_evolution_stage = creature.evolution_stage
    
    def _show_pending_evolutions(self):
        """保留中の進化演出を表示"""
        if not hasattr(self, '_pending_evolutions') or not self._pending_evolutions:
            return
        
        evolutions = self._pending_evolutions
        self._pending_evolutions = []
        
        if evolutions:
            self._show_evolution_animation(evolutions)
    
    def _show_evolution_animation(self, evolutions):
        """進化演出ダイアログ"""
        if not evolutions:
            return
        
        evolution = evolutions[0]
        from_stage = evolution['from_stage']
        to_stage = evolution['to_stage']
        creature_name = evolution['creature_name']
        
        # 進化段階の情報
        stage_info = {
            1: ("🥚", "たまご"),
            2: ("⭐", "ほしのあかちゃん"),
            3: ("🌟", "ほし"),
            4: ("🐰", "こうさぎ"),
            5: ("🌙", "つき"),
        }
        
        from_emoji, from_name = stage_info.get(from_stage, ("🥚", "たまご"))
        to_emoji, to_name = stage_info.get(to_stage, ("⭐", "ほしのあかちゃん"))
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
            # 複数進化の場合は次を表示
            if len(evolutions) > 1:
                self._show_evolution_animation(evolutions[1:])
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("✨ 進化しました！", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            content=ft.Container(
                content=ft.Column([
                    ft.Container(height=10),
                    ft.Row([
                        ft.Column([
                            ft.Text(from_emoji, size=50),
                            ft.Text(from_name, size=12, color="#9e9e9e"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        ft.Text("→", size=30, color="#ffc107"),
                        ft.Column([
                            ft.Text(to_emoji, size=60),
                            ft.Text(to_name, size=14, weight=ft.FontWeight.BOLD, color="#ffc107"),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                    ft.Container(height=15),
                    ft.Text(f"🎉 {creature_name}が進化しました！", size=16, text_align=ft.TextAlign.CENTER),
                    ft.Text("これからも大切に育ててね", size=14, color="#9e9e9e", text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=280,
            ),
            actions=[
                ft.ElevatedButton(
                    "やったー！🎉",
                    bgcolor="#ffc107",
                    color="black",
                    on_click=close_dialog
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self._page.open(dialog)
    
    def _show_badge_unlock_animation(self, badges):
        """称号獲得演出ダイアログ"""
        if not badges:
            return
        
        badge = badges[0]
        badge_system = BadgeSystem(self.db)
        rarity = badge_system.get_rarity_from_condition(badge)
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
                self._show_badge_unlock_animation(badges[1:])
        
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
    
    def _show_pending_presents(self):
        """保留中のプレゼント演出を表示"""
        if not hasattr(self, '_pending_presents') or not self._pending_presents:
            return
        
        presents = self._pending_presents
        self._pending_presents = []
        
        if presents:
            self._show_present_dialog(presents)
    
    def _show_present_dialog(self, presents):
        """プレゼント演出ダイアログ"""
        if not presents:
            return
        
        present = presents[0]
        name, emoji, desc = present
        
        creature = self.creature_system.get_creature()
        creature_name = creature.name if creature else "生命体"
        
        # プレゼントを図鑑に保存
        if creature:
            self.db.add_present(creature.id, name, emoji, desc)
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
            # 複数プレゼントの場合は次を表示
            if len(presents) > 1:
                self._show_present_dialog(presents[1:])
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"🎁 {creature_name}からのプレゼント", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Container(height=10),
                    ft.Text("(◕‿◕)", size=50, text_align=ft.TextAlign.CENTER),
                    ft.Text("…", size=14, color="#9e9e9e", text_align=ft.TextAlign.CENTER),
                    ft.Container(height=15),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(emoji, size=40, text_align=ft.TextAlign.CENTER),
                            ft.Text(name, size=18, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                            ft.Text(desc, size=12, color="#9e9e9e", text_align=ft.TextAlign.CENTER),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        bgcolor="#263238",
                        border_radius=10,
                        padding=20
                    ),
                    ft.Container(height=10),
                    ft.Text("（無言で差し出してくれた）", size=12, color="#9e9e9e", italic=True, 
                           text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=260,
            ),
            actions=[
                ft.ElevatedButton(
                    "ありがとう 💖",
                    bgcolor="#f06292",
                    color="white",
                    on_click=close_dialog
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self._page.open(dialog)
