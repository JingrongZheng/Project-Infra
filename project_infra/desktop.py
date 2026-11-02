"""Portable desktop launcher; project services stay in this process."""
from pathlib import Path
import json
import os
import sys
import threading
import webbrowser
from contextlib import contextmanager

from .bootstrap import initialize
from .service import Service
from .store import Store
from .web import make_server


@contextmanager
def application_mutex():
    """Let Setup/Uninstall detect a running app without forcibly stopping it."""
    handle = None
    if sys.platform == 'win32':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateMutexW(None, False, 'Local\\ProjectInfra.Desktop')
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        if handle:
            kernel.CloseHandle(handle)


def application_directory():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / '.work' / 'desktop'


def load_recent(directory):
    try:
        entries = json.loads((directory / 'settings.json').read_text(encoding='utf-8'))['projects']
        result = []
        for entry in entries:
            candidates = [directory / entry['relative']] if entry.get('relative') else []
            candidates += [Path(entry['absolute'])] if entry.get('absolute') else []
            for candidate in candidates:
                if (candidate / '.project/config.toml').is_file():
                    candidate = candidate.resolve()
                    if candidate not in result:
                        result.append(candidate)
                    break
        return result[:10]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []


def save_recent(directory, projects):
    entries = []
    for project in projects[:10]:
        try:
            relative = os.path.relpath(project, directory)
        except ValueError:  # Different Windows drives.
            relative = None
        entries.append({'relative': relative, 'absolute': str(project)})
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / 'settings.tmp'
    temporary.write_text(json.dumps({'projects': entries}, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(directory / 'settings.json')


class ProjectSessions:
    def __init__(self):
        self.sessions = {}

    def open(self, project):
        project = Path(project).resolve()
        if not (project / '.project/config.toml').is_file():
            raise ValueError('尚未初始化项目')
        if project in self.sessions:
            return self.sessions[project][2]
        server = make_server(Service(Store(project)), 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}/'
        self.sessions[project] = (server, thread, url)
        return url

    def close(self, project=None):
        targets = [Path(project).resolve()] if project else list(self.sessions)
        for target in targets:
            session = self.sessions.pop(target, None)
            if session:
                server, thread, _ = session
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


def write_runtime_hint(project, directory):
    cli = directory / 'project-infra.exe'
    if not cli.is_file():
        return
    work = Path(project) / '.work'
    work.mkdir(exist_ok=True)
    work.joinpath('infra-runtime.md').write_text(
        '# 本次应用运行入口\n\n由应用启动时更新，移动应用后重新打开项目即可刷新。\n'
        '无需系统 Python，命令行入口为应用目录的 project-infra.exe。PowerShell 示例：\n\n'
        '```powershell\n& \'' + str(cli).replace("'", "''") + '\' --root \'' +
        str(project).replace("'", "''") + '\' validate\n```\n', encoding='utf-8')


def main(startup=True, on_ready=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox

    directory = application_directory()
    sessions = ProjectSessions()
    recent = load_recent(directory)
    root = tk.Tk()
    root.title('Project Infra')
    icon = Path(__file__).parent / 'assets/pi-monogram.ico'
    if sys.platform == 'win32' and icon.is_file():
        root.iconbitmap(str(icon))
    root.geometry('760x430')
    root.minsize(620, 360)
    root.configure(bg='#0b1119')
    tk.Label(root, text='PROJECT INFRA', bg='#0b1119', fg='#dce7ed', font=('Segoe UI', 22, 'bold')).pack(anchor='w', padx=28, pady=(24, 6))
    tk.Label(root, text='选择项目，打开设计与探索看板。', bg='#0b1119', fg='#8294a6', font=('Microsoft YaHei', 11)).pack(anchor='w', padx=28)
    listing = tk.Listbox(root, bg='#101922', fg='#dce7ed', selectbackground='#286e65', selectforeground='white',
                         highlightthickness=0, borderwidth=0, font=('Microsoft YaHei', 10), activestyle='none')
    listing.pack(fill='both', expand=True, padx=28, pady=18)
    status = tk.StringVar(value='首次使用请选择项目文件夹。空项目可以直接初始化。')
    tk.Label(root, textvariable=status, bg='#0b1119', fg='#8294a6', anchor='w', wraplength=700).pack(fill='x', padx=28)
    controls = tk.Frame(root, bg='#0b1119')
    controls.pack(fill='x', padx=28, pady=(16, 24))

    def refresh_list(selected=None):
        listing.delete(0, 'end')
        for project in recent:
            running = '  ● 已运行' if project in sessions.sessions else ''
            listing.insert('end', str(project) + running)
        if recent:
            index = recent.index(selected) if selected in recent else 0
            listing.selection_set(index)

    def open_project(project):
        try:
            url = sessions.open(project)
            try:
                write_runtime_hint(project, directory)
                if project in recent:
                    recent.remove(project)
                recent.insert(0, project)
                del recent[10:]
                save_recent(directory, recent)
            except OSError:
                messagebox.showwarning('无法保存启动记录', '看板可以使用，但无法保存运行入口或最近项目。请检查应用和项目目录的写入权限。', parent=root)
            refresh_list(project)
            status.set('运行中 · ' + url + '  关闭此窗口会停止看板服务。')
            webbrowser.open(url)
        except Exception as exc:
            messagebox.showerror('无法打开项目', str(exc), parent=root)

    def choose_project():
        chosen = filedialog.askdirectory(title='选择项目文件夹（可以是空目录）', parent=root)
        if not chosen:
            return
        project = Path(chosen).resolve()
        if not (project / '.project/config.toml').is_file():
            if not messagebox.askyesno('初始化这个项目？', '将在以下目录生成项目文件骨架，已有文件会保留：\n\n' + str(project), parent=root):
                return
            try:
                initialize(Store(project))
            except Exception as exc:
                messagebox.showerror('初始化失败', str(exc), parent=root)
                return
        open_project(project)

    def selected_project():
        selection = listing.curselection()
        return recent[selection[0]] if selection else None

    def open_selected():
        project = selected_project()
        open_project(project) if project else choose_project()

    def stop_selected():
        project = selected_project()
        if project:
            sessions.close(project)
            refresh_list(project)
            status.set('该项目服务已停止。项目文件保留原位。')

    def button(text, action, primary=False):
        tk.Button(controls, text=text, command=action, bg='#286e65' if primary else '#17232d', fg='#dce7ed',
                  activebackground='#338477', activeforeground='white', relief='flat', padx=16, pady=9).pack(side='left', padx=(0, 10))

    button('选择项目文件夹', choose_project, True)
    button('打开所选看板', open_selected)
    button('停止所选服务', stop_selected)
    listing.bind('<Double-Button-1>', lambda event: open_selected())
    refresh_list()

    def shutdown():
        sessions.close()
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', shutdown)
    # Existing users get straight to their last project with a double-click.
    if startup:
        root.after(200, lambda: open_project(recent[0]) if recent else choose_project())
    if on_ready:
        root.after(300, lambda: on_ready(root, shutdown))
    with application_mutex():
        root.mainloop()
