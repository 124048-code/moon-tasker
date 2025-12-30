"""
Moon Tasker - Flask Application
HTMX + Static CSS based web application
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from datetime import datetime, timedelta
import os
import sys

# Add moon_tasker to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from moon_tasker.database import Database
from moon_tasker.models import Task, Playlist, MoonCycle
from moon_tasker.logic.creature_logic import CreatureSystem
from moon_tasker.logic.moon_cycle import MoonCycleCalculator
from moon_tasker.logic.badge_logic import BadgeSystem

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', 'moon-tasker-secret-key-2024')

# Database instance
db = Database()
creature_system = CreatureSystem(db)
moon_calc = MoonCycleCalculator()
badge_system = BadgeSystem(db)

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
    
    emotion = None
    warning = None
    emoji = "🥚"
    if creature and creature.status in ["active", "completed"]:
        creature_system.check_neglect()
        emotion = creature_system.get_emotion_state(creature)
        warning = creature_system.get_warning_message(creature)
        emoji = creature_system.get_creature_emoji(creature)
    
    return render_template('pages/home.html',
                         creature=creature,
                         emotion=emotion,
                         warning=warning,
                         emoji=emoji,
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
    
    schedule = []
    time_cursor = datetime.now()
    
    for task in tasks:
        task_end = time_cursor + timedelta(minutes=task.duration + task.break_duration)
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
    
    return jsonify({'success': True})


@app.route('/playlist')
def playlist():
    """プレイリスト管理画面"""
    playlists = db.get_all_playlists()
    tasks = db.get_all_tasks()
    pending_tasks = [t for t in tasks if t.status == "pending"]
    
    selected_id = request.args.get('selected', type=int)
    selected_tasks = []
    if selected_id:
        selected_tasks = db.get_playlist_tasks(selected_id)
    
    return render_template('pages/playlist.html',
                         playlists=playlists,
                         pending_tasks=pending_tasks,
                         selected_id=selected_id,
                         selected_tasks=selected_tasks)


@app.route('/playlist/create', methods=['POST'])
def create_playlist():
    """プレイリスト作成"""
    name = request.form.get('name', '').strip()
    if name:
        pl = Playlist(name=name, description="")
        db.create_playlist(pl)
    return redirect(url_for('playlist'))


@app.route('/playlist/<int:playlist_id>/delete', methods=['POST'])
def delete_playlist(playlist_id):
    """プレイリスト削除"""
    db.delete_playlist(playlist_id)
    return redirect(url_for('playlist'))


@app.route('/playlist/<int:playlist_id>/add/<int:task_id>', methods=['POST'])
def add_to_playlist(playlist_id, task_id):
    """タスクをプレイリストに追加"""
    db.add_task_to_playlist(playlist_id, task_id)
    return redirect(url_for('playlist', selected=playlist_id))


@app.route('/playlist/<int:playlist_id>/remove/<int:task_id>', methods=['POST'])
def remove_from_playlist(playlist_id, task_id):
    """タスクをプレイリストから削除"""
    db.remove_task_from_playlist(playlist_id, task_id)
    return redirect(url_for('playlist', selected=playlist_id))


@app.route('/task/create', methods=['POST'])
def create_task():
    """タスク作成"""
    title = request.form.get('title', '').strip()
    if not title:
        return redirect(url_for('playlist'))
    
    difficulty = request.form.get('difficulty', 2, type=int)
    duration = request.form.get('duration', 25, type=int)
    break_duration = request.form.get('break_duration', 5, type=int)
    
    task = Task(
        title=title,
        category="",
        difficulty=difficulty,
        duration=duration,
        break_duration=break_duration,
        priority=0,
        status="pending"
    )
    db.create_task(task)
    
    selected_id = request.form.get('selected_playlist', type=int)
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
    
    return render_template('pages/moon_cycle.html',
                         active_cycle=active_cycle,
                         cycle_tasks=cycle_tasks,
                         completed_cycles=completed_cycles,
                         moon_emoji=moon_emoji,
                         moon_phase=moon_phase,
                         progress=progress,
                         completed_count=completed_count,
                         total_count=total_count)


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


@app.route('/collection')
def collection():
    """星座図鑑画面"""
    try:
        badges = db.get_all_badges()
        unlocked = [b for b in badges if b.unlocked_at]
        locked = [b for b in badges if not b.unlocked_at]
    except Exception as e:
        print(f"Badge error: {e}")
        unlocked = []
        locked = []
    
    return render_template('pages/collection.html',
                         unlocked_badges=unlocked,
                         locked_badges=locked)


@app.route('/creature')
def creature():
    """生命体画面"""
    current_creature = creature_system.get_creature()
    
    if current_creature:
        creature_system.check_neglect()
        emotion = creature_system.get_emotion_state(current_creature)
        warning = creature_system.get_warning_message(current_creature)
        emoji = creature_system.get_creature_emoji(current_creature)
    else:
        emotion = None
        warning = None
        emoji = "🥚"
    
    evolution_history = []
    if current_creature:
        stage_info = {
            1: ("🥚", "たまご"),
            2: ("⭐", "ほしのあかちゃん"),
            3: ("🌟", "ほし"),
            4: ("🐰", "こうさぎ"),
            5: ("🌙", "つき"),
        }
        for stage in range(1, current_creature.evolution_stage + 1):
            emoji_s, name = stage_info.get(stage, ("?", "不明"))
            evolution_history.append({'stage': stage, 'emoji': emoji_s, 'name': name})
    
    return render_template('pages/creature.html',
                         creature=current_creature,
                         emotion=emotion,
                         warning=warning,
                         emoji=emoji,
                         evolution_history=evolution_history)


@app.route('/creature/start', methods=['POST'])
def start_creature():
    """生命体育成開始"""
    name = request.form.get('name', 'ルナ').strip()
    creature_system.start_new_creature(name)
    return redirect(url_for('creature'))


@app.route('/friends')
def friends():
    """フレンド画面"""
    is_logged_in = False
    user_profile = None
    friends_list = []
    
    try:
        from moon_tasker.cloud.supabase_client import SupabaseAuth
        auth = SupabaseAuth()
        is_logged_in = auth.current_user is not None
        
        if is_logged_in:
            user_profile = auth.get_profile()
            friends_list = auth.get_friends()
    except Exception:
        pass
    
    return render_template('pages/friends.html',
                         is_logged_in=is_logged_in,
                         user_profile=user_profile,
                         friends_list=friends_list)


@app.route('/friends/login', methods=['POST'])
def friends_login():
    """ログイン処理"""
    try:
        from moon_tasker.cloud.supabase_client import SupabaseAuth
        auth = SupabaseAuth()
        email = request.form.get('email')
        password = request.form.get('password')
        result = auth.sign_in_with_email(email, password)
        if result.get('error'):
            return render_template('partials/login_error.html', error=result['error'])
    except Exception:
        pass
    return redirect(url_for('friends'))


@app.route('/friends/signup', methods=['POST'])
def friends_signup():
    """新規登録処理"""
    try:
        from moon_tasker.cloud.supabase_client import SupabaseAuth
        auth = SupabaseAuth()
        email = request.form.get('email')
        password = request.form.get('password')
        result = auth.sign_up_with_email(email, password)
        if result.get('error'):
            return render_template('partials/login_error.html', error=result['error'])
    except Exception:
        pass
    return redirect(url_for('friends'))


@app.route('/friends/logout', methods=['POST'])
def friends_logout():
    """ログアウト処理"""
    try:
        from moon_tasker.cloud.supabase_client import SupabaseAuth
        auth = SupabaseAuth()
        auth.sign_out()
    except Exception:
        pass
    return redirect(url_for('friends'))


# ============ ERROR HANDLERS ============

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
