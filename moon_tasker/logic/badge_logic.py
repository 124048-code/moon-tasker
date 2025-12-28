"""
称号（バッジ）達成判定ロジック
"""
import json
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from ..database import Database
from ..models import Badge


class BadgeSystem:
    """称号システム - 達成判定・獲得処理"""
    
    def __init__(self, db: Database):
        self.db = db
        self.newly_unlocked: List[Badge] = []  # 今回新たに解放された称号
    
    def check_all_badges(self) -> List[Badge]:
        """全ての称号の達成条件をチェックし、新たに解放されたものを返す"""
        self.newly_unlocked = []
        badges = self.db.get_all_badges()
        
        for badge in badges:
            if not badge.unlocked:
                if self._check_condition(badge):
                    self.db.unlock_badge(badge.id)
                    badge.unlocked = True
                    badge.unlocked_at = datetime.now()
                    self.newly_unlocked.append(badge)
        
        return self.newly_unlocked
    
    def _check_condition(self, badge: Badge) -> bool:
        """個別の称号の達成条件をチェック"""
        try:
            condition = json.loads(badge.unlock_condition)
            condition_type = condition.get("type", "")
            
            if condition_type == "tasks_completed":
                return self._check_tasks_completed(condition.get("count", 1))
            
            elif condition_type == "cycles_completed":
                return self._check_cycles_completed(condition.get("count", 1))
            
            elif condition_type == "cycle_high_achievement":
                return self._check_cycle_high_achievement(condition.get("rate", 80))
            
            elif condition_type == "consecutive_days":
                return self._check_consecutive_days(condition.get("count", 7))
            
            elif condition_type == "time_tasks":
                return self._check_time_tasks(
                    condition.get("time", "night"),
                    condition.get("count", 10)
                )
            
            elif condition_type == "difficulty_tasks":
                return self._check_difficulty_tasks(
                    condition.get("difficulty", 5),
                    condition.get("count", 10)
                )
            
            elif condition_type == "all_difficulties":
                return self._check_all_difficulties(condition.get("count_each", 5))
            
            elif condition_type == "creature_evolution":
                return self._check_creature_evolution(condition.get("stage", 3))
            
        except (json.JSONDecodeError, KeyError):
            pass
        
        return False
    
    def _check_tasks_completed(self, required_count: int) -> bool:
        """完了タスク数をチェック"""
        count = self.db.get_completed_task_count()
        return count >= required_count
    
    def _check_cycles_completed(self, required_count: int) -> bool:
        """完了サイクル数をチェック"""
        cycles = self.db.get_all_moon_cycles()
        completed_count = len([c for c in cycles if c.status == "completed"])
        return completed_count >= required_count
    
    def _check_cycle_high_achievement(self, required_rate: int) -> bool:
        """高達成率サイクルをチェック"""
        cycles = self.db.get_all_moon_cycles()
        for cycle in cycles:
            if cycle.status == "completed" and cycle.target_task_count > 0:
                rate = cycle.completed_task_count / cycle.target_task_count * 100
                if rate >= required_rate:
                    return True
        return False
    
    def _check_consecutive_days(self, required_days: int) -> bool:
        """連続完了日数をチェック"""
        tasks = self.db.get_all_tasks()
        completed_dates = set()
        
        for task in tasks:
            if task.status == "completed" and task.completed_at:
                if isinstance(task.completed_at, str):
                    try:
                        date = datetime.fromisoformat(task.completed_at).date()
                    except:
                        continue
                else:
                    date = task.completed_at.date()
                completed_dates.add(date)
        
        if not completed_dates:
            return False
        
        # 連続日数を計算
        sorted_dates = sorted(completed_dates)
        max_consecutive = 1
        current_consecutive = 1
        
        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] - sorted_dates[i-1] == timedelta(days=1):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 1
        
        return max_consecutive >= required_days
    
    def _check_time_tasks(self, time_type: str, required_count: int) -> bool:
        """時間帯別タスク完了数をチェック"""
        tasks = self.db.get_all_tasks()
        count = 0
        
        for task in tasks:
            if task.status == "completed" and task.completed_at:
                try:
                    if isinstance(task.completed_at, str):
                        completed_time = datetime.fromisoformat(task.completed_at)
                    else:
                        completed_time = task.completed_at
                    
                    hour = completed_time.hour
                    
                    if time_type == "night" and hour >= 22:
                        count += 1
                    elif time_type == "morning" and hour < 6:
                        count += 1
                except:
                    continue
        
        return count >= required_count
    
    def _check_difficulty_tasks(self, difficulty: int, required_count: int) -> bool:
        """特定難易度タスク完了数をチェック"""
        tasks = self.db.get_all_tasks()
        count = sum(1 for t in tasks if t.status == "completed" and t.difficulty == difficulty)
        return count >= required_count
    
    def _check_all_difficulties(self, required_each: int) -> bool:
        """全難易度タスク完了をチェック"""
        tasks = self.db.get_all_tasks()
        difficulty_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        for task in tasks:
            if task.status == "completed" and task.difficulty in difficulty_counts:
                difficulty_counts[task.difficulty] += 1
        
        return all(count >= required_each for count in difficulty_counts.values())
    
    def _check_creature_evolution(self, required_stage: int) -> bool:
        """生命体進化段階をチェック"""
        creature = self.db.get_creature()
        if creature:
            return creature.evolution_stage >= required_stage
        return False
    
    def get_badge_progress(self, badge: Badge) -> Tuple[int, int]:
        """称号の進捗を取得 (current, target)"""
        try:
            condition = json.loads(badge.unlock_condition)
            condition_type = condition.get("type", "")
            
            if condition_type == "tasks_completed":
                target = condition.get("count", 1)
                current = min(self.db.get_completed_task_count(), target)
                return (current, target)
            
            elif condition_type == "cycles_completed":
                target = condition.get("count", 1)
                cycles = self.db.get_all_moon_cycles()
                current = min(len([c for c in cycles if c.status == "completed"]), target)
                return (current, target)
            
            elif condition_type == "difficulty_tasks":
                target = condition.get("count", 10)
                difficulty = condition.get("difficulty", 5)
                tasks = self.db.get_all_tasks()
                current = min(sum(1 for t in tasks if t.status == "completed" and t.difficulty == difficulty), target)
                return (current, target)
            
            elif condition_type == "creature_evolution":
                target = condition.get("stage", 3)
                creature = self.db.get_creature()
                current = creature.evolution_stage if creature else 0
                return (current, target)
            
        except:
            pass
        
        return (0, 1)
    
    def get_rarity_from_condition(self, badge: Badge) -> int:
        """条件JSONからレア度を推定"""
        try:
            condition = json.loads(badge.unlock_condition)
            condition_type = condition.get("type", "")
            count = condition.get("count", 1)
            
            # タスク完了数に基づくレア度
            if condition_type == "tasks_completed":
                if count >= 100:
                    return 4
                elif count >= 50:
                    return 3
                elif count >= 20:
                    return 2
                else:
                    return 1
            
            # 連続日数に基づくレア度
            elif condition_type == "consecutive_days":
                if count >= 30:
                    return 5
                elif count >= 7:
                    return 3
                else:
                    return 2
            
            # 生命体進化に基づくレア度
            elif condition_type == "creature_evolution":
                stage = condition.get("stage", 1)
                if stage >= 5:
                    return 5
                elif stage >= 3:
                    return 3
                else:
                    return 2
            
            # その他
            return 2
            
        except:
            return 1
