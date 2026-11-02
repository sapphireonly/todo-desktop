"""开机自启动：通过写入当前用户注册表 Run 项，在用户登录后自动启动。

- 打包成 exe 后：直接写入 exe 路径。
- 源码运行时：用 pythonw.exe 启动 main.py，避免弹出控制台黑框。
"""

import os
import sys
import winreg

APP_NAME = "TodoDesktop"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command():
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后的可执行文件
        return f'"{sys.executable}"'
    # 源码运行：用同目录的 pythonw.exe（无控制台），指向 main.py
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
    return f'"{pythonw}" "{script}"'


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except FileNotFoundError:
        return False


def set_enabled(enable):
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
