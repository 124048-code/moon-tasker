"""
Moon Tasker - Flask Application
HTMX + Static CSS based web application (Full Feature Version)
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import os
import sys
import json

# Add moon_tasker to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from moon_tasker.database import Database
from moon_tasker.models import Task, Playlist, MoonCycle, LifestyleSettings
from moon_tasker.logic.creature_logic import CreatureSystem
from moon_tasker.logic.moon_cycle import MoonCycleCalculator
from moon_tasker.logic.badge_logic import BadgeSystem
from moon_tasker.logic.schedule_ai import ScheduleOptimizer, GeneticScheduleOptimizer

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'moon-tasker-secret-key-2024')

# Database instance
db = Database()
creature_system = CreatureSystem(db)
moon_calc = MoonCycleCalculator()
badge_system = BadgeSystem(db)


def get_creature_context(creature):
    """生命体のコンテキスト情報を取得"""
    if not creature or creature.status not in ["active", "completed"]:
        return {
            'creature': None,
            'emotion': None,
            'warning': None,
            'creature_image': None
        }
    
    creature_system.check_neglect()
    emotion = creature_system.get_emotion_state(creature)
    warning = creature_system.get_warning_message(creature)
    image_filename = creature_system.get_image_filename(creature)
    
    return {
        'creature': creature,
        'emotion': emotion,
        'warning': warning,
        'creature_image': f'/static/images/creature/{image_filename}'
    }


# ============ ROUTES ============

@app.route('/')
def home():
    """ホーム画面"""
    creature = creature_system.get_creature()
    moon_phase = moon_calc.get_moon_phase_name()
    moon_emoji = moon_calc.get_moon_emoji()
    
    tasks = db.get_all_tasks()
    pending_count = len([t for t in tasks if t.status == "pending"])
    completed_count = db.get_completed_task_count()
    
    streak_data = db.get_streak_data()
    
    ctx = get_creature_context(creature)
    
    return render_template('pages/home.html',
                         creature=ctx['creature'],
                         emotion=ctx['emotion'],
                         warning=ctx['warning'],
                         creature_image=ctx['creature_image'],
                         moon_phase=moon_phase,
                         moon_emoji=moon_emoji,
                         pending_count=pending_count,
                         completed_count=completed_count,
                         streak_data=streak_data)


@app.route('/timer')
def timer():
    """タイマー画面"""
    playlists = db.get_all_playlists()
    lifestyle = db.get_lifestyle_settings()
    return render_template('pages/timer.html',
                         playlists=playlists,
                         lifestyle=lifestyle)


@app.route('/timer/playlist/<int:playlist_id>/tasks')
def get_playlist_tasks(playlist_id):
    """プレイリストのタスク一覧を取得（HTMX用）"""
    tasks = db.get_playlist_tasks(playlist_id)
    
    # 日本標準時（JST、UTC+9）を使用
    from datetime import timezone
    JST = timezone(timedelta(hours=9))
    
    schedule = []
    time_cursor = datetime.now(JST)
    
    for idx, task in enumerate(tasks):
        is_last = idx == len(tasks) - 1
        # 最後のタスクは休憩時間をカット
        break_time = 0 if is_last else task.break_duration
        task_end = time_cursor + timedelta(minutes=task.duration + break_time)
        schedule.append({
            'task': task,
            'start': time_cursor.strftime('%H:%M'),
            'end': task_end.strftime('%H:%M')
        })
        time_cursor = task_end
    
    estimated_end = time_cursor.strftime('%H:%M')
    
    return render_template('partials/playlist_tasks.html',
                         tasks=tasks,
                         schedule=schedule,
                         estimated_end=estimated_end)


@app.route('/timer/complete', methods=['POST'])
def complete_task():
    """タスク完了処理"""
    task_id = request.form.get('task_id', type=int)
    difficulty = request.form.get('difficulty', 3, type=int)
    
    if task_id and task_id > 0:
        db.update_task_status(task_id, "completed")
        db.log_activity(task_id, "completed")
    
    creature_system.on_task_completed(difficulty)
    
    # バッジチェック
    newly_unlocked = badge_system.check_all_badges()
    
    # 新しいバッジをセッションに保存（星座図鑑で演出表示用）
    if newly_unlocked:
        new_badge_names = [b.name for b in newly_unlocked]
        existing = session.get('new_badges', [])
        session['new_badges'] = existing + new_badge_names
        
        # ログインユーザー: Supabaseにも保存
        user_id = session.get('user_id')
        if user_id:
            from moon_tasker.cloud.supabase_client import get_cloud_db
            cloud_db = get_cloud_db()
            for badge_name in new_badge_names:
                cloud_db.save_user_badge(user_id, badge_name)
    
    # 進化チェック
    creature = creature_system.get_creature()
    evolutions = []
    if creature:
        old_stage = creature.evolution_stage
        creature_system._check_evolution(creature)
        if creature.evolution_stage > old_stage:
            evolutions.append({
                'from': old_stage,
                'to': creature.evolution_stage,
                'name': creature_system.get_stage_name(creature)
            })
    
    # プレゼントチェック
    present = creature_system.last_present
    
    return jsonify({
        'success': True,
        'badges': [{'name': b.name, 'constellation': b.constellation_name} for b in newly_unlocked],
        'evolutions': evolutions,
        'present': {'name': present[0], 'emoji': present[1], 'desc': present[2]} if present else None
    })


@app.route('/playlist')
def playlist():
    """プレイリスト管理画面"""
    user_id = session.get('user_id')
    
    if user_id:
        # ログインユーザー: Supabaseからデータ取得
        from moon_tasker.cloud.supabase_client import get_cloud_db
        cloud_db = get_cloud_db()
        
        cloud_playlists = cloud_db.get_user_playlists(user_id)
        playlists = [type('Playlist', (), {'id': p['id'], 'name': p['name'], 'description': p.get('description', '')})() for p in cloud_playlists]
        
        cloud_tasks = cloud_db.get_user_tasks(user_id)
        tasks = [type('Task', (), {
            'id': t['id'], 'title': t['title'], 'duration': t.get('duration', 25),
            'break_duration': t.get('break_duration', 5), 'difficulty': t.get('difficulty', 3),
            'priority': t.get('priority', 0), 'status': t.get('status', 'pending')
        })() for t in cloud_tasks]
        pending_tasks = [t for t in tasks if t.status == 'pending']
        
        selected_id = request.args.get('selected')
        selected_tasks = []
        # クラウドプレイリストの場合はまだ実装なし
    else:
        # ゲスト: ローカルDBから取得
        playlists = db.get_all_playlists()
        tasks = db.get_all_tasks()
        pending_tasks = [t for t in tasks if t.status == "pending"]
        
        selected_id = request.args.get('selected', type=int)
        selected_tasks = []
        if selected_id:
            selected_tasks = db.get_playlist_tasks(selected_id)
    
    lifestyle = db.get_lifestyle_settings()
    
    return render_template('pages/playlist.html',
                         playlists=playlists,
                         pending_tasks=pending_tasks,
                         selected_id=selected_id,
                         selected_tasks=selected_tasks,
                         lifestyle=lifestyle,
                         is_logged_in=bool(user_id))


@app.route('/playlist/create', methods=['POST'])
def create_playlist():
    """プレイリスト作成"""
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('playlist'))
    
    user_id = session.get('user_id')
    if user_id:
        # ログインユーザー: Supabaseに保存
        from moon_tasker.cloud.supabase_client import get_cloud_db
        cloud_db = get_cloud_db()
        new_id = cloud_db.save_user_playlist(user_id, {'name': name, 'description': ''})
        return redirect(url_for('playlist', selected=new_id))
    else:
        # ゲスト: ローカルDBに保存
        pl = Playlist(name=name, description="")
        new_id = db.create_playlist(pl)
        return redirect(url_for('playlist', selected=new_id))


@app.route('/playlist/<playlist_id>/delete', methods=['POST'])
def delete_playlist(playlist_id):
    """プレイリスト削除"""
    user_id = session.get('user_id')
    if user_id:
        from moon_tasker.cloud.supabase_client import get_cloud_db
        cloud_db = get_cloud_db()
        cloud_db.delete_user_playlist(user_id, str(playlist_id))
    else:
        db.delete_playlist(playlist_id)
    return redirect(url_for('playlist'))


@app.route('/playlist/<playlist_id>/add/<task_id>', methods=['POST'])
def add_to_playlist(playlist_id, task_id):
    """タスクをプレイリストに追加"""
    user_id = session.get('user_id')
    if user_id:
        from moon_tasker.cloud.supabase_client import get_cloud_db
        cloud_db = get_cloud_db()
        cloud_db.add_task_to_playlist(playlist_id, task_id, 0)
    else:
        db.add_task_to_playlist(int(playlist_id), int(task_id))
    return redirect(url_for('playlist', selected=playlist_id))


@app.route('/playlist/<playlist_id>/remove/<task_id>', methods=['POST'])
def remove_from_playlist(playlist_id, task_id):
    """タスクをプレイリストから削除"""
    user_id = session.get('user_id')
    if user_id:
        from moon_tasker.cloud.supabase_client import get_cloud_db
        cloud_db = get_cloud_db()
        cloud_db.remove_task_from_playlist(playlist_id, task_id)
    else:
        db.remove_task_from_playlist(int(playlist_id), int(task_id))
    return redirect(url_for('playlist', selected=playlist_id))


@app.route('/playlist/<int:playlist_id>/move/<int:task_id>/<direction>', methods=['POST'])
def move_task_in_playlist(playlist_id, task_id, direction):
    """プレイリスト内でタスクを移動"""
    tasks = db.get_playlist_tasks(playlist_id)
    task_ids = [t.id for t in tasks]
    
    if task_id in task_ids:
        idx = task_ids.index(task_id)
        if direction == 'up' and idx > 0:
            task_ids[idx], task_ids[idx-1] = task_ids[idx-1], task_ids[idx]
        elif direction == 'down' and idx < len(task_ids) - 1:
            task_ids[idx], task_ids[idx+1] = task_ids[idx+1], task_ids[idx]
        
        db.reorder_playlist_tasks(playlist_id, task_ids)
    
    return redirect(url_for('playlist', selected=playlist_id))


@app.route('/playlist/<int:playlist_id>/optimize', methods=['POST'])
def optimize_playlist(playlist_id):
    """AIでプレイリストを最適化"""
    mode = request.form.get('mode', 'balanced')
    time_limit = request.form.get('time_limit', type=int)
    
    tasks = db.get_playlist_tasks(playlist_id)
    if not tasks:
        return redirect(url_for('playlist', selected=playlist_id))
    
    lifestyle = db.get_lifestyle_settings()
    
    if mode == 'balanced':
        optimizer = ScheduleOptimizer()
        optimized = optimizer.generate_balanced_schedule(tasks)
    elif mode == 'time_limited' and time_limit:
        optimizer = ScheduleOptimizer()
        optimized = optimizer.optimize_schedule(tasks, time_limit)
    elif mode == 'genetic':
        genetic = GeneticScheduleOptimizer(lifestyle)
        optimized = genetic.optimize(tasks)
    else:
        optimized = tasks
    
    task_ids = [t.id for t in optimized]
    db.reorder_playlist_tasks(playlist_id, task_ids)
    
    return redirect(url_for('playlist', selected=playlist_id))


@app.route('/lifestyle/save', methods=['POST'])
def save_lifestyle():
    """生活設定を保存"""
    settings = LifestyleSettings(
        wake_time=request.form.get('wake_time', '07:00'),
        sleep_time=request.form.get('sleep_time', '23:00'),
        min_sleep_hours=request.form.get('min_sleep_hours', 7, type=int),
        bath_time=request.form.get('bath_time', '21:00'),
        bath_duration=request.form.get('bath_duration', 30, type=int),
        breakfast_time=request.form.get('breakfast_time', '07:30'),
        lunch_time=request.form.get('lunch_time', '12:00'),
        dinner_time=request.form.get('dinner_time', '19:00'),
        meal_duration=request.form.get('meal_duration', 30, type=int)
    )
    db.save_lifestyle_settings(settings)
    
    selected_id = request.form.get('selected_playlist', type=int)
    return redirect(url_for('playlist', selected=selected_id))


@app.route('/task/create', methods=['POST'])
def create_task():
    """タスク作成"""
    title = request.form.get('title', '').strip()
    if not title:
        return redirect(url_for('playlist'))
    
    difficulty = request.form.get('difficulty', 2, type=int)
    duration = request.form.get('duration', 25, type=int)
    break_duration = request.form.get('break_duration', 5, type=int)
    selected_id = request.form.get('selected_playlist')
    
    user_id = session.get('user_id')
    if user_id:
        # ログインユーザー: Supabaseに保存
        from moon_tasker.cloud.supabase_client import get_cloud_db
        cloud_db = get_cloud_db()
        task_id = cloud_db.save_user_task(user_id, {
            'title': title,
            'duration': duration,
            'break_duration': break_duration,
            'difficulty': difficulty,
            'priority': 0,
            'status': 'pending'
        })
        
        # プレイリストが選択されていれば自動的に追加
        if selected_id and task_id:
            cloud_db.add_task_to_playlist(selected_id, task_id, 0)
    else:
        # ゲスト: ローカルDBに保存
        task = Task(
            title=title,
            category="",
            difficulty=difficulty,
            duration=duration,
            break_duration=break_duration,
            priority=0,
            status="pending"
        )
        new_task_id = db.create_task(task)
        
        # プレイリストが選択されていれば自動的に追加
        if selected_id:
            db.add_task_to_playlist(int(selected_id), new_task_id)
    
    return redirect(url_for('playlist', selected=selected_id))


@app.route('/task/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """タスク削除"""
    db.delete_task(task_id)
    return redirect(url_for('playlist'))


@app.route('/moon-cycle')
def moon_cycle():
    """月のサイクル画面"""
    active_cycle = db.get_active_moon_cycle()
    all_cycles = db.get_all_moon_cycles()
    completed_cycles = [c for c in all_cycles if c.status == "completed"][:5]
    
    moon_emoji = moon_calc.get_moon_emoji()
    moon_phase = moon_calc.get_moon_phase_name()
    
    cycle_tasks = []
    progress = 0
    completed_count = 0
    total_count = 0
    
    if active_cycle:
        cycle_tasks = db.get_cycle_tasks(active_cycle.id)
        completed_count = sum(1 for t in cycle_tasks if getattr(t, '_cycle_completed', False))
        total_count = len(cycle_tasks)
        if total_count > 0:
            progress = (completed_count / total_count) * 100
    
    # 利用可能なタスク（サイクルに追加可能）
    all_tasks = db.get_all_tasks()
    available_tasks = [t for t in all_tasks if t.status == "pending"]
    
    return render_template('pages/moon_cycle.html',
                         active_cycle=active_cycle,
                         cycle_tasks=cycle_tasks,
                         completed_cycles=completed_cycles,
                         moon_emoji=moon_emoji,
                         moon_phase=moon_phase,
                         progress=progress,
                         completed_count=completed_count,
                         total_count=total_count,
                         available_tasks=available_tasks)


@app.route('/moon-cycle/create', methods=['POST'])
def create_moon_cycle():
    """新規サイクル作成"""
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    goal = request.form.get('goal', '')
    
    cycle = MoonCycle(
        cycle_start=start_date,
        cycle_end=end_date,
        goal=goal,
        review="",
        target_task_count=0,
        completed_task_count=0,
        status="active"
    )
    db.create_moon_cycle(cycle)
    return redirect(url_for('moon_cycle'))


@app.route('/moon-cycle/<int:cycle_id>/add-task', methods=['POST'])
def add_task_to_cycle(cycle_id):
    """サイクルにタスクを追加"""
    task_ids = request.form.getlist('task_ids')
    for task_id in task_ids:
        db.add_task_to_cycle(cycle_id, int(task_id))
    return redirect(url_for('moon_cycle'))


@app.route('/moon-cycle/<int:cycle_id>/complete', methods=['POST'])
def complete_moon_cycle(cycle_id):
    """サイクル完了"""
    self_rating = request.form.get('self_rating', 0, type=int)
    good_points = request.form.get('good_points', '')
    improvement_points = request.form.get('improvement_points', '')
    next_actions = request.form.get('next_actions', '')
    
    db.complete_moon_cycle(cycle_id, self_rating, good_points, improvement_points, next_actions)
    return redirect(url_for('moon_cycle'))


@app.route('/moon-cycle/<int:cycle_id>/delete', methods=['POST'])
def delete_moon_cycle(cycle_id):
    """サイクル削除"""
    db.delete_moon_cycle(cycle_id)
    return redirect(url_for('moon_cycle'))


@app.route('/collection')
def collection():
    """星座図鑑画面"""
    user_id = session.get('user_id')
    
    try:
        # 全バッジ定義を取得
        badges = db.get_all_badges()
        
        if user_id:
            # ログインユーザー: Supabaseからバッジ獲得状況を取得
            from moon_tasker.cloud.supabase_client import get_cloud_db
            cloud_db = get_cloud_db()
            cloud_badges = cloud_db.get_user_badges(user_id)
            unlocked_names = {b.get('badge_name') for b in cloud_badges}
            
            # クラウドの獲得状況でローカルを上書き
            unlocked = []
            locked = []
            for b in badges:
                if b.name in unlocked_names:
                    b.unlocked_at = True  # 仮設定
                    unlocked.append(b)
                else:
                    locked.append(b)
        else:
            # ゲスト: ローカルDBの状態を使用
            unlocked = [b for b in badges if b.unlocked_at]
            locked = [b for b in badges if not b.unlocked_at]
        
        # カテゴリ分け
        categories = {}
        for badge in badges:
            cat = getattr(badge, 'category', 'その他') or 'その他'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(badge)
    except Exception as e:
        print(f"Badge error: {e}")
        unlocked = []
        locked = []
        categories = {}
    # 新しく獲得したバッジをセッションから取得（表示後にクリア）
    new_badges = session.pop('new_badges', [])
    
    return render_template('pages/collection.html',
                         unlocked_badges=unlocked,
                         locked_badges=locked,
                         categories=categories,
                         new_badges=new_badges)


@app.route('/creature')
def creature():
    """生命体画面"""
    current_creature = creature_system.get_creature()
    ctx = get_creature_context(current_creature)
    
    evolution_history = []
    if current_creature and current_creature.status in ["active", "completed"]:
        stage_info = {
            1: ("stage1_content.png", "たまご"),
            2: ("stage2_content.png", "ほしのあかちゃん"),
            3: ("stage3_content.png", "ほし"),
            4: ("stage4_content.png", "こうさぎ"),
            5: ("stage5_content.png", "つき"),
        }
        for stage in range(1, current_creature.evolution_stage + 1):
            img, name = stage_info.get(stage, ("stage1_content.png", "不明"))
            evolution_history.append({
                'stage': stage, 
                'image': f'/static/images/creature/{img}', 
                'name': name
            })
    
    # クールダウン状態チェック
    cooldown_remaining = None
    if current_creature and current_creature.cooldown_until:
        try:
            if isinstance(current_creature.cooldown_until, str):
                cooldown_date = datetime.fromisoformat(current_creature.cooldown_until)
            else:
                cooldown_date = current_creature.cooldown_until
            
            if cooldown_date > datetime.now():
                cooldown_remaining = (cooldown_date - datetime.now()).days
        except:
            pass
    
    return render_template('pages/creature.html',
                         creature=ctx['creature'],
                         emotion=ctx['emotion'],
                         warning=ctx['warning'],
                         creature_image=ctx['creature_image'],
                         evolution_history=evolution_history,
                         cooldown_remaining=cooldown_remaining,
                         raw_creature=current_creature)


@app.route('/creature/start', methods=['POST'])
def start_creature():
    """生命体育成開始（誓約確認後）"""
    name = request.form.get('name', 'ルナ').strip()
    
    # NGワードチェック（簡易版）
    ng_words = ['バカ', 'アホ', '死', '殺']
    for ng in ng_words:
        if ng in name:
            return redirect(url_for('creature'))
    
    creature_system.start_new_creature(name)
    return redirect(url_for('creature'))


@app.route('/friends')
def friends():
    """フレンド画面"""
    from moon_tasker.cloud.supabase_client import get_auth, get_cloud_db
    
    auth = get_auth()
    is_logged_in = session.get('user_id') is not None
    user_profile = None
    friends_list = []
    pending_requests = []
    my_friend_code = None
    my_creature_cloud = None
    
    # ローカルの生命体を取得
    local_creature = creature_system.get_creature()
    has_local_creature = local_creature and local_creature.status in ['active', 'completed']
    
    # 獲得済みバッジ（称号選択用）
    unlocked_badges = []
    try:
        from moon_tasker.logic.titles import get_title_for_constellation
        all_badges = db.get_all_badges()
        for b in all_badges:
            if b.unlocked_at:
                # 称号を追加（辞書に変換）
                badge_dict = {
                    'id': b.id,
                    'name': b.name,
                    'constellation_name': b.constellation_name,
                    'title': get_title_for_constellation(b.constellation_name)
                }
                unlocked_badges.append(badge_dict)
    except Exception as e:
        print(f"Badge title error: {e}")
    
    if is_logged_in:
        try:
            cloud_db = get_cloud_db()
            user_id = session.get('user_id')
            
            # プロフィール取得
            user_profile = cloud_db.get_profile(user_id)
            
            # セッションにプロフィールデータを同期
            if user_profile:
                session['user_nickname'] = user_profile.get('nickname', '')
                session['user_title'] = user_profile.get('constellation_badge', '')
            
            # フレンドコード（ユーザーID短縮版）
            my_friend_code = user_id[:8].upper() if user_id else None
            
            # フレンド一覧取得
            friends_list = cloud_db.get_friends(user_id) or []
            
            # クラウドの生命体取得
            my_creature_cloud = cloud_db.get_creature(user_id)
        except Exception as e:
            print(f"Friend data error: {e}")
    
    return render_template('pages/friends.html',
                         is_logged_in=is_logged_in,
                         user_profile=user_profile,
                         friends_list=friends_list,
                         pending_requests=pending_requests,
                         my_friend_code=my_friend_code,
                         my_creature_cloud=my_creature_cloud,
                         local_creature=local_creature,
                         has_local_creature=has_local_creature,
                         unlocked_badges=unlocked_badges,
                         user_email=session.get('user_email'),
                         user_nickname=session.get('user_nickname'))


@app.route('/friends/login', methods=['POST'])
def friends_login():
    """ログイン処理"""
    from moon_tasker.cloud.supabase_client import get_auth
    
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    
    if not email or not password:
        return render_template('partials/login_error.html', error='メールとパスワードを入力してください')
    
    try:
        auth = get_auth()
        result = auth.sign_in_with_email(email, password)
        
        if result.get('error'):
            return render_template('partials/login_error.html', error=result['error'])
        
        # セッションにユーザー情報を保存
        session['user_id'] = auth.user_id
        session['user_email'] = email
        session['access_token'] = auth._access_token
        
        # プロフィールからニックネームを取得
        try:
            from moon_tasker.cloud.supabase_client import get_cloud_db
            cloud_db = get_cloud_db()
            profile = cloud_db.get_profile(auth.user_id)
            if profile:
                session['user_nickname'] = profile.get('nickname', '') or email.split('@')[0]
                session['user_title'] = profile.get('constellation_badge', '')
            else:
                session['user_nickname'] = email.split('@')[0]
        except:
            session['user_nickname'] = email.split('@')[0]
        
    except Exception as e:
        return render_template('partials/login_error.html', error=f'ログインエラー: {str(e)}')
    
    return redirect(url_for('friends'))


@app.route('/friends/signup', methods=['POST'])
def friends_signup():
    """新規登録処理"""
    from moon_tasker.cloud.supabase_client import get_auth, get_cloud_db
    
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    nickname = request.form.get('nickname', '').strip() or email.split('@')[0]
    
    if not email or not password:
        return render_template('partials/login_error.html', error='メールとパスワードを入力してください')
    
    if len(password) < 6:
        return render_template('partials/login_error.html', error='パスワードは6文字以上にしてください')
    
    try:
        auth = get_auth()
        result = auth.sign_up_with_email(email, password)
        
        if result.get('error'):
            return render_template('partials/login_error.html', error=result['error'])
        
        # プロフィール作成
        if auth.user_id:
            cloud_db = get_cloud_db()
            cloud_db.upsert_profile(auth.user_id, nickname)
            
            session['user_id'] = auth.user_id
            session['user_email'] = email
            session['user_nickname'] = nickname
            session['access_token'] = auth._access_token
        
    except Exception as e:
        return render_template('partials/login_error.html', error=f'登録エラー: {str(e)}')
    
    return redirect(url_for('friends'))


@app.route('/friends/logout', methods=['POST'])
def friends_logout():
    """ログアウト処理"""
    session.clear()
    return redirect(url_for('friends'))


@app.route('/friends/add', methods=['POST'])
def add_friend():
    """フレンド追加（コードで検索）"""
    from moon_tasker.cloud.supabase_client import get_cloud_db
    
    friend_code = request.form.get('friend_code', '').strip().lower()
    user_id = session.get('user_id')
    
    if not user_id:
        return redirect(url_for('friends'))
    
    if not friend_code:
        return redirect(url_for('friends'))
    
    try:
        cloud_db = get_cloud_db()
        # フレンドコードで検索（簡易版：IDの先頭8文字）
        result = cloud_db.send_friend_request(user_id, friend_code)
    except Exception as e:
        print(f"Add friend error: {e}")
    
    return redirect(url_for('friends'))


@app.route('/friends/sync-creature', methods=['POST'])
def sync_creature():
    """生命体をクラウドに同期"""
    from moon_tasker.cloud.supabase_client import get_cloud_db
    
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('friends'))
    
    creature = creature_system.get_creature()
    if not creature or creature.status not in ['active', 'completed']:
        # 生命体がいない場合は育成画面へ
        return redirect(url_for('creature'))
    
    try:
        cloud_db = get_cloud_db()
        creature_data = {
            'name': creature.name,
            'mood': creature.mood,
            'energy': creature.energy,
            'evolution_stage': creature.evolution_stage,
            'status': creature.status
        }
        cloud_db.save_creature(user_id, creature_data)
    except Exception as e:
        print(f"Sync creature error: {e}")
    
    return redirect(url_for('friends'))


@app.route('/friends/update-title', methods=['POST'])
def update_title():
    """称号を更新"""
    from moon_tasker.cloud.supabase_client import get_cloud_db
    
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('friends'))
    
    title = request.form.get('title', '')
    
    try:
        cloud_db = get_cloud_db()
        # 現在のニックネームを取得（セッション優先、なければプロフィールから）
        nickname = session.get('user_nickname')
        if not nickname:
            current_profile = cloud_db.get_profile(user_id)
            nickname = current_profile.get('nickname', '') if current_profile else ''
        if not nickname:
            nickname = session.get('user_email', '').split('@')[0]
        
        print(f"[UPDATE_TITLE] user_id={user_id}, nickname={nickname}, title={title}")
        
        # プロフィールの称号を更新
        result = cloud_db.upsert_profile(user_id, nickname, title)
        print(f"[UPDATE_TITLE] upsert result: {result}")
        
        # セッションにも保存
        session['user_title'] = title
        session['user_nickname'] = nickname
        
        # 更新後にプロフィールを再取得してセッションを同期
        updated_profile = cloud_db.get_profile(user_id)
        if updated_profile:
            session['user_nickname'] = updated_profile.get('nickname', nickname)
            session['user_title'] = updated_profile.get('constellation_badge', title)
        
    except Exception as e:
        print(f"Update title error: {e}")
    
    return redirect(url_for('friends'))


@app.route('/friends/update-nickname', methods=['POST'])
def update_nickname():
    """ニックネームを更新"""
    from moon_tasker.cloud.supabase_client import get_cloud_db
    
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('friends'))
    
    nickname = request.form.get('nickname', '').strip()
    if not nickname:
        return redirect(url_for('friends'))
    
    try:
        cloud_db = get_cloud_db()
        # 現在の称号を保持しつつニックネームを更新
        current_profile = cloud_db.get_profile(user_id)
        current_title = current_profile.get('constellation_badge', '') if current_profile else ''
        cloud_db.upsert_profile(user_id, nickname, current_title)
        session['user_nickname'] = nickname
    except Exception as e:
        print(f"Update nickname error: {e}")
    
    return redirect(url_for('friends'))


@app.route('/friends/<friend_id>/creature')
def view_friend_creature(friend_id):
    """フレンドの生命体を閲覧"""
    from moon_tasker.cloud.supabase_client import get_cloud_db
    
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('friends'))
    
    try:
        cloud_db = get_cloud_db()
        friend_creature = cloud_db.get_friend_creature(friend_id)
        friend_profile = cloud_db.get_profile(friend_id)
        
        # 生命体画像を決定
        creature_image = None
        if friend_creature:
            stage = friend_creature.get('evolution_stage', 1)
            mood = friend_creature.get('mood', 50)
            if mood >= 70:
                emotion = 'happy'
            elif mood >= 40:
                emotion = 'content'
            else:
                emotion = 'sad'
            creature_image = f'/static/images/creature/stage{stage}_{emotion}.png'
        
        return render_template('pages/friend_creature.html',
                             friend_creature=friend_creature,
                             friend_profile=friend_profile,
                             creature_image=creature_image)
    except Exception as e:
        print(f"View friend creature error: {e}")
        return redirect(url_for('friends'))


# ============ DATA SYNC ============

@app.route('/sync/upload', methods=['POST'])
def sync_upload():
    """ローカルデータをSupabaseにアップロード"""
    from moon_tasker.cloud.supabase_client import get_cloud_db
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        cloud_db = get_cloud_db()
        
        # ローカルタスクをアップロード
        local_tasks = db.get_all_tasks()
        for task in local_tasks:
            cloud_db.save_user_task(user_id, {
                'title': task.title,
                'duration': task.duration,
                'break_duration': task.break_duration,
                'difficulty': task.difficulty,
                'priority': task.priority,
                'status': task.status
            })
        
        # ローカルプレイリストをアップロード
        local_playlists = db.get_all_playlists()
        for pl in local_playlists:
            cloud_db.save_user_playlist(user_id, {
                'name': pl.name,
                'description': pl.description
            })
        
        # ローカルバッジをアップロード
        local_badges = db.get_all_badges()
        unlocked_badges = [b for b in local_badges if b.unlocked_at]
        badge_count = 0
        for badge in unlocked_badges:
            if cloud_db.save_user_badge(user_id, badge.name):
                badge_count += 1
        
        return jsonify({'success': True, 'tasks': len(local_tasks), 'playlists': len(local_playlists), 'badges': badge_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/sync/download', methods=['POST'])
def sync_download():
    """Supabaseからローカルにダウンロード"""
    from moon_tasker.cloud.supabase_client import get_cloud_db
    
    user_id = session.get('user_id')
    print(f"[SYNC_DOWNLOAD] user_id: {user_id}")
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    try:
        cloud_db = get_cloud_db()
        
        # クラウドタスクをダウンロード
        cloud_tasks = cloud_db.get_user_tasks(user_id)
        print(f"[SYNC_DOWNLOAD] cloud_tasks count: {len(cloud_tasks)}")
        for t in cloud_tasks:
            task = Task(
                title=t.get('title', ''),
                duration=t.get('duration', 25),
                break_duration=t.get('break_duration', 5),
                difficulty=t.get('difficulty', 3),
                priority=t.get('priority', 0),
                status=t.get('status', 'pending')
            )
            db.create_task(task)
        
        # クラウドプレイリストをダウンロード
        cloud_playlists = cloud_db.get_user_playlists(user_id)
        print(f"[SYNC_DOWNLOAD] cloud_playlists count: {len(cloud_playlists)}")
        for p in cloud_playlists:
            pl = Playlist(
                name=p.get('name', ''),
                description=p.get('description', '')
            )
            db.create_playlist(pl)
        
        # クラウドバッジをダウンロード
        cloud_badges = cloud_db.get_user_badges(user_id)
        print(f"[SYNC_DOWNLOAD] cloud_badges count: {len(cloud_badges)}")
        for b in cloud_badges:
            badge_name = b.get('badge_name', '')
            if badge_name:
                db.unlock_badge_by_name(badge_name)
        
        return jsonify({'success': True, 'tasks': len(cloud_tasks), 'playlists': len(cloud_playlists), 'badges': len(cloud_badges)})
    except Exception as e:
        print(f"[SYNC_DOWNLOAD] Error: {e}")
        return jsonify({'error': str(e)}), 500


# ============ LOCAL STORAGE API ============

@app.route('/api/restore-local', methods=['POST'])
def restore_from_local():
    """localStorageからデータを復元"""
    try:
        data = request.get_json() or {}
        tasks = data.get('tasks', [])
        playlists = data.get('playlists', [])
        
        restored_tasks = 0
        restored_playlists = 0
        
        # 既存データがなければ復元
        existing_tasks = db.get_all_tasks()
        existing_playlists = db.get_all_playlists()
        
        if len(existing_tasks) == 0:
            for t in tasks:
                task = Task(
                    title=t.get('title', ''),
                    duration=t.get('duration', 25),
                    break_duration=t.get('break_duration', 5),
                    difficulty=t.get('difficulty', 3),
                    priority=t.get('priority', 0),
                    status=t.get('status', 'pending')
                )
                db.create_task(task)
                restored_tasks += 1
        
        if len(existing_playlists) == 0:
            for p in playlists:
                pl = Playlist(
                    name=p.get('name', ''),
                    description=p.get('description', '')
                )
                db.create_playlist(pl)
                restored_playlists += 1
        
        return jsonify({'success': True, 'tasks': restored_tasks, 'playlists': restored_playlists})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get-all-data')
def get_all_data():
    """全データを取得（localStorageに保存用）"""
    try:
        tasks = db.get_all_tasks()
        playlists = db.get_all_playlists()
        
        tasks_data = [{
            'id': t.id,
            'title': t.title,
            'duration': t.duration,
            'break_duration': t.break_duration,
            'difficulty': t.difficulty,
            'priority': t.priority,
            'status': t.status
        } for t in tasks]
        
        playlists_data = [{
            'id': p.id,
            'name': p.name,
            'description': p.description
        } for p in playlists]
        
        return jsonify({'tasks': tasks_data, 'playlists': playlists_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.errorhandler(404)
def not_found(e):
    return render_template('pages/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('pages/500.html'), 500


# ============ MAIN ============

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
