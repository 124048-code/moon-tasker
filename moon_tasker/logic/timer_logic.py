"""
タイマー制御ロジック
"""
import asyncio
from typing import Callable, Optional, List
from ..models import Task


class TimerController:
    """連続タイマー制御クラス（プレイリスト対応）"""
    
    def __init__(self):
        # 現在のタスク
        self.current_task: Optional[Task] = None
        self.is_running: bool = False
        self.is_break: bool = False
        self.remaining_seconds: int = 0
        
        # プレイリスト連続実行用
        self.playlist_tasks: List[Task] = []
        self.current_task_index: int = 0
        self.is_playlist_mode: bool = False
        
        # コールバック
        self.on_tick: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None  # 個別タスク完了
        self.on_break_start: Optional[Callable] = None
        self.on_task_start: Optional[Callable] = None
        self.on_resume: Optional[Callable] = None
        self.on_playlist_complete: Optional[Callable] = None  # プレイリスト全完了
        self.on_next_task_start: Optional[Callable] = None  # 次のタスク開始
    
    async def start_timer(self, task: Task):
        """単一タスクタイマーを開始"""
        self.is_playlist_mode = False
        self.playlist_tasks = []
        self.current_task_index = 0
        await self._start_task(task)
    
    async def start_playlist(self, tasks: List[Task]):
        """プレイリスト連続タイマーを開始"""
        if not tasks:
            return
        
        self.is_playlist_mode = True
        self.playlist_tasks = tasks
        self.current_task_index = 0
        await self._start_task(tasks[0])
    
    async def _start_task(self, task: Task):
        """タスクを開始（内部用）"""
        self.current_task = task
        self.is_running = True
        self.is_break = False
        self.remaining_seconds = task.duration * 60
        
        if self.on_task_start:
            self.on_task_start(task)
        
        await self._countdown()
    
    async def _countdown(self):
        """カウントダウン処理"""
        while self.is_running and self.remaining_seconds > 0:
            await asyncio.sleep(1)
            if self.is_running:
                self.remaining_seconds -= 1
                
                if self.on_tick:
                    self.on_tick(self.remaining_seconds, self.is_break)
        
        if self.remaining_seconds == 0 and self.is_running:
            await self._on_timer_complete()
    
    async def _on_timer_complete(self):
        """タイマー完了時の処理"""
        if not self.is_break:
            # タスク作業完了 → 休憩開始（ただし最後のタスクは休憩スキップ）
            is_last_task = self.is_playlist_mode and (self.current_task_index >= len(self.playlist_tasks) - 1)
            
            if self.current_task and self.current_task.break_duration > 0 and not is_last_task:
                self.is_break = True
                self.remaining_seconds = self.current_task.break_duration * 60
                
                if self.on_break_start:
                    self.on_break_start(self.current_task)
                
                await self._countdown()
            else:
                # 休憩なし、または最後のタスク（休憩スキップ）
                await self._on_task_finished()
        else:
            # 休憩完了
            await self._on_task_finished()
    
    async def _on_task_finished(self):
        """タスク（+休憩）完了時の処理"""
        # 個別タスク完了コールバック
        if self.on_complete:
            self.on_complete(self.current_task)
        
        # プレイリストモードの場合、次のタスクへ
        if self.is_playlist_mode:
            self.current_task_index += 1
            
            if self.current_task_index < len(self.playlist_tasks):
                # 次のタスクを開始
                next_task = self.playlist_tasks[self.current_task_index]
                
                if self.on_next_task_start:
                    self.on_next_task_start(next_task, self.current_task_index, len(self.playlist_tasks))
                
                await self._start_task(next_task)
            else:
                # プレイリスト全完了 - 0:00を表示してすぐに完了通知
                self.remaining_seconds = 0
                if self.on_tick:
                    self.on_tick(0, False)
                
                if self.on_playlist_complete:
                    self.on_playlist_complete()
    
    def pause(self):
        """タイマーを一時停止"""
        self.is_running = False
    
    def resume(self):
        """タイマーを再開"""
        if self.remaining_seconds > 0 and not self.is_running:
            self.is_running = True
            if self.on_resume:
                self.on_resume()
    
    async def resume_countdown(self):
        """カウントダウンを再開（page.run_taskから呼び出し）"""
        await self._countdown()
    
    def stop(self):
        """タイマーを停止"""
        self.is_running = False
        self.remaining_seconds = 0
        self.current_task = None
        self.playlist_tasks = []
        self.current_task_index = 0
        self.is_playlist_mode = False
    
    def get_formatted_time(self) -> str:
        """残り時間を整形（MM:SS）"""
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_progress(self) -> tuple:
        """プレイリスト進捗を取得 (current, total)"""
        if self.is_playlist_mode:
            return (self.current_task_index + 1, len(self.playlist_tasks))
        return (1, 1)
    
    def get_next_task(self) -> Optional[Task]:
        """次のタスクを取得（プレビュー用）"""
        if self.is_playlist_mode and self.current_task_index + 1 < len(self.playlist_tasks):
            return self.playlist_tasks[self.current_task_index + 1]
        return None
