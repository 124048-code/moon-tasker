"""
目標サイクル画面（タスク紐付け・タイマー連携対応）
"""
import flet as ft
from datetime import datetime, timedelta
from ..database import Database
from ..logic.moon_cycle import MoonCycleCalculator
from ..models import MoonCycle, Task


class MoonCycleView(ft.Column):
    """目標サイクル管理画面"""
    
    def __init__(self, db: Database, page: ft.Page):
        super().__init__()
        self.db = db
        self._page = page
        self.moon_calc = MoonCycleCalculator()
        self.spacing = 20
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        
        # 現在のサイクル情報
        self.current_cycle = None
        self.goal_field = None
        self.review_field = None
        
        self._load_active_cycle()
        self._build()
    
    def _load_active_cycle(self):
        """アクティブな目標サイクルを読み込み"""
        self.current_cycle = self.db.get_active_moon_cycle()
    
    def _build(self):
        """画面を構築"""
        self.controls.clear()
        
        title = ft.Text("目標サイクル 🎯", size=28, weight=ft.FontWeight.BOLD)
        
        # 月の情報（参考表示）
        moon_emoji = self.moon_calc.get_moon_emoji()
        moon_phase_name = self.moon_calc.get_moon_phase_name()
        
        moon_info = ft.Container(
            content=ft.Row([
                ft.Text(moon_emoji, size=24),
                ft.Text(f"現在の月: {moon_phase_name}", size=14, color="#9e9e9e"),
            ], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=10
        )
        
        # アクティブサイクルがある場合
        if self.current_cycle:
            content = self._build_active_cycle_view()
        else:
            content = self._build_new_cycle_form()
        
        self.controls = [
            title,
            moon_info,
            ft.Divider(),
            content,
        ]
    
    def _build_active_cycle_view(self):
        """アクティブサイクルの表示"""
        cycle = self.current_cycle
        
        # サイクルに紐付けられたタスク
        cycle_tasks = self.db.get_cycle_tasks(cycle.id)
        completed_count = sum(1 for t in cycle_tasks if getattr(t, '_cycle_completed', False))
        total_count = len(cycle_tasks)
        
        # 進捗計算（紐付けられたタスクベース）
        if total_count > 0:
            progress = completed_count / total_count
        else:
            progress = 0
        progress_percent = min(progress * 100, 100)
        
        # 進捗判定
        if progress >= 1.0:
            progress_color = "#81c784"
            progress_text = "目標達成！ 🎉"
        elif progress >= 0.5:
            progress_color = "#64b5f6"
            progress_text = "順調に進行中"
        else:
            progress_color = "#ffb74d"
            progress_text = "頑張りましょう"
        
        # 進捗カード
        progress_card = ft.Container(
            content=ft.Column([
                ft.Text("進捗状況", size=20, weight=ft.FontWeight.BOLD),
                ft.Text(f"{cycle.cycle_start} ～ {cycle.cycle_end}", size=14, color="#9e9e9e"),
                ft.Divider(),
                ft.Row([
                    ft.Text(f"{completed_count}", size=48, weight=ft.FontWeight.BOLD, color=progress_color),
                    ft.Text(f"/ {total_count} タスク", size=20, color="#9e9e9e"),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.ProgressBar(
                    value=min(progress, 1.0),
                    color=progress_color,
                    bgcolor="#424242"
                ),
                ft.Text(f"{progress_percent:.1f}% - {progress_text}", size=16, color=progress_color),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 紐付けられたタスク一覧
        task_items = []
        for task in cycle_tasks:
            is_done = getattr(task, '_cycle_completed', False)
            task_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Checkbox(value=is_done, disabled=True),
                        ft.Text(
                            task.title,
                            size=14,
                            color="#81c784" if is_done else "white",
                            style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if is_done else None
                        ),
                        ft.Text(f"({task.duration}分)", size=12, color="#9e9e9e"),
                    ]),
                    bgcolor="#263238" if not is_done else "#1b5e20",
                    border_radius=5,
                    padding=10
                )
            )
        
        tasks_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("設定タスク", size=18, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon="add",
                        tooltip="タスクを追加",
                        on_click=self._show_add_task_dialog
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                *(task_items if task_items else [ft.Text("タスクが設定されていません", size=14, color="#9e9e9e")]),
                ft.Divider(),
                ft.ElevatedButton(
                    "タイマーにセット",
                    icon="timer",
                    bgcolor="#ff9800",
                    color="white",
                    on_click=self._set_to_timer,
                    disabled=len([t for t in cycle_tasks if not getattr(t, '_cycle_completed', False)]) == 0
                ),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 目標内容カード（Plan）
        self.goal_field = ft.TextField(
            label="目標の説明（Plan）",
            multiline=True,
            min_lines=2,
            max_lines=4,
            value=cycle.goal
        )
        
        # 振り返りメモ（互換性維持）
        self.review_field = ft.TextField(
            label="振り返りメモ",
            multiline=True,
            min_lines=2,
            max_lines=4,
            value=cycle.review
        )
        
        # Check フェーズ: 自己評価
        self.rating_slider = ft.Slider(
            min=1,
            max=5,
            divisions=4,
            label="{value}",
            value=cycle.self_rating if cycle.self_rating > 0 else 3
        )
        
        rating_labels = ft.Row([
            ft.Text("1: 未達成", size=10, color="#f44336"),
            ft.Container(expand=True),
            ft.Text("3: まあまあ", size=10, color="#ffeb3b"),
            ft.Container(expand=True),
            ft.Text("5: 達成！", size=10, color="#4caf50"),
        ])
        
        self.good_points_field = ft.TextField(
            label="✅ うまくいったこと",
            multiline=True,
            min_lines=2,
            max_lines=3,
            value=cycle.good_points,
            hint_text="今回のサイクルで成功したこと..."
        )
        
        self.improvement_field = ft.TextField(
            label="📝 改善が必要なこと",
            multiline=True,
            min_lines=2,
            max_lines=3,
            value=cycle.improvement_points,
            hint_text="次回に向けて改善したいこと..."
        )
        
        # Act フェーズ: 次のアクション
        self.next_actions_field = ft.TextField(
            label="🎯 次のサイクルへのアクション（Act）",
            multiline=True,
            min_lines=2,
            max_lines=3,
            value=cycle.next_actions,
            hint_text="次回に実践する具体的な改善策..."
        )
        
        self.save_status = ft.Text("", size=12, color="#81c784")
        
        # 前サイクルからの引き継ぎ表示
        inherited_section = None
        if cycle.parent_cycle_id:
            all_cycles = self.db.get_all_moon_cycles()
            parent = next((c for c in all_cycles if c.id == cycle.parent_cycle_id), None)
            if parent and parent.next_actions:
                inherited_section = ft.Container(
                    content=ft.Column([
                        ft.Text("📋 前サイクルからの引き継ぎ", size=14, weight=ft.FontWeight.BOLD, color="#64b5f6"),
                        ft.Text(parent.next_actions, size=12, color="#9e9e9e"),
                    ]),
                    bgcolor="#263238",
                    border_radius=5,
                    padding=10
                )
        
        # シンプルな目標カード（Check/Actは完了時に入力）
        goal_card = ft.Container(
            content=ft.Column([
                ft.Text("📋 目標（Plan）", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                *([] if not inherited_section else [inherited_section]),
                self.goal_field,
                ft.Divider(),
                ft.Text("💭 振り返りメモ", size=14, weight=ft.FontWeight.BOLD, color="#9e9e9e"),
                ft.Text("※ Check/Actはサイクル完了時に入力", size=12, color="#757575"),
                self.review_field,
                ft.Row([
                    ft.ElevatedButton("保存", icon="save", on_click=self._save_cycle),
                    self.save_status
                ]),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 操作カード
        action_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.ElevatedButton(
                        "サイクル完了",
                        icon="check_circle",
                        bgcolor="#2196f3",
                        color="white",
                        on_click=self._complete_cycle
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                ft.TextButton(
                    "このサイクルを削除",
                    icon="delete",
                    icon_color="#f44336",
                    on_click=self._confirm_delete_cycle
                ),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        return ft.Column([
            progress_card,
            tasks_card,
            goal_card,
            action_card,
        ], spacing=20)
    
    def _build_new_cycle_form(self):
        """新規サイクル作成フォーム"""
        today = datetime.now()
        default_end = today + timedelta(days=7)
        
        self.start_date_text = ft.Text(today.strftime("%Y-%m-%d"), size=16)
        self.end_date_text = ft.Text(default_end.strftime("%Y-%m-%d"), size=16)
        self.start_date_value = today.strftime("%Y-%m-%d")
        self.end_date_value = default_end.strftime("%Y-%m-%d")
        
        self.goal_field = ft.TextField(
            label="目標の説明",
            multiline=True,
            min_lines=2,
            max_lines=4,
            hint_text="この期間で達成したい目標を入力..."
        )
        
        # 期間選択カード
        period_card = ft.Container(
            content=ft.Column([
                ft.Text("新しい目標サイクルを作成", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("期間設定（最低3日）", size=16, color="#9e9e9e"),
                ft.Row([
                    ft.Column([
                        ft.Text("開始日", size=12, color="#9e9e9e"),
                        ft.Container(
                            content=ft.Row([
                                self.start_date_text,
                                ft.IconButton(
                                    icon="calendar_today",
                                    on_click=lambda e: self._pick_date("start")
                                )
                            ]),
                            bgcolor="#263238",
                            border_radius=5,
                            padding=10
                        )
                    ]),
                    ft.Text("～", size=20),
                    ft.Column([
                        ft.Text("終了日", size=12, color="#9e9e9e"),
                        ft.Container(
                            content=ft.Row([
                                self.end_date_text,
                                ft.IconButton(
                                    icon="calendar_today",
                                    on_click=lambda e: self._pick_date("end")
                                )
                            ]),
                            bgcolor="#263238",
                            border_radius=5,
                            padding=10
                        )
                    ]),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Divider(),
                self.goal_field,
                ft.Text("※ サイクル作成後にタスクを追加できます", size=12, color="#9e9e9e"),
                ft.ElevatedButton(
                    "サイクルを開始",
                    icon="play_arrow",
                    bgcolor="#4caf50",
                    color="white",
                    on_click=self._create_cycle
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 過去のサイクル一覧（詳細展開・引き継ぎ機能付き）
        past_cycles = self.db.get_all_moon_cycles()
        completed_cycles = [c for c in past_cycles if c.status == "completed"]
        
        history_items = []
        for cycle in completed_cycles[:5]:
            # 自己評価の星表示
            rating_stars = "★" * cycle.self_rating + "☆" * (5 - cycle.self_rating) if cycle.self_rating > 0 else "未評価"
            
            # 達成率
            if cycle.target_task_count > 0:
                rate = cycle.completed_task_count / cycle.target_task_count * 100
            else:
                rate = 0
            
            # 詳細パネル（展開可能）
            detail_panel = ft.ExpansionTile(
                title=ft.Text(f"{cycle.cycle_start} ～ {cycle.cycle_end}", size=14),
                subtitle=ft.Text(f"{cycle.completed_task_count}/{cycle.target_task_count} ({rate:.0f}%) {rating_stars}", size=12, color="#9e9e9e"),
                initially_expanded=False,
                controls=[
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"📋 目標: {cycle.goal[:50]}..." if len(cycle.goal) > 50 else f"📋 目標: {cycle.goal or '（なし）'}", size=12, color="#9e9e9e"),
                            ft.Text(f"✅ 良かった点: {cycle.good_points[:30]}..." if len(cycle.good_points) > 30 else f"✅ 良かった点: {cycle.good_points or '（なし）'}", size=12, color="#81c784") if cycle.good_points else ft.Container(),
                            ft.Text(f"📝 改善点: {cycle.improvement_points[:30]}..." if len(cycle.improvement_points) > 30 else f"📝 改善点: {cycle.improvement_points or '（なし）'}", size=12, color="#ffeb3b") if cycle.improvement_points else ft.Container(),
                            ft.Text(f"🎯 次のアクション: {cycle.next_actions[:30]}..." if len(cycle.next_actions) > 30 else f"🎯 次のアクション: {cycle.next_actions or '（なし）'}", size=12, color="#64b5f6") if cycle.next_actions else ft.Container(),
                            ft.Container(height=10),
                            ft.ElevatedButton(
                                "このサイクルから引き継いで開始",
                                icon="arrow_forward",
                                bgcolor="#2196f3",
                                color="white",
                                data=cycle.id,
                                on_click=self._start_from_previous_cycle
                            ),
                        ]),
                        padding=10,
                        bgcolor="#263238",
                        border_radius=5
                    )
                ]
            )
            history_items.append(detail_panel)
        
        history_content = history_items if history_items else [ft.Text("履歴なし", size=14, color="#9e9e9e")]
        
        history_card = ft.Container(
            content=ft.Column([
                ft.Text("📚 過去のサイクル", size=16, weight=ft.FontWeight.BOLD),
                ft.Text("クリックで詳細表示・引き継ぎ可能", size=12, color="#9e9e9e"),
                ft.Divider(),
                *history_content,
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        return ft.Column([
            period_card,
            history_card,
        ], spacing=20)
    
    def _show_add_task_dialog(self, e):
        """タスク追加ダイアログを表示"""
        all_tasks = self.db.get_all_tasks()
        cycle_task_ids = [t.id for t in self.db.get_cycle_tasks(self.current_cycle.id)]
        
        # まだ追加されていないタスクのみ表示
        available_tasks = [t for t in all_tasks if t.id not in cycle_task_ids]
        
        task_checkboxes = []
        selected_tasks = []
        
        for task in available_tasks:
            cb = ft.Checkbox(label=f"{task.title} ({task.duration}分)", value=False, data=task.id)
            task_checkboxes.append(cb)
        
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        def add_tasks(e):
            for cb in task_checkboxes:
                if cb.value:
                    self.db.add_task_to_cycle(self.current_cycle.id, cb.data)
            close_dialog(e)
            self._refresh()
        
        dialog = ft.AlertDialog(
            title=ft.Text("タスクを追加"),
            content=ft.Column([
                ft.Text("サイクルに追加するタスクを選択：", size=14),
                *(task_checkboxes if task_checkboxes else [ft.Text("追加可能なタスクがありません", color="#9e9e9e")]),
            ], scroll=ft.ScrollMode.AUTO, height=300),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.TextButton("追加", on_click=add_tasks),
            ]
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()
    
    def _set_to_timer(self, e):
        """未完了タスクをタイマー用プレイリストにセット"""
        if not self.current_cycle:
            return
        
        cycle_tasks = self.db.get_cycle_tasks(self.current_cycle.id)
        incomplete_tasks = [t for t in cycle_tasks if not getattr(t, '_cycle_completed', False)]
        
        if not incomplete_tasks:
            return
        
        # 専用プレイリストを作成または取得
        playlists = self.db.get_all_playlists()
        cycle_playlist = None
        playlist_name = f"🎯 目標: {self.current_cycle.goal[:20] if self.current_cycle.goal else 'サイクル'}"
        
        for pl in playlists:
            if pl.name == playlist_name:
                cycle_playlist = pl
                break
        
        if not cycle_playlist:
            from ..models import Playlist
            new_playlist = Playlist(name=playlist_name, description="目標サイクルから自動生成")
            playlist_id = self.db.create_playlist(new_playlist)
        else:
            playlist_id = cycle_playlist.id
            # 既存のタスクをクリア
            for task in self.db.get_playlist_tasks(playlist_id):
                self.db.remove_task_from_playlist(playlist_id, task.id)
        
        # タスクを追加
        for task in incomplete_tasks:
            self.db.add_task_to_playlist(playlist_id, task.id)
        
        # 成功メッセージ（簡易）
        self._page.snack_bar = ft.SnackBar(
            content=ft.Text(f"タイマーにセットしました！プレイリスト「{playlist_name}」を選択してください"),
            action="OK"
        )
        self._page.snack_bar.open = True
        self._page.update()
    
    def _pick_date(self, date_type: str):
        """日付ピッカーを表示"""
        def on_date_picked(e):
            if e.control.value:
                date_str = e.control.value.strftime("%Y-%m-%d")
                if date_type == "start":
                    self.start_date_value = date_str
                    self.start_date_text.value = date_str
                    self.start_date_text.update()
                else:
                    self.end_date_value = date_str
                    self.end_date_text.value = date_str
                    self.end_date_text.update()
        
        date_picker = ft.DatePicker(
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31),
            on_change=on_date_picked
        )
        self._page.overlay.append(date_picker)
        date_picker.open = True
        self._page.update()
    
    def _create_cycle(self, e):
        """新しいサイクルを作成"""
        # 期間チェック（最低3日）
        start = datetime.strptime(self.start_date_value, "%Y-%m-%d")
        end = datetime.strptime(self.end_date_value, "%Y-%m-%d")
        if (end - start).days < 3:
            return
        
        new_cycle = MoonCycle(
            cycle_start=self.start_date_value,
            cycle_end=self.end_date_value,
            goal=self.goal_field.value or "",
            review="",
            target_task_count=0,
            completed_task_count=0,
            status="active"
        )
        
        self.db.create_moon_cycle(new_cycle)
        self._refresh()
    
    def _save_cycle(self, e):
        """サイクルを保存（PDCAフィールド含む）"""
        if self.current_cycle:
            self.current_cycle.goal = self.goal_field.value or ""
            self.current_cycle.review = self.review_field.value or ""
            # Check フェーズ
            self.current_cycle.self_rating = int(self.rating_slider.value) if hasattr(self, 'rating_slider') else 0
            self.current_cycle.good_points = self.good_points_field.value or "" if hasattr(self, 'good_points_field') else ""
            self.current_cycle.improvement_points = self.improvement_field.value or "" if hasattr(self, 'improvement_field') else ""
            # Act フェーズ
            self.current_cycle.next_actions = self.next_actions_field.value or "" if hasattr(self, 'next_actions_field') else ""
            
            self.db.update_moon_cycle(self.current_cycle)
            
            self.save_status.value = "✓ 保存しました"
            self.save_status.update()
    
    def _complete_cycle(self, e):
        """サイクル完了（振り返りダイアログ付き）"""
        if not self.current_cycle:
            return
        
        # まず現在の入力内容を保存
        self._save_cycle(e)
        
        cycle_tasks = self.db.get_cycle_tasks(self.current_cycle.id)
        completed_count = sum(1 for t in cycle_tasks if getattr(t, '_cycle_completed', False))
        total_count = len(cycle_tasks)
        
        # Check/Act入力用フィールド
        rating_slider = ft.Slider(min=1, max=5, divisions=4, label="{value}", value=3)
        good_points_input = ft.TextField(label="✅ うまくいったこと", multiline=True, min_lines=2, max_lines=3)
        improvement_input = ft.TextField(label="📝 改善が必要なこと", multiline=True, min_lines=2, max_lines=3)
        next_actions_input = ft.TextField(label="🎯 次のアクション", multiline=True, min_lines=2, max_lines=3)
        
        # 完了確認ダイアログ
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        def confirm_complete(e):
            # Check/Actフィールドを保存
            self.current_cycle.self_rating = int(rating_slider.value)
            self.current_cycle.good_points = good_points_input.value or ""
            self.current_cycle.improvement_points = improvement_input.value or ""
            self.current_cycle.next_actions = next_actions_input.value or ""
            self.current_cycle.status = "completed"
            self.current_cycle.completed_task_count = completed_count
            self.current_cycle.target_task_count = total_count
            self.db.update_moon_cycle(self.current_cycle)
            dialog.open = False
            self._refresh()
            self._page.update()
        
        # 達成率によるメッセージ
        if total_count > 0:
            rate = completed_count / total_count * 100
        else:
            rate = 0
        
        if rate >= 80:
            message = "🎉 素晴らしい成果です！"
            color = "#4caf50"
        elif rate >= 50:
            message = "👍 良い進捗ですね！"
            color = "#64b5f6"
        else:
            message = "💪 次はもっと達成できます！"
            color = "#ffeb3b"
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("サイクルを完了 - 振り返り"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"進捗: {completed_count}/{total_count} タスク ({rate:.0f}%)", size=16),
                    ft.Text(message, size=14, color=color),
                    ft.Divider(),
                    ft.Text("Check（振り返り）", size=14, weight=ft.FontWeight.BOLD, color="#ffeb3b"),
                    ft.Text("自己評価", size=12, color="#9e9e9e"),
                    rating_slider,
                    good_points_input,
                    improvement_input,
                    ft.Divider(),
                    ft.Text("Act（次のアクション）", size=14, weight=ft.FontWeight.BOLD, color="#4caf50"),
                    next_actions_input,
                ], tight=True, scroll=ft.ScrollMode.AUTO),
                width=350,
                height=400,
            ),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.ElevatedButton("完了する", bgcolor="#4caf50", color="white", on_click=confirm_complete),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self._page.open(dialog)
    
    def _confirm_delete_cycle(self, e):
        """削除確認ダイアログ"""
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        def delete_cycle(e):
            if self.current_cycle:
                self.db.delete_moon_cycle(self.current_cycle.id)
            close_dialog(e)
            self._refresh()
        
        dialog = ft.AlertDialog(
            title=ft.Text("サイクルを削除"),
            content=ft.Text("このサイクルと紐付けられたタスク情報を削除しますか？"),
            actions=[
                ft.TextButton("キャンセル", on_click=close_dialog),
                ft.TextButton("削除", on_click=delete_cycle),
            ]
        )
        self._page.overlay.append(dialog)
        dialog.open = True
        self._page.update()
    
    def _refresh(self):
        """画面を更新"""
        self._load_active_cycle()
        self.controls.clear()
        self._build()
        self.update()
    
    def _start_from_previous_cycle(self, e):
        """前サイクルから引き継いで新しいサイクルを開始"""
        parent_cycle_id = e.control.data
        if not parent_cycle_id:
            return
        
        # 親サイクルを取得
        all_cycles = self.db.get_all_moon_cycles()
        parent = next((c for c in all_cycles if c.id == parent_cycle_id), None)
        if not parent:
            return
        
        # 新しいサイクルの期間設定
        today = datetime.now()
        default_end = today + timedelta(days=7)
        
        # 前サイクルの「次のアクション」を目標にプリセット
        new_goal = ""
        if parent.next_actions:
            new_goal = f"【前サイクルからの引き継ぎ】\n{parent.next_actions}"
        
        new_cycle = MoonCycle(
            cycle_start=today.strftime("%Y-%m-%d"),
            cycle_end=default_end.strftime("%Y-%m-%d"),
            goal=new_goal,
            review="",
            target_task_count=0,
            completed_task_count=0,
            status="active",
            parent_cycle_id=parent_cycle_id
        )
        
        self.db.create_moon_cycle(new_cycle)
        
        # 成功メッセージ
        self._page.snack_bar = ft.SnackBar(
            content=ft.Text("✅ 前サイクルから引き継いで新しいサイクルを開始しました！"),
            action="OK"
        )
        self._page.snack_bar.open = True
        
        self._refresh()
