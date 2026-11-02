"""全局配置：窗口尺寸、颜色、字体、持久化路径等。

如需调整外观或行为，修改本文件即可，无需改动逻辑代码。
"""

import os

APP_NAME = "TodoDesktop"

# 窗口尺寸（像素）
WINDOW_WIDTH = 250
WINDOW_HEIGHT = 340

# 自由缩放的最小尺寸下限
MIN_WIDTH = 180
MIN_HEIGHT = 150

# 整体透明度 0~1，越小越透明。背景为半透明白色，深字在 0.65 下仍清晰可读
ALPHA = 0.65

# 配色（白色半透明主题：浅色底 + 深色字，保证可读性）
BG_COLOR = "#fafafa"      # 半透明白色背景
FG_COLOR = "#1e1e1e"      # 正常文字（近黑）
DONE_FG = "#a0a0a0"       # 已完成文字（置灰）
ENTRY_BG = "#ffffff"      # 输入框底色
ACCENT_COLOR = "#2b7fff"  # 强调色（预留）

# 字体（Windows 下对中文友好）
FONT_FAMILY = "Microsoft YaHei UI"
FONT_SIZE = 11

# 是否始终置顶。True=像桌面挂件一样浮在最上层；
# 若希望“完全不干扰日常操作”，可改为 False，让它成为普通窗口。
ALWAYS_ON_TOP = True


def _app_dir():
    """数据存放目录：优先用系统 APPDATA，便携场景回退到程序目录。"""
    base = os.environ.get("APPDATA")
    if not base:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, APP_NAME)


def data_path():
    """待办数据文件（todos.json）。"""
    return os.path.join(_app_dir(), "todos.json")


def settings_path():
    """窗口位置等设置文件（settings.json）。"""
    return os.path.join(_app_dir(), "settings.json")
