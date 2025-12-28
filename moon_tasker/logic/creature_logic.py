"""
生命体育成ロジック（傍観者正義発動版）
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from ..models import Creature
from ..database import Database
import random


class CreatureSystem:
    """生命体育成システム - 感情に訴えかける版"""
    
    # 進化段階の定義
    EVOLUTION_STAGES = {
        1: {"name": "たまご", "emoji": "🥚", "worst_state": "petrified"},
        2: {"name": "ほしのあかちゃん", "emoji": "⭐", "worst_state": "petrified"},
        3: {"name": "ほし", "emoji": "🌟", "worst_state": "runaway"},
        4: {"name": "こうさぎ", "emoji": "🐰", "worst_state": "runaway"},
        5: {"name": "つき", "emoji": "🌙", "worst_state": "desperate"},  # 消えない
    }
    
    # 形態×感情ごとのセリフと様子（ちいかわモブ風）
    # speech: ～や…！を使った非言語的表現
    # desc: （様子を表す描写）
    STAGE_EMOTIONS = {
        1: {  # たまご
            "overjoyed": {"speech": "～～～♪", "desc": "殻がぴかぴか光っています"},
            "happy": {"speech": "～♪", "desc": "嬉しそうに揺れています"},
            "content": {"speech": "…", "desc": "静かに温まっています"},
            "worried": {"speech": "……", "desc": "少し冷たくなっています"},
            "sad": {"speech": "…………", "desc": "震えています"},
            "desperate": {"speech": "………………", "desc": "ひび割れが見えます"},
            "petrified": {"speech": "", "desc": "石のように動きません…"},
        },
        2: {  # ほしのあかちゃん
            "overjoyed": {"speech": "～～！", "desc": "きらきら輝いて跳ねています"},
            "happy": {"speech": "～♪", "desc": "嬉しそうにあなたを見ています"},
            "content": {"speech": "…～", "desc": "穏やかに光っています"},
            "worried": {"speech": "……？", "desc": "不安そうにあなたを探しています"},
            "sad": {"speech": "…………", "desc": "光が弱くなっています"},
            "desperate": {"speech": "………………", "desc": "消えそうなほど儚く光っています"},
            "petrified": {"speech": "", "desc": "光を失い、石のようになりました…"},
        },
        3: {  # ほし
            "overjoyed": {"speech": "～～～！！", "desc": "眩しいほど輝いて飛び回っています"},
            "happy": {"speech": "～！", "desc": "楽しそうにくるくる回っています"},
            "content": {"speech": "…～♪", "desc": "穏やかに浮かんでいます"},
            "worried": {"speech": "……", "desc": "心配そうにあなたのそばにいます"},
            "sad": {"speech": "…………", "desc": "悲しそうに沈んでいます"},
            "desperate": {"speech": "………………", "desc": "あなたを思って泣いているようです"},
            "runaway": {"speech": "", "desc": "寂しさに耐えられず、どこかへ行ってしまいました…"},
        },
        4: {  # こうさぎ
            "overjoyed": {"speech": "～～！！", "desc": "ぴょんぴょん跳ねて喜んでいます"},
            "happy": {"speech": "～♪", "desc": "尻尾を振って嬉しそうです"},
            "content": {"speech": "…～", "desc": "のんびりくつろいでいます"},
            "worried": {"speech": "……？", "desc": "寂しそうにあなたを待っています"},
            "sad": {"speech": "…………", "desc": "耳を垂れてしょんぼりしています"},
            "desperate": {"speech": "………………", "desc": "うずくまって震えています"},
            "runaway": {"speech": "", "desc": "悲しみに耐えられず、家出してしまいました…"},
        },
        5: {  # つき
            "overjoyed": {"speech": "～～～♪♪", "desc": "満月のように輝いています"},
            "happy": {"speech": "～♪", "desc": "優しく微笑んでいるようです"},
            "content": {"speech": "…～", "desc": "静かにあなたを見守っています"},
            "worried": {"speech": "……", "desc": "少し曇って心配しています"},
            "sad": {"speech": "…………", "desc": "悲しそうに欠けています"},
            "desperate": {"speech": "………………", "desc": "それでもあなたのそばにいます"},
        },
    }
    
    # タスク完了時のプレゼント（健気なお礼）
    SMALL_PRESENTS = [
        ("小石", "✨🪨", "どこかで拾った宝物みたい"),
        ("変な形の葉っぱ", "🍃✨", "一生懸命選んでくれた"),
        ("光る砂", "✨", "キラキラしてる…！"),
        ("お花のかけら", "🌸", "ちょっと枯れてるけど…"),
        ("謎の木の実", "🌰", "食べられるかは不明"),
        ("ボタン", "🔘", "どこで見つけたの…？"),
        ("星のかけら", "⭐", "夜空から落ちてきたらしい"),
        ("青い羽根", "🪶", "青くてきれい"),
        ("まるい石", "⚪", "すべすべで気持ちいい"),
        ("透明な欠片", "💎", "ガラスかな…宝石かな…"),
    ]
    
    # 放置時のセリフ（時間経過で変化）
    NEGLECT_MESSAGES = {
        0: [],  # 正常
        6: ["……", "…～…"],
        12: ["………", "……～……"],
        24: ["…………", "………………"],
        48: ["……………………", "………………………"],
        72: ["…………………………………", "……………………………………"],
    }
    
    def __init__(self, db: Database):
        self.db = db
        self.last_present: Optional[Tuple[str, str, str]] = None
    
    def get_creature(self) -> Optional[Creature]:
        """現在の生命体を取得"""
        return self.db.get_creature()
    
    def get_stage_info(self, stage: int) -> dict:
        """進化段階の情報を取得"""
        return self.EVOLUTION_STAGES.get(stage, self.EVOLUTION_STAGES[1])
    
    def on_task_completed(self, difficulty: int = 1):
        """タスク完了時の処理（プレゼント付き）"""
        creature = self.get_creature()
        if not creature:
            return
        
        # 難易度に応じてパラメータ上昇
        mood_increase = 8 * difficulty
        energy_increase = 5 * difficulty
        
        creature.mood = min(100, creature.mood + mood_increase)
        creature.energy = min(100, creature.energy + energy_increase)
        
        # 進化判定
        self._check_evolution(creature)
        
        # プレゼントをランダムで選ぶ（20%の確率）
        if random.random() < 0.2:
            self.last_present = random.choice(self.SMALL_PRESENTS)
        else:
            self.last_present = None
        
        self.db.update_creature(creature)
    
    def on_task_failed(self):
        """タスク失敗時の処理"""
        creature = self.get_creature()
        if not creature:
            return
        
        # 機嫌が下がる
        creature.mood = max(0, creature.mood - 15)
        creature.energy = max(0, creature.energy - 8)
        
        self.db.update_creature(creature)
    
    def check_neglect(self) -> Tuple[int, str]:
        """放置チェック（経過時間と状態を返す）"""
        creature = self.get_creature()
        if not creature or not creature.last_interaction:
            return 0, ""
        
        # 最後のインタラクションから経過時間を計算
        now = datetime.now()
        try:
            if isinstance(creature.last_interaction, str):
                last_time = datetime.fromisoformat(creature.last_interaction)
            else:
                last_time = creature.last_interaction
        except:
            return 0, ""
        
        hours_passed = (now - last_time).total_seconds() / 3600
        
        # 6時間以上放置で機嫌低下
        if hours_passed > 6:
            decay = int(hours_passed / 6) * 5  # より急激に低下
            creature.mood = max(0, creature.mood - decay)
            creature.energy = max(0, creature.energy - decay)
            
            # 死亡/家出判定（mood=0の場合）
            if creature.mood <= 0 and creature.status == "active":
                self._handle_creature_end(creature)
            else:
                self.db.update_creature(creature)
        
        return int(hours_passed), self._get_neglect_message(hours_passed)
    
    def _handle_creature_end(self, creature: Creature):
        """生命体の終了処理（死亡/家出）"""
        stage = creature.evolution_stage
        now = datetime.now()
        
        # つきは消えない
        if stage == 5:
            creature.mood = 5  # 最低限の機嫌を維持
            self.db.update_creature(creature)
            return
        
        # 石化or家出
        if stage <= 2:
            creature.status = "dead"  # 石化
        else:
            creature.status = "runaway"  # 家出
        
        creature.ended_at = now
        # 1ヶ月後に次の生命体を育てられる
        creature.cooldown_until = now + timedelta(days=30)
        
        self.db.update_creature(creature)
    
    def check_evolution_complete(self, creature: Creature) -> bool:
        """つきに進化したかチェックして完了処理"""
        if creature.evolution_stage == 5 and creature.status == "active":
            creature.status = "completed"
            self.db.update_creature(creature)
            return True
        return False
    
    def _get_neglect_message(self, hours: float) -> str:
        """放置時間に応じたメッセージを取得"""
        messages = []
        for threshold in sorted(self.NEGLECT_MESSAGES.keys(), reverse=True):
            if hours >= threshold:
                messages = self.NEGLECT_MESSAGES[threshold]
                break
        
        if messages:
            return random.choice(messages)
        return ""
    
    def _get_emotion_name(self, creature: Creature) -> str:
        """機嫌から感情名を取得"""
        stage_info = self.get_stage_info(creature.evolution_stage)
        worst_state = stage_info.get("worst_state", "desperate")
        
        if creature.mood >= 90:
            return "overjoyed"
        elif creature.mood >= 70:
            return "happy"
        elif creature.mood >= 50:
            return "content"
        elif creature.mood >= 30:
            return "worried"
        elif creature.mood >= 15:
            return "sad"
        elif creature.mood >= 5:
            return "desperate"
        else:
            # 最悪の状態（進化段階により異なる）
            if creature.evolution_stage == 5:
                return "desperate"  # つきは消えない
            return worst_state
    
    def get_emotion_state(self, creature: Creature) -> dict:
        """現在の感情状態を取得"""
        stage = creature.evolution_stage
        emotion_name = self._get_emotion_name(creature)
        
        stage_emotions = self.STAGE_EMOTIONS.get(stage, self.STAGE_EMOTIONS[1])
        emotion_data = stage_emotions.get(emotion_name, stage_emotions.get("content"))
        
        return {
            "name": emotion_name,
            "speech": emotion_data["speech"],
            "desc": emotion_data["desc"],
            "mood": creature.mood,
            "stage": stage
        }
    
    def get_creature_posture(self, creature: Creature) -> str:
        """機嫌に応じた姿勢を取得（様子描写として使用）"""
        emotion = self.get_emotion_state(creature)
        return emotion["desc"]
    
    def _check_evolution(self, creature: Creature):
        """進化条件をチェック"""
        completed_tasks = self.db.get_completed_task_count()
        
        # 進化条件（タスク完了数とパラメータ）
        evolution_thresholds = {
            2: (5, 60, 60),    # ほしのあかちゃん
            3: (15, 70, 70),   # ほし
            4: (30, 80, 80),   # こうさぎ
            5: (50, 90, 90),   # つき
        }
        
        for stage, (tasks_req, mood_req, energy_req) in evolution_thresholds.items():
            if creature.evolution_stage < stage:
                if (completed_tasks >= tasks_req and 
                    creature.mood >= mood_req and 
                    creature.energy >= energy_req):
                    creature.evolution_stage = stage
                    break
    
    def get_creature_emoji(self, creature: Creature) -> str:
        """進化段階の絵文字を返す（フォールバック用）"""
        stage_info = self.get_stage_info(creature.evolution_stage)
        return stage_info.get("emoji", "🥚")
    
    def get_stage_name(self, creature: Creature) -> str:
        """進化段階の名前を返す"""
        stage_info = self.get_stage_info(creature.evolution_stage)
        return stage_info["name"]
    
    def get_mood_description(self, mood: int) -> str:
        """機嫌の説明テキスト（様子描写）"""
        # この関数はlegacy用、get_emotion_stateを使用することを推奨
        if mood >= 90:
            return "とても嬉しそうです"
        elif mood >= 70:
            return "嬉しそうです"
        elif mood >= 50:
            return "穏やかです"
        elif mood >= 30:
            return "少し寂しそうです"
        elif mood >= 15:
            return "悲しんでいます"
        else:
            return "とても辛そうです"
    
    def is_in_danger(self, creature: Creature) -> bool:
        """生命体が危険な状態かどうか"""
        return creature.mood < 20 or creature.energy < 20
    
    def get_warning_message(self, creature: Creature) -> Optional[str]:
        """緊急警告メッセージを取得（進化段階に応じて変化）"""
        stage = creature.evolution_stage
        
        if creature.mood < 10:
            if stage <= 2:
                return "⚠️ 石になってしまいそうです！"
            elif stage <= 4:
                return "⚠️ どこかへ行ってしまいそうです！"
            else:
                return "😢 とても辛そうですが、そばにいてくれています"
        elif creature.mood < 20:
            return "😢 とても悲しんでいます…"
        elif creature.mood < 30:
            return "💧 寂しがっています"
        return None
    
    def get_image_filename(self, creature: Creature) -> str:
        """画像ファイル名を取得"""
        emotion_name = self._get_emotion_name(creature)
        stage = creature.evolution_stage
        return f"stage{stage}_{emotion_name}.png"
