import asyncio
import flet as ft
import platform
import subprocess

# --- 音声読み上げ関数 ---
def speak_sync(text):
    system = platform.system()
    try:
        if system == "Windows":
            cmd = [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                f"Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}');"
            ]
            subprocess.run(cmd, creationflags=0x08000000)
        elif system == "Darwin":
            subprocess.run(["say", text])
    except:
        pass

async def speak(text):
    await asyncio.to_thread(speak_sync, text)

# --- アプリ本体 ---
async def main(page: ft.Page):
    page.title = "Owl Optimus - Final"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 800
    page.vertical_alignment = ft.MainAxisAlignment.START
    
    state = {"is_running": False}
    my_tasks = []

    # === 部品定義 ===
    name_input = ft.TextField(label="タスク名", expand=True)
    time_input = ft.TextField(label="分", width=80, value="30", text_align=ft.TextAlign.RIGHT)
    tasks_view = ft.ListView(expand=True, spacing=10, padding=20)

    timer_display = ft.Text(value="00:00", size=80, color=ft.Colors.BLUE_200, visible=False)
    current_task_display = ft.Text(value="", size=30, weight="bold", visible=False)
    progress_bar = ft.ProgressBar(width=300, value=0, visible=False)
    
    menu_button = ft.IconButton(
        icon=ft.Icons.MORE_VERT,
        icon_size=30,
        visible=False,
        tooltip="メニュー"
    )

    # === 動きを作る関数 ===

    def add_task_click(e):
        if not name_input.value: return
        try:
            mins = float(time_input.value)
        except ValueError: return

        task_data = {"name": name_input.value, "minutes": mins}
        my_tasks.append(task_data)
        refresh_list()
        name_input.value = ""
        name_input.focus()
        page.update()

    def refresh_list():
        tasks_view.controls.clear()
        for task in my_tasks:
            row = ft.ListTile(
                title=ft.Text(task["name"]),
                subtitle=ft.Text(f"{task['minutes']} 分"),
                leading=ft.Icon(ft.Icons.TASK_ALT),
                trailing=ft.IconButton(
                    icon=ft.Icons.DELETE, icon_color="red",
                    data=task, on_click=delete_clicked
                )
            )
            tasks_view.controls.append(row)
        page.update()

    def delete_clicked(e):
        if e.control.data in my_tasks:
            my_tasks.remove(e.control.data)
        refresh_list()

    def close_dialog(e):
        page.close(abort_dialog)

    def confirm_abort(e):
        state["is_running"] = False
        page.close(abort_dialog)
        reset_view()

    abort_dialog = ft.AlertDialog(
        title=ft.Text("確認"),
        content=ft.Text("集中モードを中断して設定に戻りますか？\n今のタスクはリセットされます。"),
        actions=[
            ft.TextButton("いいえ（続ける）", on_click=close_dialog),
            ft.TextButton("はい（中断）", on_click=confirm_abort, style=ft.ButtonStyle(color=ft.Colors.RED)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def open_menu(e):
        page.open(abort_dialog)

    menu_button.on_click = open_menu

    # ★ プレイリスト実行 ★
    async def run_playlist(e):
        if not my_tasks:
            await speak("タスクがありません")
            return

        state["is_running"] = True

        # ★ 修正箇所：画面を切り替える前に、表示をリセットする ★
        timer_display.value = "00:00"
        current_task_display.value = "準備中..."
        progress_bar.value = 0

        # ここから画面切り替え
        input_container.visible = False
        tasks_view.visible = False
        run_btn.visible = False
        
        timer_display.visible = True
        current_task_display.visible = True
        progress_bar.visible = True
        menu_button.visible = True
        
        top_row.controls = [menu_button]
        top_row.alignment = ft.MainAxisAlignment.END
        
        page.update() # この時点で「00:00」が表示される

        for task in my_tasks:
            if not state["is_running"]: break

            name = task["name"]
            mins = task["minutes"]
            sec = int(mins * 60)

            current_task_display.value = name
            page.update()
            await speak(f"{name}、{mins}分、スタート")

            for i in range(sec, -1, -1):
                if not state["is_running"]: break

                m, s = divmod(i, 60)
                timer_display.value = "{:02d}:{:02d}".format(m, s)
                if sec > 0:
                    progress_bar.value = (sec - i) / sec
                else:
                    progress_bar.value = 1.0 # 0秒タスク対策
                page.update()
                await asyncio.sleep(1)

            if state["is_running"]:
                await speak(f"{name}、終了")
                await asyncio.sleep(1)

        if state["is_running"]:
            current_task_display.value = "全タスク完了"
            timer_display.value = "FINISH"
            menu_button.visible = False
            page.update()
            await speak("全てのタスクが終わりました")
            await asyncio.sleep(3)
            reset_view()

    def reset_view(e=None):
        input_container.visible = True
        tasks_view.visible = True
        run_btn.visible = True
        
        timer_display.visible = False
        current_task_display.visible = False
        progress_bar.visible = False
        menu_button.visible = False
        
        top_row.controls = []
        
        page.update()

    # === レイアウト組み立て ===
    add_btn = ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_size=40, on_click=add_task_click)
    input_container = ft.Row([name_input, time_input, add_btn])
    run_btn = ft.ElevatedButton("プレイリスト開始", icon=ft.Icons.PLAY_ARROW, on_click=run_playlist, height=50)

    top_row = ft.Row([], alignment=ft.MainAxisAlignment.END)

    page.add(
        ft.Column(
            [
                top_row,
                ft.Text("Owl Optimus Scheduler", size=20, weight="bold", text_align=ft.TextAlign.CENTER),
                ft.Divider(height=10, color=ft.Colors.TRANSPARENT),
                input_container,
                ft.Divider(),
                tasks_view,
                ft.Divider(),
                run_btn,
                
                ft.Divider(height=30, color=ft.Colors.TRANSPARENT),
                current_task_display,
                timer_display,
                progress_bar,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

ft.app(target=main)