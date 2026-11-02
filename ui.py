"""主界面与交互逻辑：无边框半透明白色窗口、拖动、自由缩放、双页面、增删改查、持久化、开机自启。"""

import tkinter as tk
import uuid

from config import (
    APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT, MIN_WIDTH, MIN_HEIGHT, ALPHA,
    BG_COLOR, FG_COLOR, DONE_FG, ENTRY_BG, ACCENT_COLOR, FONT_FAMILY,
    FONT_SIZE, ALWAYS_ON_TOP,
)
from storage import load_todos, save_todos, load_geometry, save_geometry
from autostart import is_enabled, set_enabled


class TodoApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.attributes("-alpha", ALPHA)          # 半透明
        self.root.overrideredirect(True)               # 无边框
        self.root.attributes("-topmost", ALWAYS_ON_TOP)  # 置顶（可在 config 关闭）
        self.root.configure(bg=BG_COLOR)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        self.todos = load_todos()
        self.current_page = "active"   # "active" 待办 / "done" 已完成
        self._drag_x = 0
        self._drag_y = 0
        self._resize_dir = None
        self._resize_start = None
        self._collapsed = False          # 是否处于手动折叠态
        self._expanded_geo = None        # 折叠前记住的 (w, h, x, y)，展开时还原

        self._build_widgets()
        self._build_resize_grips()
        self._place_window()
        self._update_tabs()
        self.render()
        self.root.mainloop()

    # ---------- 窗口定位与拖动 ----------
    def _place_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        geo = load_geometry()
        if geo and len(geo) == 4:
            # 钳制到最小尺寸，防止历史存档（如自动隐藏残留的 40px 高度）压没列表区
            w = max(MIN_WIDTH, int(geo[0]))
            h = max(MIN_HEIGHT, int(geo[1]))
            x = int(geo[2])
            y = int(geo[3])
            # 若窗口整体跑出屏幕（换显示器/存档位置失效），回落到右下角
            if x + w <= 0 or y + h <= 0 or x >= sw or y >= sh:
                x = sw - w - 20
                y = sh - h - 20
        else:
            w, h = WINDOW_WIDTH, WINDOW_HEIGHT
            x = sw - w - 20
            y = sh - h - 20
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _start_drag(self, event):
        # 点 tab 按钮 / 折叠键 / 关闭键时不启动拖动，交给各自的点击逻辑
        if event.widget in (self.tab_active, self.tab_done, self.collapse_btn, self.close_btn):
            return
        self._drag_x = event.x_root
        self._drag_y = event.y_root

    def _on_drag(self, event):
        dx = event.x_root - self._drag_x
        dy = event.y_root - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self._drag_x = event.x_root
        self._drag_y = event.y_root

    # ---------- 自由缩放（无边框需手动手柄） ----------
    def _build_resize_grips(self):
        # 跳过 nw/ne 顶角，避免压住关闭按钮与标题栏；其余边/角均可拖拽缩放
        specs = {
            "n":  {"relx": 0.0, "rely": 0.0, "relwidth": 1.0, "height": 6, "anchor": "nw", "cursor": "sb_v_double_arrow"},
            "s":  {"relx": 0.0, "rely": 1.0, "relwidth": 1.0, "height": 6, "anchor": "sw", "cursor": "sb_v_double_arrow"},
            "w":  {"relx": 0.0, "rely": 0.0, "relwidth": 0.0, "width": 6, "relheight": 1.0, "anchor": "nw", "cursor": "sb_h_double_arrow"},
            "e":  {"relx": 1.0, "rely": 0.0, "relwidth": 0.0, "width": 6, "relheight": 1.0, "anchor": "ne", "cursor": "sb_h_double_arrow"},
            "sw": {"relx": 0.0, "rely": 1.0, "width": 12, "height": 12, "anchor": "sw", "cursor": "size_ne_sw"},
            "se": {"relx": 1.0, "rely": 1.0, "width": 12, "height": 12, "anchor": "se", "cursor": "size_nw_se"},
        }
        for dir_, spec in specs.items():
            g = tk.Frame(self.root, bg=BG_COLOR, cursor=spec.pop("cursor"))
            g.place(**spec)
            g.bind("<ButtonPress-1>", self._start_resize(dir_))
            g.bind("<ButtonRelease-1>", self._end_resize)

    def _start_resize(self, dir_):
        def handler(event):
            self._resize_dir = dir_
            self._resize_start = (
                event.x_root, event.y_root,
                self.root.winfo_width(), self.root.winfo_height(),
                self.root.winfo_x(), self.root.winfo_y(),
            )
            self.root.bind("<B1-Motion>", self._on_resize)
        return handler

    def _on_resize(self, event):
        if not self._resize_dir:
            return
        dx = event.x_root - self._resize_start[0]
        dy = event.y_root - self._resize_start[1]
        w0, h0, x0, y0 = self._resize_start[2:6]
        d = self._resize_dir
        nw, nh, nx, ny = w0, h0, x0, y0
        if "e" in d:
            nw = max(MIN_WIDTH, w0 + dx)
        if "s" in d:
            nh = max(MIN_HEIGHT, h0 + dy)
        if "w" in d:
            nw = max(MIN_WIDTH, w0 - dx)
            nx = x0 - (nw - w0)
        if "n" in d:
            nh = max(MIN_HEIGHT, h0 - dy)
            ny = y0 - (nh - h0)
        self.root.geometry(f"{nw}x{nh}+{nx}+{ny}")

    def _end_resize(self, _=None):
        self._resize_dir = None
        self.root.unbind("<B1-Motion>")
        self.save()   # 持久化新的尺寸/位置

    # ---------- 右键菜单（自启动 / 退出） ----------
    def _build_menu(self):
        self._autostart_var = tk.BooleanVar(value=is_enabled())
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_checkbutton(
            label="开机自动启动", variable=self._autostart_var,
            command=self._toggle_autostart,
        )
        self.menu.add_separator()
        self.menu.add_command(label="退出", command=self.on_close)

    def _show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def _toggle_autostart(self):
        try:
            set_enabled(self._autostart_var.get())
        except OSError:
            self._autostart_var.set(not self._autostart_var.get())

    # ---------- 构建静态控件 ----------
    def _build_widgets(self):
        self._build_menu()

        # 主体容器（无描边，保持通透）
        self.body = tk.Frame(self.root, bg=BG_COLOR, highlightthickness=0)
        self.body.pack(fill="both", expand=True)

        # 顶部选项卡：待办 / 已完成（兼作拖动把手与右键菜单，关闭键置于右上角）
        self.tab_bar = tk.Frame(self.body, bg=BG_COLOR, height=32)
        self.tab_bar.pack(fill="x", side="top", pady=(2, 4))
        self.tab_bar.pack_propagate(False)

        self.close_btn = tk.Button(
            self.tab_bar, text="✕", bg=BG_COLOR, fg=FG_COLOR, bd=0,
            font=(FONT_FAMILY, 12), width=3, command=self.on_close,
        )
        self.close_btn.pack(side="right", padx=2)
        self.close_btn.bind("<Button-3>", self._show_menu)

        # 折叠/展开按钮（点击切换：收起内容 / 恢复内容），位于关闭键左侧
        self.collapse_btn = tk.Button(
            self.tab_bar, text="▾", bg=BG_COLOR, fg=FG_COLOR, bd=0,
            font=(FONT_FAMILY, 12), width=3, command=self._toggle_collapse,
        )
        self.collapse_btn.pack(side="right", padx=2)
        self.collapse_btn.bind("<Button-3>", self._show_menu)

        self.tab_active = tk.Button(
            self.tab_bar, text="待办", bg=BG_COLOR, bd=0,
            font=(FONT_FAMILY, FONT_SIZE), command=lambda: self.switch_page("active"),
        )
        self.tab_done = tk.Button(
            self.tab_bar, text="已完成", bg=BG_COLOR, bd=0,
            font=(FONT_FAMILY, FONT_SIZE), command=lambda: self.switch_page("done"),
        )
        self.tab_active.pack(side="left", padx=12)
        self.tab_done.pack(side="left", padx=12)

        # 在选项卡空白处按住可拖动窗口、右键打开菜单
        # （在 tab 按钮 / 关闭键上按下时不触发，避免误拖动或切换页面）
        self.tab_bar.bind("<ButtonPress-1>", self._start_drag)
        self.tab_bar.bind("<B1-Motion>", self._on_drag)
        self.tab_bar.bind("<Button-3>", self._show_menu)

        # 可滚动列表区
        self.list_container = tk.Frame(self.body, bg=BG_COLOR)
        self.list_container.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        self.canvas = tk.Canvas(self.list_container, bg=BG_COLOR, highlightthickness=0)
        # Canvas 的 "units" 默认约 1 像素，滚轮会几乎不动；设 30px/格让滚动明显
        self.canvas.configure(yscrollincrement=30)
        self.scrollbar = tk.Scrollbar(self.list_container, orient="vertical",
                                      command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_COLOR)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.scrollable_frame.bind("<MouseWheel>", self._on_mousewheel)

        # 底部：输入框（已完成页隐藏，显示提示）
        self.bottom = tk.Frame(self.body, bg=BG_COLOR)
        self.bottom.pack(fill="x", side="bottom", padx=8, pady=(0, 8))
        self.entry = tk.Entry(
            self.bottom, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR,
            bd=0, font=(FONT_FAMILY, FONT_SIZE),
        )
        self.entry.pack(fill="x", ipady=6)
        self.entry.bind("<Return>", lambda e: self.add_item())
        self.entry.focus_set()
        self.done_hint = tk.Label(
            self.bottom, text="已完成事项", bg=ENTRY_BG, fg=DONE_FG,
            font=(FONT_FAMILY, FONT_SIZE),
        )
        self.done_hint.pack_forget()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ---------- 手动折叠 / 展开 ----------
    def _toggle_collapse(self):
        if not self._collapsed:
            # 折叠：记住当前尺寸位置，仅保留选项卡条
            self._expanded_geo = (
                self.root.winfo_width(), self.root.winfo_height(),
                self.root.winfo_x(), self.root.winfo_y(),
            )
            self.list_container.pack_forget()
            self.bottom.pack_forget()
            x, y = self._expanded_geo[2], self._expanded_geo[3]
            self.root.geometry(f"{self._expanded_geo[0]}x40+{x}+{y}")
            self.collapse_btn.configure(text="▸")
            self._collapsed = True
        else:
            # 展开：还原尺寸位置并重新显示内容
            w, h, x, y = self._expanded_geo
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.list_container.pack(fill="both", expand=True, padx=8, pady=(4, 4))
            self.bottom.pack(fill="x", side="bottom", padx=8, pady=(0, 8))
            self.collapse_btn.configure(text="▾")
            self._collapsed = False
            self.render()

    # ---------- 页面切换 ----------
    def switch_page(self, page):
        self.current_page = page
        if page == "done":
            self.entry.pack_forget()
            self.done_hint.pack(fill="x", ipady=6)
        else:
            self.done_hint.pack_forget()
            self.entry.pack(fill="x", ipady=6)
        self.render()

    def _update_tabs(self):
        active_n = sum(1 for t in self.todos if not t["done"])
        done_n = sum(1 for t in self.todos if t["done"])
        self.tab_active.configure(text=f"待办 {active_n}")
        self.tab_done.configure(text=f"已完成 {done_n}")
        if self.current_page == "active":
            self.tab_active.configure(fg=ACCENT_COLOR, font=(FONT_FAMILY, FONT_SIZE, "bold"))
            self.tab_done.configure(fg=DONE_FG, font=(FONT_FAMILY, FONT_SIZE))
        else:
            self.tab_done.configure(fg=ACCENT_COLOR, font=(FONT_FAMILY, FONT_SIZE, "bold"))
            self.tab_active.configure(fg=DONE_FG, font=(FONT_FAMILY, FONT_SIZE))

    # ---------- 数据操作 ----------
    def add_item(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.todos.append({"id": uuid.uuid4().hex[:8], "text": text, "done": False})
        self.entry.delete(0, tk.END)
        self.render()
        self.save()

    def toggle(self, todo):
        todo["done"] = not todo["done"]
        self.render()
        self.save()

    def delete(self, todo):
        self.todos = [t for t in self.todos if t["id"] != todo["id"]]
        self.render()
        self.save()

    def commit_edit(self, todo, new_text):
        new_text = new_text.strip()
        if new_text:
            todo["text"] = new_text
        self.render()
        self.save()

    # ---------- 渲染 ----------
    def render(self):
        self._update_tabs()
        for child in self.scrollable_frame.winfo_children():
            child.destroy()
        items = [t for t in self.todos if (self.current_page == "done") == t["done"]]
        if not items:
            tip = "暂无待办，输入后回车添加" if self.current_page == "active" else "暂无已完成事项"
            tk.Label(
                self.scrollable_frame, text=tip, bg=BG_COLOR, fg=DONE_FG,
                font=(FONT_FAMILY, FONT_SIZE),
            ).pack(pady=20)
        else:
            for todo in items:
                self._render_row(todo)
        # 滚轮事件只会派发给鼠标正下方的控件；把滚轮递归绑到列表里的
        # 每一个子控件（勾选框/文字/删除键/编辑框），保证停在任意条目上都能滚动
        self._bind_mousewheel_all(self.scrollable_frame)

    def _bind_mousewheel_all(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_mousewheel_all(child)

    def _render_row(self, todo):
        row = tk.Frame(self.scrollable_frame, bg=BG_COLOR)
        row.pack(fill="x", pady=2)

        done = todo["done"]
        tk.Button(
            row, text="☑" if done else "☐",
            bg=BG_COLOR, fg=DONE_FG if done else FG_COLOR, bd=0,
            font=(FONT_FAMILY, FONT_SIZE), width=3,
            command=lambda t=todo: self.toggle(t),
        ).pack(side="left")

        label = tk.Label(
            row, text=todo["text"], bg=BG_COLOR,
            fg=DONE_FG if done else FG_COLOR,
            font=(FONT_FAMILY, FONT_SIZE, "overstrike" if done else "normal"),
            anchor="w", justify="left",
        )
        label.pack(side="left", fill="x", expand=True, padx=4)
        label.bind(
            "<Double-Button-1>",
            lambda e, t=todo, l=label, r=row: self._start_edit(t, l, r),
        )

        tk.Button(
            row, text="✕", bg=BG_COLOR, fg=DONE_FG, bd=0,
            font=(FONT_FAMILY, FONT_SIZE), width=3,
            command=lambda t=todo: self.delete(t),
        ).pack(side="right")

    def _start_edit(self, todo, label, row):
        entry = tk.Entry(
            row, bg=ENTRY_BG, fg=FG_COLOR, insertbackground=FG_COLOR,
            bd=0, font=(FONT_FAMILY, FONT_SIZE),
        )
        entry.insert(0, todo["text"])
        label.pack_forget()
        entry.pack(side="left", fill="x", expand=True, padx=4)
        entry.focus_set()
        entry.icursor(tk.END)

        def commit(_=None):
            self.commit_edit(todo, entry.get())

        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda e: self.render())   # 取消编辑
        entry.bind("<FocusOut>", commit)                  # 失焦自动保存

    # ---------- 退出 ----------
    def save(self):
        save_todos(self.todos)
        # 折叠态下窗口实际高度为 40，保存时还原为展开尺寸，避免下次启动仍是折叠
        if self._collapsed and self._expanded_geo:
            w, h, x, y = self._expanded_geo
        else:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
        save_geometry(w, h, x, y)

    def on_close(self):
        self.save()
        self.root.destroy()
