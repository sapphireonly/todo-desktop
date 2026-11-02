# 桌面待办小工具（Windows）

一个无边框、半透明白色、可拖动、固定在桌面右下角的轻量待办清单。纯 Python 标准库实现，零运行时第三方依赖，资源占用极低，数据本地持久化，支持开机自动启动。

## 1. 可行性结论

| 需求 | 可行性 | 实现方式 |
|---|---|---|
| 右下角固定 + 无边框 + 可拖动 | ✅ 完全可行 | `overrideredirect(True)` 去边框；`geometry()` 定位右下角；标题栏鼠标事件实现拖动 |
| 半透明白色背景 + 清晰文字 | ✅ 可行 | `attributes('-alpha', 0.92)` 全局半透明；浅色底 (`#fafafa`) + 深色字 (`#1e1e1e`) 保证可读性，并加细描边防亮桌面看不清 |
| 增删改查 + 完成置灰/删除线 + 回车添加 | ✅ 完全可行 | 标准控件 + 双击行内编辑 + `Enter` 提交 |
| 本地持久化 | ✅ 完全可行 | JSON 存到 `%APPDATA%/TodoDesktop/` |
| 低占用 + 关闭入口 + 不干扰桌面 | ✅ 可行 | 标准库实现，仅 ~10MB；右上角 `✕` 关闭；置顶可关 |
| 开机自动启动 | ✅ 可行 | 写入当前用户注册表 `Run` 项（标题栏右键菜单开关） |

**替代方案提示（针对个别难点）：**
- 若要求"背景半透明、但文字 100% 不透明"：Tkinter 的 `-alpha` 是整体透明度，文字会随背景一同变淡（但 0.92 下仍清晰）。要做到背景半透明、文字全不透明，需换 **PyQt6/PySide6** 的 `WA_TranslucentBackground` + 自定义绘制（代价是打包体积增至 ~40MB，与"资源占用低"略有冲突）。
- 若要求"完全不干扰桌面操作"（不遮挡任何内容）：可把 `config.py` 中 `ALWAYS_ON_TOP` 改为 `False` 让其成为普通窗口；进阶做法是接系统托盘（需 `pystray`）实现"最小化到托盘/单击恢复"。

## 2. 实现方式概述

- **语言/框架**：Python 3 + Tkinter（标准库）。
- **窗口**：去边框 + 全局透明度；标题栏区域同时作为拖动把手（按住拖动即可调整位置），位置自动记忆。
- **交互**：
  - 底部输入框，回车即新增条目；
  - 左侧 `☐/☑` 点击切换完成状态（完成项加删除线并置灰）；
  - 文字**双击**进入行内编辑，回车保存、Esc 取消、失焦自动保存；
  - 右侧 `✕` 删除该条目；
  - 右上角 `✕` 关闭程序。
- **持久化**：待办存 `todos.json`，窗口位置存 `settings.json`，均位于 `%APPDATA%/TodoDesktop/`，关闭后重开自动还原。

## 3. 依赖与安装步骤

本工具**运行时不依赖任何第三方库**，只需 Python。

1. 安装 Python 3.8+（推荐 3.10+），安装时勾选 "Add Python to PATH"。
   下载：https://www.python.org/downloads/windows/
2. 验证（命令行）：
   ```bash
   python --version
   ```
3. 直接运行即可（见下）。如需把它打包成 exe，再装一个打包工具：
   ```bash
   pip install pyinstaller
   ```

## 4. 文件结构

```
todo_desktop/
├── main.py          # 入口：启动 TodoApp
├── config.py        # 配置：尺寸/透明度/配色/字体/置顶开关/路径
├── storage.py       # 持久化：todos.json 与 settings.json 的读写
├── ui.py            # 界面与交互：窗口、拖动、增删改查、渲染
├── autostart.py     # 开机自启动：注册表 Run 项的开关
├── requirements.txt # 依赖说明（仅打包时需要 pyinstaller）
└── README.md        # 本说明
```

数据文件（运行时自动生成，不在项目内）：
```
%APPDATA%/TodoDesktop/todos.json      # 待办清单
%APPDATA%/TodoDesktop/settings.json   # 窗口位置
```

## 5. 启动方法

方式一：命令行
```bash
cd todo_desktop
python main.py
```

方式二：双击
将 `main.py` 关联到 Python 后直接双击运行（或新建 `run.bat` 写 `python "%~dp0main.py"`）。

## 6. 打包为可执行文件（exe）

使用 PyInstaller 打包成**单文件、无控制台窗口**的 exe：

```bash
cd todo_desktop
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name TodoDesktop main.py
```

打包完成后，exe 位于 `dist/TodoDesktop.exe`，可单独拷贝到其他 Windows 机器直接运行（无需安装 Python）。

可选参数：
- `--icon=app.ico` 自定义图标；
- 若希望体积更小，可加 `--upx-dir` 配合 UPX 压缩。

## 7. 开机自动启动

在**标题栏右键**弹出菜单，勾选「开机自动启动」即可。其原理是向当前用户的注册表
`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` 写入一条启动项，
在**用户登录后**自动拉起本程序（非登录前，符合普通桌面工具的预期）。

- 源码运行时：注册表指向 `pythonw.exe main.py`（`pythonw` 不会弹出控制台黑框）。
- 打包成 exe 后：注册表直接指向 `TodoDesktop.exe`。
- 关闭自启动：再次右键取消勾选即可，会自动删除该注册表项。

> 若希望"开机即启动、无需登录"（如服务场景），可改用任务计划程序（Task Scheduler）
> 创建触发器为"计算机启动时"的任务，目标指向 `dist/TodoDesktop.exe`。

## 8. 常见问题

- **中文显示乱码/方块**：确保系统有"Microsoft YaHei UI"字体，或在 `config.py` 把 `FONT_FAMILY` 改成你系统已有的中文字体。
- **想让它不置顶**：编辑 `config.py`，设 `ALWAYS_ON_TOP = False`。
- **想换背景透明度**：改 `config.py` 的 `ALPHA`（0~1，越小越透明）。
- **数据在哪**：`%APPDATA%/TodoDesktop/`，重装系统前备份该目录即可保留清单。
