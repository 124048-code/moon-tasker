"""
データモデル定義
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Task:
    """タスクモデル"""
    id: Optional[int] = None
    title: str = ""
    category: str = ""
    difficulty: int = 1  # 1-5
    duration: int = 25  # 分単位
    break_duration: int = 5  # 休憩時間（分）
    priority: int = 0
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Playlist:
    """プレイリストモデル"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: Optional[datetime] = None


@dataclass
class Creature:
    """生命体モデル"""
    id: Optional[int] = None
    name: str = ""
    mood: int = 50  # 0-100
    energy: int = 50  # 0-100
    evolution_stage: int = 1  # 1-5
    status: str = "none"  # none, active, dead, runaway, completed
    started_at: Optional[datetime] = None  # 養育開始日
    ended_at: Optional[datetime] = None  # 終了日（死亡/家出/完了）
    cooldown_until: Optional[datetime] = None  # 次に育てられる日（死亡/家出時は1ヶ月後）
    last_interaction: Optional[datetime] = None
    created_at: Optional[datetime] = None


@dataclass
class Badge:
    """バッジ（星座）モデル"""
    id: Optional[int] = None
    name: str = ""
    constellation_name: str = ""
    description: str = ""
    unlock_condition: str = ""  # JSON形式
    unlocked: bool = False
    unlocked_at: Optional[datetime] = None


@dataclass
class MoonCycle:
    """目標サイクルモデル（PDCA対応・タスクベース進捗）"""
    id: Optional[int] = None
    cycle_start: Optional[str] = None  # YYYY-MM-DD形式
    cycle_end: Optional[str] = None    # YYYY-MM-DD形式
    goal: str = ""                     # 目標の説明（Plan）
    review: str = ""                   # 振り返りメモ（互換性維持）
    target_task_count: int = 1         # 目標タスク数（分母）
    completed_task_count: int = 0      # 完了タスク数（分子）
    status: str = "active"             # active, completed
    # Check フェーズ用（振り返り）
    self_rating: int = 0               # 自己評価（1-5、0は未評価）
    good_points: str = ""              # うまくいった点
    improvement_points: str = ""       # 改善が必要な点
    # Act フェーズ用（次のアクション）
    next_actions: str = ""             # 次サイクルへの改善アクション
    parent_cycle_id: Optional[int] = None  # 前サイクルへの参照


@dataclass
class LifestyleSettings:
    """生活時間設定モデル"""
    id: Optional[int] = None
    wake_time: str = "07:00"  # 起床時間
    sleep_time: str = "23:00"  # 就寝時間
    min_sleep_hours: int = 7  # 最低睡眠時間
    bath_time: str = "21:00"  # 入浴時間
    bath_duration: int = 30  # 入浴時間（分）
    breakfast_time: str = "07:30"  # 朝食時間
    lunch_time: str = "12:00"  # 昼食時間
    dinner_time: str = "19:00"  # 夕食時間
    meal_duration: int = 30  # 食事時間（分）
