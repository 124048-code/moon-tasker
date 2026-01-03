"""
データベース操作クラス
"""
import sqlite3
from datetime import datetime
from typing import List, Optional
from .models import Task, Playlist, Creature, Badge, MoonCycle, LifestyleSettings


class Database:
    """SQLiteデータベース管理クラス"""
    
    def __init__(self, db_path: str = "moon_tasker.db", guest_id: str = None):
        self.db_path = db_path
        self.guest_id = guest_id  # ゲストユーザー識別用
        self.init_database()
    
    def get_connection(self):
        """データベース接続を取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """データベースとテーブルの初期化"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # tasksテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT,
                difficulty INTEGER DEFAULT 1,
                duration INTEGER,
                break_duration INTEGER,
                priority INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # playlistsテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # playlist_tasksテーブル（多対多の関連）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER,
                task_id INTEGER,
                order_index INTEGER,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # creaturesテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                mood INTEGER DEFAULT 50,
                energy INTEGER DEFAULT 50,
                evolution_stage INTEGER DEFAULT 1,
                last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                ended_at TIMESTAMP,
                cooldown_until TIMESTAMP
            )
        """)
        
        # creaturesテーブルのマイグレーション（statusカラム追加）
        try:
            cursor.execute("ALTER TABLE creatures ADD COLUMN status TEXT DEFAULT 'active'")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE creatures ADD COLUMN ended_at TIMESTAMP")
        except:
            pass
        try:
            cursor.execute("ALTER TABLE creatures ADD COLUMN cooldown_until TIMESTAMP")
        except:
            pass
        
        # badgesテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                constellation_name TEXT,
                description TEXT,
                unlock_condition TEXT,
                unlocked BOOLEAN DEFAULT 0,
                unlocked_at TIMESTAMP
            )
        """)
        
        # moon_cyclesテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS moon_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_start DATE NOT NULL,
                cycle_end DATE,
                goal TEXT,
                review TEXT,
                target_task_count INTEGER DEFAULT 1,
                completed_task_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        """)
        
        # cycle_tasksテーブル（サイクルとタスクの紐付け）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cycle_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                is_completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                FOREIGN KEY (cycle_id) REFERENCES moon_cycles(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # activity_logテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                action TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # lifestyle_settingsテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lifestyle_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wake_time TEXT DEFAULT '07:00',
                sleep_time TEXT DEFAULT '23:00',
                min_sleep_hours INTEGER DEFAULT 7,
                bath_time TEXT DEFAULT '21:00',
                bath_duration INTEGER DEFAULT 30,
                breakfast_time TEXT DEFAULT '07:30',
                lunch_time TEXT DEFAULT '12:00',
                dinner_time TEXT DEFAULT '19:00',
                meal_duration INTEGER DEFAULT 30
            )
        """)
        
        # プレゼント図鑑テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS present_collection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creature_id INTEGER,
                name TEXT NOT NULL,
                emoji TEXT,
                description TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creature_id) REFERENCES creatures(id)
            )
        """)
        
        # 思い出日記テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creature_diary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creature_id INTEGER,
                entry_date DATE NOT NULL,
                entry_type TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creature_id) REFERENCES creatures(id)
            )
        """)
        
        conn.commit()
        conn.close()
        
        # マイグレーション（既存DBへのカラム追加）
        self._migrate_moon_cycles_table()
        self._migrate_guest_id_columns()  # ゲストID分離用マイグレーション
        
        # 初期データの作成（生命体が存在しない場合）
        self._init_default_creature()
        self._init_default_badges()
        self._init_default_lifestyle()
    
    def _migrate_guest_id_columns(self):
        """ゲストID分離用のカラムを追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 各テーブルにguest_idカラムを追加
        tables_to_migrate = ['tasks', 'playlists', 'creatures', 'moon_cycles', 
                            'activity_log', 'lifestyle_settings']
        
        for table in tables_to_migrate:
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row['name'] for row in cursor.fetchall()]
                if 'guest_id' not in columns:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN guest_id TEXT")
            except Exception as e:
                print(f"Migration error for {table}: {e}")
        
        conn.commit()
        conn.close()
    
    def _migrate_moon_cycles_table(self):
        """moon_cyclesテーブルのマイグレーション"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # カラムの存在確認と追加
        cursor.execute("PRAGMA table_info(moon_cycles)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'target_task_count' not in columns:
            cursor.execute("ALTER TABLE moon_cycles ADD COLUMN target_task_count INTEGER DEFAULT 1")
        if 'completed_task_count' not in columns:
            cursor.execute("ALTER TABLE moon_cycles ADD COLUMN completed_task_count INTEGER DEFAULT 0")
        # PDCA Check/Act フェーズ用カラム
        if 'self_rating' not in columns:
            cursor.execute("ALTER TABLE moon_cycles ADD COLUMN self_rating INTEGER DEFAULT 0")
        if 'good_points' not in columns:
            cursor.execute("ALTER TABLE moon_cycles ADD COLUMN good_points TEXT DEFAULT ''")
        if 'improvement_points' not in columns:
            cursor.execute("ALTER TABLE moon_cycles ADD COLUMN improvement_points TEXT DEFAULT ''")
        if 'next_actions' not in columns:
            cursor.execute("ALTER TABLE moon_cycles ADD COLUMN next_actions TEXT DEFAULT ''")
        if 'parent_cycle_id' not in columns:
            cursor.execute("ALTER TABLE moon_cycles ADD COLUMN parent_cycle_id INTEGER")
        
        conn.commit()
        conn.close()
    
    def _init_default_creature(self):
        """生命体テーブルのマイグレーション（自動作成しない）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 新しいカラムを追加（存在しない場合のみ）
        cursor.execute("PRAGMA table_info(creatures)")
        columns = {row['name'] for row in cursor.fetchall()}
        
        if 'status' not in columns:
            cursor.execute("ALTER TABLE creatures ADD COLUMN status TEXT DEFAULT 'none'")
        if 'started_at' not in columns:
            cursor.execute("ALTER TABLE creatures ADD COLUMN started_at TIMESTAMP")
        if 'ended_at' not in columns:
            cursor.execute("ALTER TABLE creatures ADD COLUMN ended_at TIMESTAMP")
        if 'cooldown_until' not in columns:
            cursor.execute("ALTER TABLE creatures ADD COLUMN cooldown_until TIMESTAMP")
        
        conn.commit()
        conn.close()
    
    def _init_default_badges(self):
        """デフォルトのバッジを作成（16種類）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM badges")
        count = cursor.fetchone()['count']
        
        # 16種類より少ない場合は古いバッジを削除して再作成
        if count < 16:
            cursor.execute("DELETE FROM badges")
            
            # (name, constellation, description, unlock_condition_json, rarity)
            # rarity: 1=★, 2=★★, 3=★★★, 4=★★★★, 5=★★★★★
            default_badges = [
                # 初心者カテゴリ
                ("First Steps", "オリオン座", "初めてのタスクを完了", '{"type": "tasks_completed", "count": 1}', 1),
                ("Early Bird", "こぐま座", "5つのタスクを完了", '{"type": "tasks_completed", "count": 5}', 1),
                # タスク達成カテゴリ
                ("Task Master", "カシオペヤ座", "20タスクを完了", '{"type": "tasks_completed", "count": 20}', 2),
                ("Scorpius", "さそり座", "50タスクを完了", '{"type": "tasks_completed", "count": 50}', 3),
                ("Centurion", "ペガサス座", "100タスクを完了", '{"type": "tasks_completed", "count": 100}', 4),
                # 月サイクルカテゴリ
                ("Moon Walker", "しし座", "最初の目標サイクルを完了", '{"type": "cycles_completed", "count": 1}', 2),
                ("Lunar Master", "みずがめ座", "5つの目標サイクルを完了", '{"type": "cycles_completed", "count": 5}', 3),
                ("Gemini Flow", "ふたご座", "サイクル達成率80%以上で完了", '{"type": "cycle_high_achievement", "rate": 80}', 3),
                # 継続力カテゴリ
                ("Dedicated", "アンドロメダ座", "7日連続でタスクを完了", '{"type": "consecutive_days", "count": 7}', 3),
                ("Polaris", "北極星", "30日連続でタスクを完了", '{"type": "consecutive_days", "count": 30}', 5),
                # 時間帯カテゴリ
                ("Night Owl", "はくちょう座", "深夜(22時以降)にタスクを10回完了", '{"type": "time_tasks", "time": "night", "count": 10}', 2),
                ("Morning Star", "おうし座", "早朝(6時前)にタスクを10回完了", '{"type": "time_tasks", "time": "morning", "count": 10}', 2),
                # 難易度カテゴリ
                ("Dragon Slayer", "りゅう座", "難易度5のタスクを10回完了", '{"type": "difficulty_tasks", "difficulty": 5, "count": 10}', 3),
                ("Harmony", "こと座", "全難易度(1-5)のタスクを各5回以上完了", '{"type": "all_difficulties", "count_each": 5}', 3),
                # 生命体カテゴリ
                ("Soul Friend", "うお座", "生命体を進化段階3に到達させる", '{"type": "creature_evolution", "stage": 3}', 3),
                ("Sagittarius", "いて座", "生命体を進化段階5に到達させる", '{"type": "creature_evolution", "stage": 5}', 5),
            ]
            
            for name, constellation, desc, condition, rarity in default_badges:
                cursor.execute("""
                    INSERT INTO badges (name, constellation_name, description, unlock_condition)
                    VALUES (?, ?, ?, ?)
                """, (name, constellation, desc, condition))
            
            conn.commit()
        conn.close()
    
    # ===== Task操作 =====
    
    def create_task(self, task: Task) -> int:
        """タスクを作成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, category, difficulty, duration, break_duration, priority, status, guest_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (task.title, task.category, task.difficulty, task.duration, 
              task.break_duration, task.priority, task.status, self.guest_id))
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def get_all_tasks(self) -> List[Task]:
        """全タスクを取得（guest_idでフィルタ）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if self.guest_id:
            cursor.execute("SELECT * FROM tasks WHERE guest_id = ? ORDER BY id ASC", (self.guest_id,))
        else:
            cursor.execute("SELECT * FROM tasks WHERE guest_id IS NULL ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            task = Task(
                id=row['id'],
                title=row['title'],
                category=row['category'],
                difficulty=row['difficulty'],
                duration=row['duration'],
                break_duration=row['break_duration'],
                priority=row['priority'],
                status=row['status'],
                created_at=row['created_at'],
                completed_at=row['completed_at']
            )
            tasks.append(task)
        return tasks
    
    def update_task_status(self, task_id: int, status: str):
        """タスクのステータスを更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        completed_at = datetime.now() if status == "completed" else None
        cursor.execute("""
            UPDATE tasks SET status = ?, completed_at = ?
            WHERE id = ?
        """, (status, completed_at, task_id))
        
        conn.commit()
        conn.close()
    
    def delete_task(self, task_id: int):
        """タスクを削除"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
    
    # ===== Creature操作 =====
    
    def get_creature(self) -> Optional[Creature]:
        """生命体を取得（guest_idでフィルタ）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if self.guest_id:
            cursor.execute("SELECT * FROM creatures WHERE guest_id = ? ORDER BY id DESC LIMIT 1", (self.guest_id,))
        else:
            cursor.execute("SELECT * FROM creatures WHERE guest_id IS NULL ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Creature(
                id=row['id'],
                name=row['name'],
                mood=row['mood'],
                energy=row['energy'],
                evolution_stage=row['evolution_stage'],
                status=row['status'] if 'status' in row.keys() else 'none',
                started_at=row['started_at'] if 'started_at' in row.keys() else None,
                ended_at=row['ended_at'] if 'ended_at' in row.keys() else None,
                cooldown_until=row['cooldown_until'] if 'cooldown_until' in row.keys() else None,
                last_interaction=row['last_interaction'],
                created_at=row['created_at']
            )
        return None
    
    def create_creature(self, name: str) -> int:
        """新しい生命体を作成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute("""
            INSERT INTO creatures (name, mood, energy, evolution_stage, status, started_at, last_interaction, created_at, guest_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, 50, 50, 1, 'active', now, now, now, self.guest_id))
        creature_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return creature_id
    
    def update_creature(self, creature: Creature):
        """生命体のパラメータを更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE creatures 
            SET name = ?, mood = ?, energy = ?, evolution_stage = ?, 
                status = ?, started_at = ?, ended_at = ?, cooldown_until = ?,
                last_interaction = ?
            WHERE id = ?
        """, (creature.name, creature.mood, creature.energy, 
              creature.evolution_stage, creature.status, 
              creature.started_at, creature.ended_at, creature.cooldown_until,
              datetime.now(), creature.id))
        conn.commit()
        conn.close()
    
    def reset_all_data(self):
        """全てのプレイデータをリセット"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM creatures")
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM playlists")
        cursor.execute("DELETE FROM playlist_tasks")
        cursor.execute("DELETE FROM moon_cycles")
        cursor.execute("DELETE FROM cycle_tasks")
        cursor.execute("DELETE FROM activity_log")
        # バッジのunlockedをリセット
        cursor.execute("UPDATE badges SET unlocked = 0, unlocked_at = NULL")
        conn.commit()
        conn.close()
    
    # ===== Badge操作 =====
    
    def get_all_badges(self) -> List[Badge]:
        """全バッジを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM badges ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        
        badges = []
        for row in rows:
            badge = Badge(
                id=row['id'],
                name=row['name'],
                constellation_name=row['constellation_name'],
                description=row['description'],
                unlock_condition=row['unlock_condition'],
                unlocked=bool(row['unlocked']),
                unlocked_at=row['unlocked_at']
            )
            badges.append(badge)
        return badges
    
    def unlock_badge(self, badge_id: int):
        """バッジを解放"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE badges SET unlocked = 1, unlocked_at = ?
            WHERE id = ?
        """, (datetime.now(), badge_id))
        conn.commit()
        conn.close()
    
    def unlock_badge_by_name(self, badge_name: str):
        """バッジ名でバッジを解放"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE badges SET unlocked = 1, unlocked_at = ?
            WHERE name = ? AND unlocked = 0
        """, (datetime.now(), badge_name))
        conn.commit()
        conn.close()
    
    # ===== Playlist操作 =====
    
    def create_playlist(self, playlist: Playlist) -> int:
        """プレイリストを作成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO playlists (name, description, guest_id)
            VALUES (?, ?, ?)
        """, (playlist.name, playlist.description, self.guest_id))
        playlist_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return playlist_id
    
    def get_all_playlists(self) -> List[Playlist]:
        """全プレイリストを取得（guest_idでフィルタ）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if self.guest_id:
            cursor.execute("SELECT * FROM playlists WHERE guest_id = ? ORDER BY created_at DESC", (self.guest_id,))
        else:
            cursor.execute("SELECT * FROM playlists WHERE guest_id IS NULL ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        playlists = []
        for row in rows:
            playlist = Playlist(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=row['created_at']
            )
            playlists.append(playlist)
        return playlists
    
    def get_playlist(self, playlist_id: int) -> Optional[Playlist]:
        """プレイリストを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Playlist(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                created_at=row['created_at']
            )
        return None
    
    def delete_playlist(self, playlist_id: int):
        """プレイリストを削除"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 関連するplaylist_tasksも削除
        cursor.execute("DELETE FROM playlist_tasks WHERE playlist_id = ?", (playlist_id,))
        cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        conn.commit()
        conn.close()
    
    def get_playlist_tasks(self, playlist_id: int) -> List[Task]:
        """プレイリスト内のタスクを順序付きで取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.* FROM tasks t
            JOIN playlist_tasks pt ON t.id = pt.task_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.order_index ASC
        """, (playlist_id,))
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            task = Task(
                id=row['id'],
                title=row['title'],
                category=row['category'],
                difficulty=row['difficulty'],
                duration=row['duration'],
                break_duration=row['break_duration'],
                priority=row['priority'],
                status=row['status'],
                created_at=row['created_at'],
                completed_at=row['completed_at']
            )
            tasks.append(task)
        return tasks
    
    def add_task_to_playlist(self, playlist_id: int, task_id: int):
        """タスクをプレイリストに追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 現在の最大order_indexを取得
        cursor.execute("""
            SELECT MAX(order_index) as max_order FROM playlist_tasks 
            WHERE playlist_id = ?
        """, (playlist_id,))
        result = cursor.fetchone()
        max_order = result['max_order'] if result['max_order'] is not None else -1
        
        # 新しいタスクを追加
        cursor.execute("""
            INSERT INTO playlist_tasks (playlist_id, task_id, order_index)
            VALUES (?, ?, ?)
        """, (playlist_id, task_id, max_order + 1))
        conn.commit()
        conn.close()
    
    def remove_task_from_playlist(self, playlist_id: int, task_id: int):
        """タスクをプレイリストから削除"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM playlist_tasks 
            WHERE playlist_id = ? AND task_id = ?
        """, (playlist_id, task_id))
        conn.commit()
        conn.close()
    
    def reorder_playlist_tasks(self, playlist_id: int, task_ids: List[int]):
        """プレイリスト内のタスク順序を更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        for index, task_id in enumerate(task_ids):
            cursor.execute("""
                UPDATE playlist_tasks 
                SET order_index = ?
                WHERE playlist_id = ? AND task_id = ?
            """, (index, playlist_id, task_id))
        conn.commit()
        conn.close()
    
    # ===== 統計情報 =====
    
    def get_completed_task_count(self) -> int:
        """完了したタスク数を取得（activity_logベース：同じタスクも複数カウント）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # activity_logから完了アクション数をカウント（同じプレイリストを何回でもカウント）
        cursor.execute("SELECT COUNT(*) as count FROM activity_log WHERE action = 'completed'")
        count = cursor.fetchone()['count']
        conn.close()
        return count
    
    def log_activity(self, task_id: int, action: str):
        """アクティビティログを記録"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO activity_log (task_id, action, timestamp)
            VALUES (?, ?, ?)
        """, (task_id, action, datetime.now()))
        conn.commit()
        conn.close()
    
    # ===== MoonCycle操作 =====
    
    def get_active_moon_cycle(self) -> Optional[MoonCycle]:
        """アクティブな目標サイクルを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM moon_cycles WHERE status = 'active' ORDER BY id DESC LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_moon_cycle(row)
        return None
    
    def get_all_moon_cycles(self) -> List[MoonCycle]:
        """全ての目標サイクルを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM moon_cycles ORDER BY cycle_start DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_moon_cycle(row) for row in rows]
    
    def _row_to_moon_cycle(self, row) -> MoonCycle:
        """データベース行をMoonCycleモデルに変換"""
        keys = row.keys()
        return MoonCycle(
            id=row['id'],
            cycle_start=row['cycle_start'],
            cycle_end=row['cycle_end'],
            goal=row['goal'] or "",
            review=row['review'] or "",
            target_task_count=row['target_task_count'] if 'target_task_count' in keys else 1,
            completed_task_count=row['completed_task_count'] if 'completed_task_count' in keys else 0,
            status=row['status'],
            # PDCA Check/Act フェーズ
            self_rating=row['self_rating'] if 'self_rating' in keys else 0,
            good_points=row['good_points'] or "" if 'good_points' in keys else "",
            improvement_points=row['improvement_points'] or "" if 'improvement_points' in keys else "",
            next_actions=row['next_actions'] or "" if 'next_actions' in keys else "",
            parent_cycle_id=row['parent_cycle_id'] if 'parent_cycle_id' in keys else None
        )
    
    def create_moon_cycle(self, cycle: MoonCycle) -> int:
        """目標サイクルを作成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO moon_cycles (cycle_start, cycle_end, goal, review, target_task_count, 
                completed_task_count, status, self_rating, good_points, improvement_points, 
                next_actions, parent_cycle_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cycle.cycle_start, cycle.cycle_end, cycle.goal, cycle.review, 
              cycle.target_task_count, cycle.completed_task_count, cycle.status,
              cycle.self_rating, cycle.good_points, cycle.improvement_points,
              cycle.next_actions, cycle.parent_cycle_id))
        cycle_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return cycle_id
    
    def update_moon_cycle(self, cycle: MoonCycle):
        """目標サイクルを更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE moon_cycles SET 
                cycle_start = ?, cycle_end = ?, goal = ?, review = ?,
                target_task_count = ?, completed_task_count = ?, status = ?,
                self_rating = ?, good_points = ?, improvement_points = ?,
                next_actions = ?, parent_cycle_id = ?
            WHERE id = ?
        """, (cycle.cycle_start, cycle.cycle_end, cycle.goal, cycle.review,
              cycle.target_task_count, cycle.completed_task_count, cycle.status,
              cycle.self_rating, cycle.good_points, cycle.improvement_points,
              cycle.next_actions, cycle.parent_cycle_id, cycle.id))
        conn.commit()
        conn.close()
    
    def delete_moon_cycle(self, cycle_id: int):
        """目標サイクルを削除（関連タスクも削除）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cycle_tasks WHERE cycle_id = ?", (cycle_id,))
        cursor.execute("DELETE FROM moon_cycles WHERE id = ?", (cycle_id,))
        conn.commit()
        conn.close()
    
    def increment_cycle_progress(self, cycle_id: int):
        """サイクルの完了タスク数をインクリメント"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE moon_cycles SET completed_task_count = completed_task_count + 1
            WHERE id = ?
        """, (cycle_id,))
        conn.commit()
        conn.close()
    
    # ===== CycleTasks操作 =====
    
    def add_task_to_cycle(self, cycle_id: int, task_id: int):
        """タスクをサイクルに追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 重複チェック
        cursor.execute("""
            SELECT id FROM cycle_tasks WHERE cycle_id = ? AND task_id = ?
        """, (cycle_id, task_id))
        if cursor.fetchone():
            conn.close()
            return
        cursor.execute("""
            INSERT INTO cycle_tasks (cycle_id, task_id, is_completed)
            VALUES (?, ?, 0)
        """, (cycle_id, task_id))
        conn.commit()
        conn.close()
    
    def remove_task_from_cycle(self, cycle_id: int, task_id: int):
        """タスクをサイクルから削除"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM cycle_tasks WHERE cycle_id = ? AND task_id = ?
        """, (cycle_id, task_id))
        conn.commit()
        conn.close()
    
    def get_cycle_tasks(self, cycle_id: int) -> List[Task]:
        """サイクルに紐付けられたタスクを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, ct.is_completed as cycle_completed FROM tasks t
            JOIN cycle_tasks ct ON t.id = ct.task_id
            WHERE ct.cycle_id = ?
            ORDER BY ct.id ASC
        """, (cycle_id,))
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            task = Task(
                id=row['id'],
                title=row['title'],
                category=row['category'],
                difficulty=row['difficulty'],
                duration=row['duration'],
                break_duration=row['break_duration'],
                priority=row['priority'],
                status=row['status'],
                created_at=row['created_at'],
                completed_at=row['completed_at']
            )
            # サイクル内での完了状態を追加属性として設定
            task._cycle_completed = bool(row['cycle_completed'])
            tasks.append(task)
        return tasks
    
    def complete_cycle_task(self, cycle_id: int, task_id: int):
        """サイクル内のタスクを完了としてマーク（進捗もインクリメント）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 既に完了していないか確認
        cursor.execute("""
            SELECT is_completed FROM cycle_tasks WHERE cycle_id = ? AND task_id = ?
        """, (cycle_id, task_id))
        row = cursor.fetchone()
        
        if row and not row['is_completed']:
            # タスクを完了としてマーク
            cursor.execute("""
                UPDATE cycle_tasks SET is_completed = 1, completed_at = ?
                WHERE cycle_id = ? AND task_id = ?
            """, (datetime.now(), cycle_id, task_id))
            
            # サイクルの進捗をインクリメント
            cursor.execute("""
                UPDATE moon_cycles SET completed_task_count = completed_task_count + 1
                WHERE id = ?
            """, (cycle_id,))
            
            conn.commit()
        conn.close()
    
    def is_task_in_active_cycle(self, task_id: int) -> Optional[int]:
        """タスクがアクティブなサイクルに含まれているか確認。含まれていればcycle_idを返す"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ct.cycle_id FROM cycle_tasks ct
            JOIN moon_cycles mc ON ct.cycle_id = mc.id
            WHERE ct.task_id = ? AND mc.status = 'active' AND ct.is_completed = 0
        """, (task_id,))
        row = cursor.fetchone()
        conn.close()
        return row['cycle_id'] if row else None
    
    def delete_cycle_tasks(self, cycle_id: int):
        """サイクルに紐付けられた全タスク関連を削除"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cycle_tasks WHERE cycle_id = ?", (cycle_id,))
        conn.commit()
        conn.close()
    
    # ===== Lifestyle Settings 操作 =====
    
    def _init_default_lifestyle(self):
        """デフォルトの生活設定を作成"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM lifestyle_settings")
        count = cursor.fetchone()['count']
        
        if count == 0:
            cursor.execute("""
                INSERT INTO lifestyle_settings (wake_time, sleep_time, min_sleep_hours,
                    bath_time, bath_duration, breakfast_time, lunch_time, dinner_time, meal_duration)
                VALUES ('07:00', '23:00', 7, '21:00', 30, '07:30', '12:00', '19:00', 30)
            """)
            conn.commit()
        conn.close()
    
    def get_lifestyle_settings(self) -> LifestyleSettings:
        """生活設定を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lifestyle_settings LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return LifestyleSettings(
                id=row['id'],
                wake_time=row['wake_time'],
                sleep_time=row['sleep_time'],
                min_sleep_hours=row['min_sleep_hours'],
                bath_time=row['bath_time'],
                bath_duration=row['bath_duration'],
                breakfast_time=row['breakfast_time'],
                lunch_time=row['lunch_time'],
                dinner_time=row['dinner_time'],
                meal_duration=row['meal_duration']
            )
        return LifestyleSettings()
    
    def update_lifestyle_settings(self, settings: LifestyleSettings):
        """生活設定を更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE lifestyle_settings SET
                wake_time = ?,
                sleep_time = ?,
                min_sleep_hours = ?,
                bath_time = ?,
                bath_duration = ?,
                breakfast_time = ?,
                lunch_time = ?,
                dinner_time = ?,
                meal_duration = ?
            WHERE id = 1
        """, (
            settings.wake_time,
            settings.sleep_time,
            settings.min_sleep_hours,
            settings.bath_time,
            settings.bath_duration,
            settings.breakfast_time,
            settings.lunch_time,
            settings.dinner_time,
            settings.meal_duration
        ))
        conn.commit()
        conn.close()
    
    # ===== ゲーミフィケーション =====
    
    def get_streak_data(self) -> dict:
        """連続達成ストリークを計算"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 完了タスクの日付を取得（activity_logから）
        cursor.execute("""
            SELECT DISTINCT DATE(timestamp) as completed_date
            FROM activity_log
            WHERE action = 'completed'
            ORDER BY completed_date DESC
        """)
        dates = [row['completed_date'] for row in cursor.fetchall()]
        conn.close()
        
        if not dates:
            return {"current_streak": 0, "max_streak": 0, "total_days": 0}
        
        # ストリーク計算
        from datetime import date, timedelta
        today = date.today()
        
        current_streak = 0
        max_streak = 0
        temp_streak = 0
        prev_date = None
        
        for d in dates:
            if isinstance(d, str):
                d = date.fromisoformat(d)
            
            if prev_date is None:
                temp_streak = 1
                # 今日または昨日から始まっていれば現在のストリーク
                if d == today or d == today - timedelta(days=1):
                    current_streak = temp_streak
            else:
                if prev_date - d == timedelta(days=1):
                    temp_streak += 1
                    if prev_date >= today - timedelta(days=1):
                        current_streak = temp_streak
                else:
                    max_streak = max(max_streak, temp_streak)
                    temp_streak = 1
            
            prev_date = d
        
        max_streak = max(max_streak, temp_streak)
        
        return {
            "current_streak": current_streak,
            "max_streak": max_streak,
            "total_days": len(dates)
        }
    
    def get_weekly_stats(self) -> dict:
        """週間統計を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        from datetime import date, timedelta
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        # 今週の完了タスク数
        cursor.execute("""
            SELECT COUNT(*) as count FROM activity_log
            WHERE action = 'completed' AND DATE(timestamp) >= ?
        """, (week_start.isoformat(),))
        this_week = cursor.fetchone()['count']
        
        # 先週の完了タスク数
        last_week_start = week_start - timedelta(days=7)
        cursor.execute("""
            SELECT COUNT(*) as count FROM activity_log
            WHERE action = 'completed' AND DATE(timestamp) >= ? AND DATE(timestamp) < ?
        """, (last_week_start.isoformat(), week_start.isoformat()))
        last_week = cursor.fetchone()['count']
        
        # 曜日別完了数
        cursor.execute("""
            SELECT strftime('%w', timestamp) as dow, COUNT(*) as count
            FROM activity_log
            WHERE action = 'completed' AND DATE(timestamp) >= ?
            GROUP BY dow
        """, (week_start.isoformat(),))
        daily = {str(i): 0 for i in range(7)}
        for row in cursor.fetchall():
            daily[row['dow']] = row['count']
        
        conn.close()
        
        return {
            "this_week": this_week,
            "last_week": last_week,
            "change": this_week - last_week,
            "daily": daily
        }
    
    # ===== プレゼント図鑑 =====
    
    def add_present(self, creature_id: int, name: str, emoji: str, description: str):
        """プレゼントを図鑑に追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO present_collection (creature_id, name, emoji, description)
            VALUES (?, ?, ?, ?)
        """, (creature_id, name, emoji, description))
        conn.commit()
        conn.close()
    
    def get_all_presents(self) -> list:
        """全プレゼントを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM present_collection ORDER BY received_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_unique_presents(self) -> list:
        """ユニークなプレゼント種類を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, emoji, description, COUNT(*) as count, MIN(received_at) as first_received
            FROM present_collection
            GROUP BY name
            ORDER BY first_received
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ===== 思い出日記 =====
    
    def add_diary_entry(self, creature_id: int, entry_type: str, content: str):
        """日記エントリを追加"""
        from datetime import date
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO creature_diary (creature_id, entry_date, entry_type, content)
            VALUES (?, ?, ?, ?)
        """, (creature_id, date.today().isoformat(), entry_type, content))
        conn.commit()
        conn.close()
    
    def get_diary_entries(self, creature_id: int = None) -> list:
        """日記エントリを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if creature_id:
            cursor.execute("""
                SELECT * FROM creature_diary WHERE creature_id = ? ORDER BY entry_date DESC
            """, (creature_id,))
        else:
            cursor.execute("SELECT * FROM creature_diary ORDER BY entry_date DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    # ===== 生活設定 =====
    
    def get_lifestyle_settings(self) -> Optional[LifestyleSettings]:
        """生活設定を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lifestyle_settings LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return LifestyleSettings()  # デフォルト値
        
        return LifestyleSettings(
            wake_time=row['wake_time'] if 'wake_time' in row.keys() else '07:00',
            sleep_time=row['sleep_time'] if 'sleep_time' in row.keys() else '23:00',
            breakfast_time=row['breakfast_time'] if 'breakfast_time' in row.keys() else '07:30',
            lunch_time=row['lunch_time'] if 'lunch_time' in row.keys() else '12:00',
            dinner_time=row['dinner_time'] if 'dinner_time' in row.keys() else '19:00',
            bath_time=row['bath_time'] if 'bath_time' in row.keys() else '21:00',
            min_sleep_hours=row['min_sleep_hours'] if 'min_sleep_hours' in row.keys() else 7,
            bath_duration=row['bath_duration'] if 'bath_duration' in row.keys() else 30,
            meal_duration=row['meal_duration'] if 'meal_duration' in row.keys() else 30
        )
    
    def save_lifestyle_settings(self, settings: LifestyleSettings):
        """生活設定を保存"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # テーブルが存在しない場合は作成
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lifestyle_settings (
                id INTEGER PRIMARY KEY,
                wake_time TEXT,
                sleep_time TEXT,
                breakfast_time TEXT,
                lunch_time TEXT,
                dinner_time TEXT,
                bath_time TEXT,
                min_sleep_hours INTEGER DEFAULT 7,
                bath_duration INTEGER DEFAULT 30,
                meal_duration INTEGER DEFAULT 30
            )
        """)
        
        # 既存の設定を削除して新しく挿入
        cursor.execute("DELETE FROM lifestyle_settings")
        cursor.execute("""
            INSERT INTO lifestyle_settings 
            (wake_time, sleep_time, breakfast_time, lunch_time, dinner_time, bath_time, min_sleep_hours, bath_duration, meal_duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            settings.wake_time,
            settings.sleep_time,
            settings.breakfast_time,
            settings.lunch_time,
            settings.dinner_time,
            settings.bath_time,
            settings.min_sleep_hours,
            settings.bath_duration,
            settings.meal_duration
        ))
        conn.commit()
        conn.close()
    
    # ===== 目標サイクル追加メソッド =====
    
    def complete_moon_cycle(self, cycle_id: int, self_rating: int = 0, 
                           good_points: str = "", improvement_points: str = "", next_actions: str = ""):
        """サイクルを完了"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE moon_cycles 
            SET status = 'completed',
                review = ?
            WHERE id = ?
        """, (f"評価:{self_rating}/5\n良かった点:{good_points}\n改善点:{improvement_points}\n次のアクション:{next_actions}", cycle_id))
        conn.commit()
        conn.close()
    
    def delete_moon_cycle(self, cycle_id: int):
        """サイクルを削除"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 関連するタスクを削除
        cursor.execute("DELETE FROM cycle_tasks WHERE cycle_id = ?", (cycle_id,))
        # サイクル自体を削除
        cursor.execute("DELETE FROM moon_cycles WHERE id = ?", (cycle_id,))
        conn.commit()
        conn.close()
    
    # ===== 生命体作成 =====
    
    def create_creature(self, name: str) -> Creature:
        """新しい生命体を作成"""
        from datetime import datetime
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO creatures (name, mood, energy, evolution_stage, last_interaction, created_at, status)
            VALUES (?, 50, 50, 1, ?, ?, 'active')
        """, (name, now, now))
        
        creature_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return Creature(
            id=creature_id,
            name=name,
            mood=50,
            energy=50,
            evolution_stage=1,
            last_interaction=now,
            created_at=now,
            status='active'
        )

