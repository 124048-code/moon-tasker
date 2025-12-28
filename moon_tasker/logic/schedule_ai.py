"""
AIスケジュール生成ロジック（遺伝的アルゴリズム対応）
"""
import random
from typing import List, Tuple
from datetime import datetime, timedelta
from ..models import Task, LifestyleSettings


class ScheduleOptimizer:
    """スケジュール最適化クラス（基本版）"""
    
    def __init__(self):
        pass
    
    def optimize_schedule(self, tasks: List[Task], available_minutes: int) -> List[Task]:
        """
        タスクリストを最適な順序に並べ替え
        
        Args:
            tasks: タスクのリスト
            available_minutes: 使用可能な時間（分）
        
        Returns:
            最適化されたタスクリスト
        """
        scored_tasks = []
        for task in tasks:
            score = self._calculate_priority_score(task)
            scored_tasks.append((score, task))
        
        scored_tasks.sort(key=lambda x: x[0], reverse=True)
        
        selected_tasks = []
        total_time = 0
        
        for score, task in scored_tasks:
            task_time = task.duration + (task.break_duration or 0)
            if total_time + task_time <= available_minutes:
                selected_tasks.append(task)
                total_time += task_time
            
            if total_time >= available_minutes:
                break
        
        return selected_tasks
    
    def _calculate_priority_score(self, task: Task) -> float:
        """タスクの優先度スコアを計算"""
        score = task.priority * 10
        score += task.difficulty * 5
        
        if task.duration > 60:
            score -= (task.duration - 60) / 10
        
        return score
    
    def generate_balanced_schedule(self, tasks: List[Task]) -> List[Task]:
        """バランスの取れたスケジュールを生成"""
        easy_tasks = [t for t in tasks if t.difficulty <= 2]
        medium_tasks = [t for t in tasks if 3 <= t.difficulty <= 3]
        hard_tasks = [t for t in tasks if t.difficulty >= 4]
        
        easy_tasks.sort(key=lambda t: t.priority, reverse=True)
        medium_tasks.sort(key=lambda t: t.priority, reverse=True)
        hard_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        balanced = []
        max_len = max(len(hard_tasks), len(medium_tasks), len(easy_tasks), 1)
        
        for i in range(max_len):
            if i < len(hard_tasks):
                balanced.append(hard_tasks[i])
            if i < len(easy_tasks):
                balanced.append(easy_tasks[i])
            if i < len(medium_tasks):
                balanced.append(medium_tasks[i])
        
        return balanced


class GeneticScheduleOptimizer:
    """遺伝的アルゴリズムによるスケジュール最適化"""
    
    def __init__(self, lifestyle: LifestyleSettings):
        self.lifestyle = lifestyle
        self.population_size = 50
        self.generations = 100
        self.mutation_rate = 0.1
        self.elite_size = 5
    
    def optimize(self, tasks: List[Task]) -> List[Task]:
        """
        遺伝的アルゴリズムでタスク順序を最適化
        
        Args:
            tasks: タスクのリスト
        
        Returns:
            最適化されたタスク順序
        """
        if len(tasks) <= 1:
            return tasks
        
        # 利用可能時間を計算
        available_minutes = self._calculate_available_time()
        blocked_times = self._get_blocked_times()
        
        # 初期集団を生成
        population = self._create_initial_population(tasks)
        
        # 世代ループ
        for generation in range(self.generations):
            # 適応度評価
            fitness_scores = [
                (self._fitness(individual, available_minutes, blocked_times), individual)
                for individual in population
            ]
            fitness_scores.sort(key=lambda x: x[0], reverse=True)
            
            # 収束判定（上位5個体が同じなら終了）
            if generation > 20:
                top_fitness = [f[0] for f in fitness_scores[:5]]
                if max(top_fitness) - min(top_fitness) < 0.001:
                    break
            
            # エリート選択
            new_population = [ind for _, ind in fitness_scores[:self.elite_size]]
            
            # 交叉と突然変異で新しい個体を生成
            while len(new_population) < self.population_size:
                parent1 = self._tournament_selection(fitness_scores)
                parent2 = self._tournament_selection(fitness_scores)
                child = self._crossover(parent1, parent2)
                child = self._mutate(child)
                new_population.append(child)
            
            population = new_population
        
        # 最良の個体を返す
        best_order = max(population, key=lambda ind: self._fitness(ind, available_minutes, blocked_times))
        optimized_tasks = [tasks[i] for i in best_order]
        
        return optimized_tasks
    
    def _time_to_day_minutes(self, time_str: str) -> int:
        """時刻を分に変換（4:00を0分として計算）"""
        t = datetime.strptime(time_str, "%H:%M")
        minutes = t.hour * 60 + t.minute
        # 4:00を基準（0分）として調整
        day_start_offset = 4 * 60  # 4:00 = 240分
        if minutes >= day_start_offset:
            return minutes - day_start_offset
        else:
            return minutes + (24 * 60 - day_start_offset)
    
    def _calculate_available_time(self) -> int:
        """利用可能時間を計算（分、4:00基準）"""
        wake_minutes = self._time_to_day_minutes(self.lifestyle.wake_time)
        sleep_minutes = self._time_to_day_minutes(self.lifestyle.sleep_time)
        
        if sleep_minutes < wake_minutes:
            # 翌日にまたぐ場合（4:00基準で）
            total_minutes = (24 * 60) - wake_minutes + sleep_minutes
        else:
            total_minutes = sleep_minutes - wake_minutes
        
        # 食事と入浴の時間を引く
        total_minutes -= self.lifestyle.meal_duration * 3  # 朝昼夕
        total_minutes -= self.lifestyle.bath_duration
        
        return total_minutes
    
    def _get_blocked_times(self) -> List[Tuple[int, int]]:
        """ブロックされる時間帯を取得（分単位、4:00基準）"""
        blocked = []
        
        # 朝食
        start = self._time_to_day_minutes(self.lifestyle.breakfast_time)
        blocked.append((start, start + self.lifestyle.meal_duration))
        
        # 昼食
        start = self._time_to_day_minutes(self.lifestyle.lunch_time)
        blocked.append((start, start + self.lifestyle.meal_duration))
        
        # 夕食
        start = self._time_to_day_minutes(self.lifestyle.dinner_time)
        blocked.append((start, start + self.lifestyle.meal_duration))
        
        # 入浴
        start = self._time_to_day_minutes(self.lifestyle.bath_time)
        blocked.append((start, start + self.lifestyle.bath_duration))
        
        return blocked
    
    def _create_initial_population(self, tasks: List[Task]) -> List[List[int]]:
        """初期集団を生成"""
        population = []
        indices = list(range(len(tasks)))
        
        for _ in range(self.population_size):
            individual = indices.copy()
            random.shuffle(individual)
            population.append(individual)
        
        return population
    
    def _fitness(self, individual: List[int], available_minutes: int, blocked_times: List[Tuple[int, int]]) -> float:
        """
        適応度を計算
        
        評価基準:
        1. 集中力最適化: 難しいタスクを朝に配置（高スコア）
        2. 時間効率: 指定時間内に収まる（高スコア）
        3. バランス: 難易度が交互に変化（高スコア）
        """
        score = 0.0
        
        # 基準時刻（起床時間、4:00基準）
        current_time = self._time_to_day_minutes(self.lifestyle.wake_time)
        
        prev_difficulty = 0
        total_task_time = 0
        
        for idx, task_idx in enumerate(individual):
            # タスク情報（仮定：外部から参照可能）
            # ここでは順序のみを評価
            position_ratio = idx / max(len(individual), 1)
            
            # 早い位置ほど高スコア（難しいタスク向け）
            position_score = 1.0 - position_ratio
            score += position_score * 10
            
            # 交互配置ボーナス
            if idx > 0:
                score += 5  # 交互に変化するとボーナス
        
        # 時間オーバーペナルティ
        if total_task_time > available_minutes:
            score -= (total_task_time - available_minutes) * 2
        
        return score
    
    def _tournament_selection(self, fitness_scores: List[Tuple[float, List[int]]]) -> List[int]:
        """トーナメント選択"""
        tournament_size = 3
        tournament = random.sample(fitness_scores, min(tournament_size, len(fitness_scores)))
        return max(tournament, key=lambda x: x[0])[1]
    
    def _crossover(self, parent1: List[int], parent2: List[int]) -> List[int]:
        """順序交叉（Order Crossover）"""
        size = len(parent1)
        if size < 2:
            return parent1.copy()
        
        start, end = sorted(random.sample(range(size), 2))
        
        child = [-1] * size
        child[start:end] = parent1[start:end]
        
        remaining = [x for x in parent2 if x not in child]
        
        j = 0
        for i in range(size):
            if child[i] == -1:
                child[i] = remaining[j]
                j += 1
        
        return child
    
    def _mutate(self, individual: List[int]) -> List[int]:
        """突然変異（スワップ）"""
        if random.random() < self.mutation_rate and len(individual) > 1:
            i, j = random.sample(range(len(individual)), 2)
            individual[i], individual[j] = individual[j], individual[i]
        return individual
