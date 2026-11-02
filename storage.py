"""本地持久化：待办数据与窗口位置均以 JSON 形式保存到磁盘。

关闭程序后再次打开，清单与窗口位置都会被还原。
"""

import json
import os

from config import data_path, settings_path


def _ensure_dir(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)


def load_todos():
    """读取待办列表，文件不存在或损坏时返回空列表。"""
    try:
        with open(data_path(), "r", encoding="utf-8") as f:
            return json.load(f).get("todos", [])
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return []


def save_todos(todos):
    data = _read_data()
    data["todos"] = todos
    _write_data(data)


def load_geometry():
    """读取上次窗口几何信息 (w, h, x, y)；无记录返回 None。"""
    try:
        val = json.load(open(settings_path(), "r", encoding="utf-8")).get("geometry")
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return None
    if isinstance(val, (list, tuple)) and len(val) == 4:
        return tuple(int(v) for v in val)
    return None


def save_geometry(w, h, x, y):
    data = _read_settings()
    data["geometry"] = [w, h, x, y]
    _ensure_dir(settings_path())
    with open(settings_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_data():
    try:
        with open(data_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_data(data):
    _ensure_dir(data_path())
    with open(data_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_settings():
    try:
        with open(settings_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
