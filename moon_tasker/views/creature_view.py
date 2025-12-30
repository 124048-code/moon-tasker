"""
生命体育成画面（養育選択制・誓約付き）
"""
import flet as ft
import re
from datetime import datetime, timedelta
from ..database import Database
from ..logic.creature_logic import CreatureSystem


class CreatureView(ft.Column):
    """生命体育成画面"""
    
    # カタカナ→ひらがな変換マップ
    KATAKANA_TO_HIRAGANA = str.maketrans(
        'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンァィゥェォッャュョガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ',
        'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんぁぃぅぇぉっゃゅょがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽゔ'
    )
    
    # NGワードリスト（ひらがなで統一）
    NG_WORDS = [
        # === 性的な言葉 ===
        "ちんこ", "ちんちん", "ちんぽ", "ちんぽこ", "おちんちん",
        "まんこ", "まんまん", "おまんこ", "おめこ", "おまん",
        "おっぱい", "ぱいおつ", "ぱいぱい", "おっぱ",
        "せっくす", "えっち", "えろ", "えろい",
        "ふぇら", "ふぇらちお",
        "おなにー", "しこしこ", "しこる",
        "やりまん", "やりちん", "びっち",
        "せいし", "ざーめん",
        "こうび", "はめる", "やる",
        "ぼっき", "きんたま", "たまきん",
        "あなる", "けつあな",
        "ぬーど", "はだか",
        # === 英語の性的表現 ===
        "penis", "dick", "cock", "pussy", "vagina", "boobs", "tits",
        "sex", "fuck", "fucking", "shit", "ass", "bitch", "whore",
        "porn", "porno", "hentai", "erotic",
        # === 悪口・侮辱 ===
        "ばか", "ばーか", "ばかやろう", "ばかたれ",
        "あほ", "あほう", "あほんだら",
        "まぬけ", "のろま", "うすのろ", "とんま",
        "くず", "かす", "ごみ", "くそ", "うんこ", "うんち",
        "ぶす", "ぶさいく", "ぶさ",
        "でぶ", "でぶす", "ぴざ",
        "はげ", "はげあたま",
        "ちび",
        "きもい", "きしょい", "きしょ", "きっしょ",
        "うざい", "うざ", "うぜー", "うぜえ",
        "くさい", "くさ", "くっさ",
        "だせー", "だせえ", "ださ",
        "きえろ", "うせろ", "どっかいけ",
        "しつこい",
        # === 暴力・脅迫 ===
        "しね", "しねよ", "しんでくれ", "しんでほしい",
        "ころす", "ころしてやる", "ころすぞ",
        "くたばれ", "くたばりやがれ",
        "ぶっころす", "ぶちころす",
        "じごくにおちろ", "のろってやる",
        # === 差別語 ===
        "がいじ", "ちてきしょうがい", "きちがい", "きち",
        "しょうがいしゃ", "かたわ", "めくら", "つんぼ", "おし",
        "ちょん", "しな", "にがー",
        "ほいど", "えた", "ひにん",
        # === ネットスラング系悪口 ===
        "ks", "kz", "gz", "gm",
        "ちーぎゅう", "ちー牛",
        "いんきゃ", "いんきゃら",
        "こどおじ", "こどおば",
        "にーと", "ひきこもり",
        "おわこん", "ざこ", "よわ",
        "しょぼ", "しょぼい",
        "くさ", "w", "わら",  # 単体は避ける
        "あたおか", "がいじ",
        "ぷぎゃー", "ざまあ", "ざまぁ", "ざまみろ",
        "おつむよわ", "のうたりん",
        # === その他不適切 ===
        "やくざ", "ちんぴら", "はんしゃ", "やくぶつ",
        "どらっぐ", "まやく", "かくせいざい", "たいま", "しゃぶ",
        "いじめ", "いじめる",
    ]
    
    def __init__(self, db: Database, page: ft.Page):
        super().__init__()
        self.db = db
        self._page = page
        self.creature_system = CreatureSystem(db)
        self.spacing = 15
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO
        
        self._build()
    
    def _build(self):
        """画面を構築"""
        self.controls.clear()
        
        creature = self.creature_system.get_creature()
        
        # 生命体がいない、またはstatusがnoneの場合
        if not creature or creature.status == "none":
            self._build_no_creature_view()
            return
        
        # 死亡/家出でクールダウン中の場合
        if creature.status in ["dead", "runaway"]:
            if creature.cooldown_until:
                cooldown_date = creature.cooldown_until
                if isinstance(cooldown_date, str):
                    cooldown_date = datetime.fromisoformat(cooldown_date)
                if datetime.now() < cooldown_date:
                    self._build_cooldown_view(creature, cooldown_date)
                    return
            # クールダウン終了していたら新しい生命体を育てられる
            self._build_no_creature_view()
            return
        
        # 完了（つき達成）の場合
        if creature.status == "completed":
            self._build_completed_view(creature)
            return
        
        # アクティブな生命体がいる場合
        self._build_active_creature_view(creature)
    
    def _build_no_creature_view(self):
        """生命体がいない時の画面"""
        title = ft.Text("生命体 🐾", size=28, weight=ft.FontWeight.BOLD)
        
        # 説明
        intro_card = ft.Container(
            content=ft.Column([
                ft.Text("🌙 生命体を育てる", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("タスクを完了すると、この子のごはんになります。", size=14),
                ft.Text("大切に育てると進化していきます。", size=14),
                ft.Text("", size=8),
                ft.Text("⚠️ 放置すると寂しがって...", size=14, color="#ffb74d"),
                ft.Text("石になったり、家出してしまうかも。", size=14, color="#ffb74d"),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 育て始めるボタン
        start_button = ft.ElevatedButton(
            "🥚 生命体を育て始める",
            bgcolor="#4caf50",
            color="white",
            on_click=lambda e: self._show_pledge_dialog()
        )
        
        self.controls = [
            title,
            ft.Container(height=20),
            intro_card,
            ft.Container(height=30),
            ft.Container(content=start_button),
        ]
    
    def _build_cooldown_view(self, creature, cooldown_date):
        """クールダウン中の画面"""
        title = ft.Text("生命体 🐾", size=28, weight=ft.FontWeight.BOLD)
        
        remaining_days = (cooldown_date - datetime.now()).days + 1
        
        message = ""
        if creature.status == "dead":
            message = "前の生命体は石になってしまいました..."
        else:
            message = "前の生命体は家出してしまいました..."
        
        cooldown_card = ft.Container(
            content=ft.Column([
                ft.Text("😢", size=60, text_align=ft.TextAlign.CENTER),
                ft.Text(message, size=16, text_align=ft.TextAlign.CENTER),
                ft.Divider(height=20, color="transparent"),
                ft.Text("次に生命体を育てられるまで", size=14, color="#9e9e9e"),
                ft.Text(f"あと {remaining_days} 日", size=28, weight=ft.FontWeight.BOLD, color="#ff9800"),
                ft.Text(f"({cooldown_date.strftime('%Y年%m月%d日')} から)", size=12, color="#9e9e9e"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#3d2f1f",
            border_radius=10,
            padding=30
        )
        
        self.controls = [
            title,
            ft.Container(height=20),
            cooldown_card,
        ]
    
    def _build_completed_view(self, creature):
        """つき達成後の画面"""
        title = ft.Text("生命体 🐾", size=28, weight=ft.FontWeight.BOLD)
        
        completed_card = ft.Container(
            content=ft.Column([
                ft.Text("🌙✨", size=80, text_align=ft.TextAlign.CENTER),
                ft.Text(creature.name, size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(height=10, color="transparent"),
                ft.Text("つき に成長しました！", size=18, color="#ffc107"),
                ft.Text("これからもずっとあなたのそばにいます", size=14, color="#9e9e9e"),
                ft.Divider(height=20, color="transparent"),
                ft.Text("（つき は消えることなく、永遠にあなたを見守ります）", size=12, color="#64b5f6", italic=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e3a5f",
            border=ft.border.all(2, "#ffc107"),
            border_radius=15,
            padding=30
        )
        
        self.controls = [
            title,
            ft.Container(height=20),
            completed_card,
        ]
    
    def _build_active_creature_view(self, creature):
        """アクティブな生命体の画面"""
        # 放置チェック
        hours_passed, neglect_msg = self.creature_system.check_neglect()
        emotion = self.creature_system.get_emotion_state(creature)
        warning = self.creature_system.get_warning_message(creature)
        
        title = ft.Text("生命体 🐾", size=28, weight=ft.FontWeight.BOLD)
        
        # 緊急警告
        warning_card = None
        if warning:
            warning_card = ft.Container(
                content=ft.Row([
                    ft.Icon(name="warning_amber", color="#f44336", size=30),
                    ft.Text(warning, size=16, color="#f44336", weight=ft.FontWeight.BOLD),
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#3d1f1f",
                border_radius=10,
                padding=15
            )
        
        # 背景色
        if creature.mood >= 70:
            bg_color = "#1e3a5f"
            border_color = "#64b5f6"
        elif creature.mood >= 40:
            bg_color = "#3d3d1f"
            border_color = "#ffeb3b"
        elif creature.mood >= 20:
            bg_color = "#3d2f1f"
            border_color = "#ff9800"
        else:
            bg_color = "#3d1f1f"
            border_color = "#f44336"
        
        # 画像表示
        stage_name = self.creature_system.get_stage_name(creature)
        image_filename = self.creature_system.get_image_filename(creature)
        image_path = f"moon_tasker/assets/creature/{image_filename}"
        
        import os
        if os.path.exists(image_path):
            creature_visual = ft.Image(src=image_path, width=150, height=150, fit="contain")
        else:
            creature_visual = ft.Text(self.creature_system.get_creature_emoji(creature), size=100)
        
        creature_display = ft.Container(
            content=ft.Column([
                creature_visual,
                ft.Text(creature.name, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"{stage_name}（{creature.evolution_stage}/5）", size=14, color="#9e9e9e"),
                ft.Divider(height=10, color="transparent"),
                # セリフ
                ft.Container(
                    content=ft.Text(f'「{emotion["speech"]}」' if emotion["speech"] else "", size=20, color="#ffffff"),
                    bgcolor="#424242" if emotion["speech"] else "transparent",
                    border_radius=15,
                    padding=ft.padding.symmetric(horizontal=20, vertical=10) if emotion["speech"] else 0
                ) if emotion["speech"] else ft.Container(),
                # 様子
                ft.Text(f"（{emotion['desc']}）", size=14, color="#9e9e9e", italic=True),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=bg_color,
            border=ft.border.all(2, border_color),
            border_radius=15,
            padding=30
        )
        
        # 放置メッセージ
        neglect_card = None
        if neglect_msg and hours_passed >= 6:
            neglect_card = ft.Container(
                content=ft.Column([
                    ft.Text(f"⏰ 最後に会ってから {hours_passed} 時間経過", size=12, color="#9e9e9e"),
                    ft.Text(f'「{neglect_msg}」', size=16, color="#ffb74d", italic=True),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#2d2d1d",
                border_radius=10,
                padding=15
            )
        
        # パラメータ
        params_card = ft.Container(
            content=ft.Column([
                ft.Text("💖 パラメータ", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Text("機嫌", size=14, color="#9e9e9e"),
                ft.Row([
                    ft.ProgressBar(
                        value=creature.mood / 100,
                        color="#f06292" if creature.mood >= 30 else "#f44336",
                        bgcolor="#424242",
                        width=180
                    ),
                    ft.Text(f"{creature.mood}/100", size=14)
                ]),
                ft.Text("体力", size=14, color="#9e9e9e"),
                ft.Row([
                    ft.ProgressBar(
                        value=creature.energy / 100,
                        color="#81c784" if creature.energy >= 30 else "#ff9800",
                        bgcolor="#424242",
                        width=180
                    ),
                    ft.Text(f"{creature.energy}/100", size=14)
                ]),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # 進化条件
        evolution_card = ft.Container(
            content=ft.Column([
                ft.Text("✨ 進化条件", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                self._build_evolution_progress(creature),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=20
        )
        
        # プレゼント図鑑
        presents = self.db.get_unique_presents()
        present_items = []
        for p in presents[:6]:  # 最新6個を表示
            present_items.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(p['emoji'], size=24),
                        ft.Text(p['name'], size=10, text_align=ft.TextAlign.CENTER),
                        ft.Text(f"×{p['count']}", size=8, color="#9e9e9e"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                    width=60,
                    height=70,
                    bgcolor="#263238",
                    border_radius=8,
                    padding=5
                )
            )
        
        present_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("🎁 もらったもの", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"全{len(presents)}種類", size=12, color="#9e9e9e"),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(),
                ft.Row(present_items, wrap=True, spacing=5) if present_items else ft.Text("まだプレゼントはありません", size=12, color="#9e9e9e"),
            ]),
            bgcolor="#1e3a5f",
            border_radius=10,
            padding=15
        ) if creature else None
        
        controls = [title]
        if warning_card:
            controls.append(warning_card)
        controls.append(creature_display)
        if neglect_card:
            controls.append(neglect_card)
        controls.extend([params_card, evolution_card])
        if present_card:
            controls.append(present_card)
        
        self.controls = controls
    
    def _build_evolution_progress(self, creature):
        """進化進捗を表示"""
        completed_tasks = self.db.get_completed_task_count()
        
        stages = [
            (1, "🥚 たまご", 0, "最初の姿"),
            (2, "⭐ ???", 5, "5タスク完了"),
            (3, "🌟 ???", 15, "15タスク完了"),
            (4, "🐰 ???", 30, "30タスク完了"),
            (5, "🌙 ???", 50, "50タスク完了"),
        ]
        
        # 解放済みの名前
        unlocked_names = {
            2: "⭐ ほしのあかちゃん",
            3: "🌟 ほし",
            4: "🐰 こうさぎ",
            5: "🌙 つき",
        }
        
        items = []
        for stage, emoji, req, desc in stages:
            # 解放済みなら本当の名前を表示
            if creature.evolution_stage >= stage:
                display_name = unlocked_names.get(stage, emoji)
                color = "#81c784"
                icon = "✓"
            elif creature.evolution_stage == stage - 1:
                progress = f"({completed_tasks}/{req})"
                display_name = emoji  # まだ「???」
                color = "#64b5f6"
                icon = "→"
                desc = f"{desc} {progress}"
            else:
                display_name = emoji  # 「???」のまま
                color = "#757575"
                icon = "○"
            
            items.append(
                ft.Text(f"{icon} {display_name} {desc}", size=12, color=color)
            )
        
        return ft.Column(items, spacing=5)
    
    def _show_pledge_dialog(self):
        """誓約ダイアログを表示"""
        def on_agree(e):
            dialog.open = False
            self._page.update()
            self._show_name_input_dialog()
        
        def on_cancel(e):
            dialog.open = False
            self._page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("🌙 誓約", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("生命体を育てる前に、以下を約束してください。", size=14),
                    ft.Divider(height=15, color="transparent"),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("⚠️ この機能は心理的な効果が非常に高いです。", size=13, color="#ff9800"),
                            ft.Divider(height=10, color="transparent"),
                            ft.Text("✅ この子を大切に育てること", size=13),
                            ft.Text("✅ 虐待目的で育てないこと", size=13),
                            ft.Text("✅ 責任を持って最後まで見届けること", size=13),
                        ]),
                        bgcolor="#263238",
                        border_radius=10,
                        padding=15
                    ),
                    ft.Divider(height=15, color="transparent"),
                    ft.Text("この約束を守れますか？", size=14, weight=ft.FontWeight.BOLD),
                ]),
                width=300,
            ),
            actions=[
                ft.TextButton("やめる", on_click=on_cancel),
                ft.ElevatedButton(
                    "約束します",
                    bgcolor="#4caf50",
                    color="white",
                    on_click=on_agree
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self._page.dialog = dialog

        
        dialog.open = True

        
        self._page.update()
    
    def _show_name_input_dialog(self):
        """名前入力ダイアログを表示"""
        name_field = ft.TextField(
            label="名前を入力",
            hint_text="例: ルナ、ほしちゃん",
            max_length=20,
            width=250
        )
        error_text = ft.Text("", size=12, color="#f44336")
        
        def on_submit(e):
            name = name_field.value.strip()
            
            # バリデーション
            if not name:
                error_text.value = "名前を入力してください"
                self._page.update()
                return
            
            if len(name) < 1 or len(name) > 20:
                error_text.value = "1〜20文字で入力してください"
                self._page.update()
                return
            
            # NGワードチェック
            if self._contains_ng_word(name):
                error_text.value = "不適切な言葉が含まれています"
                self._page.update()
                return
            
            # 生命体を作成
            dialog.open = False
            self._page.update()
            self._create_new_creature(name)
        
        def on_cancel(e):
            dialog.open = False
            self._page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("🥚 名前をつけよう", size=20, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("この子の名前を決めてください。", size=14),
                    ft.Divider(height=10, color="transparent"),
                    name_field,
                    error_text,
                ]),
                width=280,
            ),
            actions=[
                ft.TextButton("キャンセル", on_click=on_cancel),
                ft.ElevatedButton(
                    "決定",
                    bgcolor="#4caf50",
                    color="white",
                    on_click=on_submit
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        self._page.dialog = dialog

        
        dialog.open = True

        
        self._page.update()
    
    def _normalize_text(self, text: str) -> str:
        """テキストを正規化（カタカナ→ひらがな、記号除去、小文字化）"""
        # カタカナをひらがなに変換
        result = text.translate(self.KATAKANA_TO_HIRAGANA)
        # アルファベットを小文字に
        result = result.lower()
        # 記号・空白を除去（回避策対策）
        result = re.sub(r'[・\s\-_\.。、！？!?,，.．]', '', result)
        return result
    
    def _contains_ng_word(self, text: str) -> bool:
        """NGワードが含まれているかチェック"""
        normalized = self._normalize_text(text)
        
        for ng in self.NG_WORDS:
            # NGワードも正規化してチェック
            ng_normalized = self._normalize_text(ng)
            if ng_normalized in normalized:
                return True
        return False
    
    def _create_new_creature(self, name: str):
        """新しい生命体を作成"""
        self.db.create_creature(name)
        
        # 画面を再構築
        self.controls.clear()
        self._build()
        self._page.update()
        
        # 歓迎メッセージ
        self._show_welcome_dialog(name)
    
    def _show_welcome_dialog(self, name: str):
        """歓迎ダイアログ"""
        def close_dialog(e):
            dialog.open = False
            self._page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"🥚 {name} が生まれました！", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🥚", size=80, text_align=ft.TextAlign.CENTER),
                    ft.Divider(height=10, color="transparent"),
                    ft.Text("大切に育ててあげてくださいね。", size=14, text_align=ft.TextAlign.CENTER),
                    ft.Text("タスクを完了すると、この子が喜びます。", size=14, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=260,
            ),
            actions=[
                ft.ElevatedButton(
                    "よろしくね！",
                    bgcolor="#4caf50",
                    color="white",
                    on_click=close_dialog
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self._page.dialog = dialog

        
        dialog.open = True

        
        self._page.update()
