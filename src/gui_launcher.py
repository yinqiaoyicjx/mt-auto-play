"""
魔塔自动游玩脚本 - GUI图形界面
提供实时控制、状态显示和决策可视化
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from datetime import datetime
from PIL import Image, ImageTk
import cv2
import numpy as np
import queue
import sys
import traceback

# 捕获导入错误，提供友好的错误信息
try:
    from capture import ScreenCapture
    from detector import GameElementDetector
    from state import GameState
    from planner import GamePlanner
    from controller import SmartController
    from resource_manager import ResourceManager
    from game_database import GameDatabase
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有模块都已正确安装")
    sys.exit(1)


class MotaGUI:
    """魔塔自动游玩GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("MOTA Auto-Play Bot")
        self.root.geometry("1000x700")

        # 控制变量
        self.running = False
        self.paused = False
        self.bot_thread = None
        self.debug_mode = tk.BooleanVar(value=True)
        self.auto_save_var = tk.BooleanVar(value=True)
        self.save_info_labels = {}
        self.last_auto_save_step = 0  # 上次自动保存时的步数

        # 游戏模块
        self.capture = None
        self.detector = None
        self.state = None
        self.planner = None
        self.controller = None
        self.resource_manager = None
        self.game_db = GameDatabase("data/game_database.json")  # 游戏基础数据库
        self.manual_capture_region = None  # 手动指定的截图区域

        # 线程安全的数据共享
        self.current_frame = None
        self.current_decision = None
        self.current_action = None
        self.frame_lock = threading.Lock()

        # 创建界面
        self._create_widgets()

        # 窗口信息
        self.window_info = {
            'title': 'Not detected',
            'handle': None,
            'rect': None,
            'capture_rect': None
        }

        # 启动UI更新循环
        self._start_ui_updates()

        # 初始化存档信息显示
        self.root.after(100, self._update_save_info_display)

    def _create_widgets(self):
        """创建界面组件"""

        # ===== 顶部控制栏 =====
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill=tk.X)

        # 按钮组
        ttk.Button(control_frame, text="选择区域", command=self.select_capture_region, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Separator(control_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(control_frame, text="开始", command=self.start_bot, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="暂停", command=self.pause_bot, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="停止", command=self.stop_bot, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="退出", command=self.root.quit, width=10).pack(side=tk.LEFT, padx=5)

        # 调试模式复选框
        ttk.Checkbutton(control_frame, text="调试模式", variable=self.debug_mode).pack(side=tk.LEFT, padx=20)

        # ===== 第二控制栏（存档管理）=====
        save_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        save_frame.pack(fill=tk.X)

        ttk.Label(save_frame, text="存档/读取:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(save_frame, text="读取 1", command=lambda: self.load_game(1), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(save_frame, text="读取 2", command=lambda: self.load_game(2), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(save_frame, text="读取 3", command=lambda: self.load_game(3), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Separator(save_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(save_frame, text="保存 1", command=lambda: self.save_game(1), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(save_frame, text="保存 2", command=lambda: self.save_game(2), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(save_frame, text="保存 3", command=lambda: self.save_game(3), width=8).pack(side=tk.LEFT, padx=2)
        ttk.Separator(save_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(save_frame, text="快速保存", command=self.quick_save, width=10).pack(side=tk.LEFT, padx=5)

        # 自动保存复选框
        self.auto_save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(save_frame, text="自动保存", variable=self.auto_save_var).pack(side=tk.LEFT, padx=10)

        # ===== 第三控制栏（存档信息显示）=====
        info_frame = ttk.Frame(self.root, padding=(10, 0, 10, 5))
        info_frame.pack(fill=tk.X)

        self.save_info_labels = {}
        for i in range(1, 4):
            label = ttk.Label(info_frame, text=f"槽位 {i}: [空]", font=('Arial', 8), width=40)
            label.pack(side=tk.LEFT, padx=5)
            self.save_info_labels[i] = label

        # ===== 第四控制栏（游戏数据库管理）=====
        db_frame = ttk.Frame(self.root, padding=(10, 0, 10, 5))
        db_frame.pack(fill=tk.X)

        ttk.Label(db_frame, text="游戏数据库:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(db_frame, text="查看", command=self.view_database, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(db_frame, text="导出", command=self.export_database, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(db_frame, text="重置", command=self.reset_database, width=8).pack(side=tk.LEFT, padx=2)

        # 数据库状态显示
        self.db_status_label = ttk.Label(db_frame, text="", font=('Arial', 8))
        self.db_status_label.pack(side=tk.LEFT, padx=15)

        # 加载数据库并更新显示
        self.root.after(100, self._load_database)

        # ===== 中间内容区 =====
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：游戏画面和状态
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 游戏画面
        self.canvas_frame = ttk.LabelFrame(left_frame, text="游戏画面", padding=5)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_frame, width=416, height=416, bg='black')
        self.canvas.pack(pady=5)

        # 窗口信息显示
        window_info_frame = ttk.LabelFrame(left_frame, text="窗口信息", padding=5)
        window_info_frame.pack(fill=tk.X, pady=5)

        self.window_info_labels = {}
        window_items = [
            ('title', '窗口:'),
            ('pos', '位置:'),
            ('size', '大小:'),
            ('capture', '截图区域:'),
        ]

        for key, label in window_items:
            frame = ttk.Frame(window_info_frame)
            frame.pack(fill=tk.X, pady=1)
            ttk.Label(frame, text=label, width=15).pack(side=tk.LEFT)
            self.window_info_labels[key] = ttk.Label(frame, text="--", font=('Consolas', 9))
            self.window_info_labels[key].pack(side=tk.LEFT)

        # 游戏状态
        status_frame = ttk.LabelFrame(left_frame, text="游戏状态", padding=5)
        status_frame.pack(fill=tk.X, pady=5)

        self.status_labels = {}
        status_items = [
            ('floor', '楼层'),
            ('hp', '生命'),
            ('atk', '攻击'),
            ('def', '防御'),
            ('gold', '金币'),
            ('keys', '钥匙'),
        ]

        for i, (key, label) in enumerate(status_items):
            row = i // 3
            col = (i % 3) * 2
            ttk.Label(status_frame, text=f"{label}:").grid(row=row, column=col, sticky=tk.E, padx=5)
            self.status_labels[key] = ttk.Label(status_frame, text="--", font=('Arial', 10, 'bold'))
            self.status_labels[key].grid(row=row, column=col+1, sticky=tk.W, padx=5)

        # 当前决策
        decision_frame = ttk.LabelFrame(left_frame, text="当前决策", padding=5)
        decision_frame.pack(fill=tk.X, pady=5)

        self.decision_label = ttk.Label(decision_frame, text="等待开始...",
                                        wraplength=300, justify=tk.LEFT,
                                        font=('Arial', 10))
        self.decision_label.pack(fill=tk.X)

        # 决策详情
        detail_frame = ttk.LabelFrame(left_frame, text="决策详情", padding=5)
        detail_frame.pack(fill=tk.X, pady=5)

        self.detail_text = tk.Text(detail_frame, height=4, wrap=tk.WORD, font=('Consolas', 9))
        self.detail_text.pack(fill=tk.X)

        # 右侧：日志输出
        right_frame = ttk.LabelFrame(content_frame, text="活动日志", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # ===== 底部状态栏 =====
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN, padding=2)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_bar, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)

        self.time_var = tk.StringVar(value="运行: 0秒")
        ttk.Label(status_bar, textvariable=self.time_var).pack(side=tk.RIGHT, padx=5)

        self.start_time = None

    def _start_ui_updates(self):
        """启动UI更新循环（在主线程中）"""
        # 使用延迟启动，避免阻塞GUI初始化
        self.root.after(500, self._update_preview_from_thread)
        self.root.after(500, self._update_status_from_thread)
        self.root.after(1000, self.update_timer)

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def select_capture_region(self):
        """选择截图区域"""
        if self.running:
            self.log("请先停止机器人！")
            return

        self.log("开始选择截图区域...")
        self.log("请拖动鼠标选择游戏截图区域")

        # 创建区域选择窗口
        selector = RegionSelector(self.root, self.on_region_selected)
        self.region_selector = selector

    def on_region_selected(self, region: dict):
        """区域选择完成回调"""
        self.manual_capture_region = region
        self.log(f"区域已选择: {region['width']}x{region['height']} 位置 ({region['left']}, {region['top']})")

        # 如果已创建capture对象，更新其区域
        if self.capture:
            self.capture.set_manual_region(region)
        else:
            # 设置手动区域标志，start_bot时会使用
            self.log("机器人启动时将应用该区域")

    def _try_focus_game_window(self):
        """尝试激活游戏窗口（手动模式下使用）"""
        try:
            import win32gui
            import win32con

            # 尝试查找包含"魔塔"或"MOTA"的窗口
            def callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if '魔塔' in title or 'MOTA' in title or 'magic' in title.lower():
                        windows.append((hwnd, title))
                return True

            windows = []
            win32gui.EnumWindows(callback, windows)

            if windows:
                # 找到了游戏窗口，激活它
                hwnd, title = windows[0]
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetFocus(hwnd)
                self.log(f"成功激活游戏窗口: {title}")
                return True
            else:
                self.log("无法自动找到游戏窗口")
                self.log("请手动点击游戏窗口！")
                return False

        except Exception as e:
            self.log(f"激活游戏窗口失败: {e}")
            self.log("请手动点击游戏窗口！")
            return False

    def start_bot(self):
        """启动机器人"""
        if self.running:
            self.log("机器人已在运行！")
            return

        self.log("启动机器人...")
        self.log("=" * 50)
        self.log("重要提示: 请确保以下条件:")
        self.log("  1. 游戏窗口已启动")
        self.log("  2. 游戏窗口在前台且可见")
        self.log("  3. 不要移动游戏窗口")
        self.log("  4. 不要切换到其他窗口")
        self.log("=" * 50)

        self.running = True
        self.paused = False
        self.start_time = time.time()

        # 初始化游戏模块
        try:
            self.log("Initializing modules...")

            self.log("Creating ScreenCapture...")
            if self.manual_capture_region:
                self.capture = ScreenCapture(manual_region=self.manual_capture_region)
                self.log(f"Using manual region: {self.manual_capture_region}")
                self.log("Manual mode: Window detection skipped")
            else:
                self.capture = ScreenCapture()
                # 只有在自动模式下才检查窗口句柄
                if not self.capture.window_handle:
                    self.log("ERROR: 未找到游戏窗口!")
                    self.log("请先启动游戏，然后重新点击Start")
                    self.running = False
                    self.status_var.set("No Game Window")
                    return
            self.log("ScreenCapture initialized")

            self.log("Creating GameElementDetector...")
            self.detector = GameElementDetector()
            self.log("GameElementDetector initialized")

            self.log("Creating GameState...")
            self.state = GameState(max_floors=24)
            self.log("GameState initialized")

            self.log("Creating GamePlanner...")
            self.planner = GamePlanner(self.state)
            self.log("GamePlanner initialized")

            self.log("Creating SmartController...")
            self.controller = SmartController()
            self.log("SmartController initialized")

            self.log("Creating ResourceManager...")
            self.resource_manager = ResourceManager(self.state)
            self.log("ResourceManager initialized")

            # 获取窗口信息
            self.log("Getting window info...")
            self._update_window_info()

            self.log("All modules initialized successfully")

            # 手动模式下，尝试激活游戏窗口
            if self.manual_capture_region:
                self.log("Manual mode: Attempting to focus game window...")
                self._try_focus_game_window()
                self.log("=" * 50)

            self.status_var.set("Running")

            # 启动bot线程
            self.log("Starting bot thread...")
            self.bot_thread = threading.Thread(target=self._run_bot, daemon=True)
            self.bot_thread.start()
            self.log("Bot thread started - Auto-play begins!")

        except Exception as e:
            self.log(f"Failed to start: {e}")
            self.log(traceback.format_exc())
            self.running = False
            self.status_var.set("Error")

    def pause_bot(self):
        """暂停/恢复"""
        if not self.running:
            return

        self.paused = not self.paused
        if self.paused:
            self.status_var.set("已暂停")
            self.log("机器人已暂停")
        else:
            self.status_var.set("运行中")
            self.log("机器人已恢复")

    def stop_bot(self):
        """停止"""
        self.running = False
        self.paused = False
        self.status_var.set("已停止")
        self.log("机器人已停止")

        # 等待线程结束
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=2)

        # 停止时自动保存
        if self.state and self.auto_save_var.get():
            self.log("停止时自动保存...")
            self.quick_save()

        # 保存游戏数据库
        if not self.game_db.is_empty():
            self.log("保存游戏数据库...")
            self.game_db.save()
            self.log(f"数据库已保存: {self.game_db.metadata['total_floors']} 层")

    def quick_save(self):
        """快速保存到存档槽1"""
        if not self.state:
            self.log("没有游戏状态可以保存！")
            return
        self.save_game(1)

    def save_game(self, slot: int):
        """保存游戏到指定存档槽"""
        if not self.state:
            self.log("没有游戏状态可以保存！")
            return

        import os
        SAVE_DIR = "data/saves"
        os.makedirs(SAVE_DIR, exist_ok=True)
        filepath = os.path.join(SAVE_DIR, f"save_{slot}.json")

        try:
            self.state.save_state(filepath)
            self.log(f"游戏已保存到 槽位 {slot}")
            self._update_save_info_display()
        except Exception as e:
            self.log(f"保存失败: {e}")

    def load_game(self, slot: int):
        """加载指定存档槽"""
        if self.running:
            self.log("请先停止机器人！")
            return

        import os
        SAVE_DIR = "data/saves"
        filepath = os.path.join(SAVE_DIR, f"save_{slot}.json")

        if not os.path.exists(filepath):
            self.log(f"槽位 {slot} 是空的！")
            return

        try:
            # 初始化state（如果还没有）
            if not self.state:
                self.state = GameState(max_floors=24)

            if self.state.load_state(filepath):
                self.log(f"从 槽位 {slot} 加载游戏")
                self.log(f"  楼层: {self.state.player.floor}")
                self.log(f"  生命: {self.state.player.hp}/{self.state.player.max_hp}")
                self.log(f"  钥匙: 黄{self.state.player.yellow_keys} 蓝{self.state.player.blue_keys} 红{self.state.player.red_keys}")
                self.log(f"  金币: {self.state.player.gold}")
                self.log(f"  步数: {self.state.steps}")
                self._update_save_info_display()
            else:
                self.log(f"从 槽位 {slot} 加载失败")
        except Exception as e:
            self.log(f"加载错误: {e}")
            import traceback
            self.log(traceback.format_exc())

    def _update_save_info_display(self):
        """更新存档信息显示"""
        import os
        import json
        SAVE_DIR = "data/saves"

        for i in range(1, 4):
            filepath = os.path.join(SAVE_DIR, f"save_{i}.json")
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        state_dict = json.load(f)

                    p = state_dict['player']
                    time_str = state_dict.get('save_time', '')
                    if ' ' in time_str:
                        time_str = time_str.split()[1][:5]  # 只显示时分

                    text = f"槽位 {i}: F{p['floor']} HP:{p['hp']}/{p['max_hp']} 攻:{p['atk']} 金:{p['gold']} {time_str}"
                except:
                    text = f"槽位 {i}: [损坏]"
            else:
                text = f"槽位 {i}: [空]"

            if i in self.save_info_labels:
                self.save_info_labels[i].config(text=text)

    def _check_auto_save(self, step_count: int):
        """检查是否需要自动保存（每50步或切换楼层时）"""
        if not self.state or not self.auto_save_var.get():
            return

        current_floor = self.state.player.floor
        last_floor = getattr(self, '_last_save_floor', current_floor)

        # 每50步或切换楼层时自动保存
        should_save = (step_count - self.last_auto_save_step >= 50) or (current_floor != last_floor)

        if should_save:
            self.quick_save()
            self.last_auto_save_step = step_count
            self._last_save_floor = current_floor

    def _load_database(self):
        """加载游戏数据库"""
        if self.game_db.load():
            self.log(f"游戏数据库已加载: {self.game_db.metadata['total_floors']} 层")
        else:
            self.log("未找到游戏数据库，探索过程中将创建新数据库")
        self._update_db_status_display()

    def _update_db_status_display(self):
        """更新数据库状态显示"""
        if self.game_db.is_empty():
            text = "空"
        else:
            text = f"层数: {self.game_db.metadata['total_floors']} | 已探索: {','.join(map(str, sorted(self.game_db.metadata['explored_floors'])))}"
        self.db_status_label.config(text=text)

    def view_database(self):
        """查看数据库内容"""
        summary = self.game_db.export_summary()
        self.log("=" * 50)
        for line in summary.split('\n'):
            self.log(line)
        self.log("=" * 50)

    def export_database(self):
        """导出数据库到文件"""
        try:
            self.game_db.save()
            self.log("游戏数据库导出成功")
            self._update_db_status_display()
        except Exception as e:
            self.log(f"导出数据库失败: {e}")

    def reset_database(self):
        """重置数据库"""
        if self.running:
            self.log("请先停止机器人！")
            return

        from tkinter import messagebox
        if messagebox.askyesno("确认重置", "确定要重置游戏数据库吗？所有探索数据将会丢失！"):
            self.game_db.reset()
            self.game_db.save()
            self.log("游戏数据库已重置")
            self._update_db_status_display()

    def _update_database_from_detection(self, floor_num: int, frame: np.ndarray,
                                        monsters, doors, keys, stairs):
        """从检测结果更新游戏数据库"""
        if not self.detector:
            return

        # 获取网格大小
        grid_size = self.detector.GRID_SIZE
        h, w = frame.shape[:2]
        width = w // grid_size
        height = h // grid_size

        # 构建网格数据
        grid = np.zeros((height, width), dtype=int)

        # 标记怪物
        for monster in monsters:
            if 0 <= monster.y < height and 0 <= monster.x < width:
                grid[monster.y, monster.x] = 3

        # 标记门
        for door in doors:
            if 0 <= door.y < height and 0 <= door.x < width:
                grid[door.y, door.x] = 2

        # 标记钥匙
        for key in keys:
            if 0 <= key.y < height and 0 <= key.x < width:
                grid[key.y, key.x] = 4

        # 标记楼梯
        if stairs.get('up'):
            s = stairs['up']
            if 0 <= s.y < height and 0 <= s.x < width:
                grid[s.y, s.x] = 5
        if stairs.get('down'):
            s = stairs['down']
            if 0 <= s.y < height and 0 <= s.x < width:
                grid[s.y, s.x] = 5

        # 更新数据库
        self.game_db.update_floor_from_detection(
            floor_num, width, height, monsters, doors, keys, stairs, grid
        )

        # 自动保存数据库（每探索一个新楼层）
        if not self.game_db.has_floor(floor_num):
            self.game_db.save()
            self._update_db_status_display()

    def _update_window_info(self):
        """更新窗口信息显示"""
        try:
            import win32gui

            if self.capture and self.capture.window_handle:
                # 获取窗口信息
                handle = self.capture.window_handle
                title = win32gui.GetWindowText(handle)
                rect = win32gui.GetWindowRect(handle)
                monitor = self.capture.monitor

                # 更新显示
                self.window_info_labels['title'].config(
                    text=f"{title[:40]}... (HWND: {handle})" if len(title) > 40 else title
                )
                self.window_info_labels['pos'].config(
                    text=f"({rect[0]}, {rect[1]})"
                )
                self.window_info_labels['size'].config(
                    text=f"{rect[2] - rect[0]}x{rect[3] - rect[1]}"
                )

                # 显示截图区域
                if monitor:
                    self.window_info_labels['capture'].config(
                        text=f"x:{monitor['left']}, y:{monitor['top']}, {monitor['width']}x{monitor['height']}"
                    )

                self.log(f"Found window: {title}")
                self.log(f"Capture region: {monitor['width']}x{monitor['height']} at ({monitor['left']}, {monitor['top']})")
            else:
                self.window_info_labels['title'].config(text="Not detected")
                self.log("Game window not found! Please start the game first.")

        except Exception as e:
            self.log(f"Failed to get window info: {e}")
            self.window_info_labels['title'].config(text="Error detecting window")

    def _run_bot(self):
        """Bot主循环（在独立线程中运行）"""
        loop_count = 0
        last_action = None
        repeat_count = 0
        MAX_REPEAT = 3
        no_player_count = 0  # 检测不到玩家的次数

        self.log("Bot loop started...")

        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            try:
                loop_count += 1

                # 定期检查窗口是否被移动（每50步检查一次）
                if loop_count % 50 == 0:
                    if self.capture.check_window_moved():
                        self.log("WARNING: 窗口已移动，继续运行可能导致问题")
                        self.log("建议: 点击Stop停止，然后重新启动")

                # 1. 截图
                frame = self.capture.capture()

                # 保存frame到共享变量（线程安全）
                with self.frame_lock:
                    self.current_frame = frame

                # 2. 检测画面稳定性
                if not self._is_stable():
                    time.sleep(0.05)
                    continue

                # 3. 识别游戏元素
                player = self.detector.detect_player(frame)
                if not player:
                    no_player_count += 1
                    if no_player_count <= 5:  # 只显示前5次
                        self.log(f"帧 {loop_count}: 无法检测到玩家！")
                    elif no_player_count == 6:
                        self.log("玩家检测多次失败。请检查:")
                        self.log("  1. 游戏是否正在运行且可见？")
                        self.log("  2. 截图区域是否正确？")
                        self.log("  3. 尝试先收集玩家模板")
                    time.sleep(0.1)
                    continue

                # 重置计数器
                no_player_count = 0

                monsters = self.detector.detect_monsters(frame)
                doors = self.detector.detect_doors(frame)
                keys = self.detector.detect_keys(frame)
                stairs = self.detector.detect_stairs(frame)

                # 4. 更新游戏状态
                self.state.update_player_position(player.x, player.y)
                current_floor = self.state.get_current_floor()
                current_floor.monsters = monsters
                current_floor.doors = doors
                current_floor.keys = keys
                current_floor.stairs = stairs

                # 更新游戏数据库
                self._update_database_from_detection(
                    self.state.current_floor, frame, monsters, doors, keys, stairs
                )

                # 自动保存检查
                self._check_auto_save(loop_count)

                # 5. 获取决策
                action, plan = self._get_decision()

                # 保存决策到共享变量（线程安全）
                with self.frame_lock:
                    self.current_decision = plan
                    self.current_action = action

                # 6. 检查重复
                if action and action == last_action:
                    repeat_count += 1
                    if repeat_count >= MAX_REPEAT:
                        self.log(f"警告: 动作重复 {MAX_REPEAT} 次！")
                else:
                    repeat_count = 0
                    last_action = action

                # 7. 执行动作
                if action:
                    self.controller.execute(action)

                # 8. 记录日志（每10步）
                if loop_count % 10 == 0:
                    self.log(f"步骤 {loop_count}: {plan.reason if plan else '思考中...'}")

                # 9. 控制速度
                time.sleep(0.15)

            except Exception as e:
                self.log(f"循环错误: {e}")
                import traceback
                self.log(traceback.format_exc())
                time.sleep(0.5)

    def _get_decision(self):
        """获取下一步决策"""
        from planner import Plan, Action

        # 使用资源管理器推荐
        recommended = self.resource_manager.recommend_action()
        if recommended:
            plan = Plan(
                action=Action.WAIT,
                target_x=recommended.target_x,
                target_y=recommended.target_y,
                expected_cost=0,
                expected_gain=0,
                reason=recommended.description
            )
            action = self.planner.get_next_step(plan)
            return action, plan

        # 备用
        plan = self.planner.plan_next_action()
        action = self.planner.get_next_step(plan)
        return action, plan

    def _update_preview(self, frame):
        """更新画面预览 - 已废弃，使用线程安全版本"""
        pass

    def _update_preview_from_thread(self):
        """从主线程更新画面预览（线程安全）"""
        # 始终调度下一次更新，确保循环不会中断
        self.root.after(100, self._update_preview_from_thread)

        try:
            frame = None
            with self.frame_lock:
                frame = self.current_frame

            # 更新canvas
            self.canvas.delete("all")

            if frame is None:
                # 没有截图时显示提示
                self.canvas.create_text(
                    208, 188,
                    text="无游戏画面",
                    fill='white',
                    font=('Arial', 14, 'bold')
                )

                if self.manual_capture_region:
                    region = self.manual_capture_region
                    self.canvas.create_text(
                        208, 218,
                        text=f"手动区域: {region['width']}x{region['height']} 位置 ({region['left']}, {region['top']})",
                        fill='yellow',
                        font=('Arial', 10)
                    )
                else:
                    self.canvas.create_text(
                        208, 218,
                        text="点击 '选择区域' 按钮选择截图区域",
                        fill='yellow',
                        font=('Arial', 10)
                    )
                return

            # Debug模式：在原图上绘制检测框
            if self.debug_mode.get() and self.detector:
                frame = self._draw_detection_boxes(frame)

            # 调整大小
            h, w = frame.shape[:2]
            scale = min(416 / w, 416 / h)
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(frame, (new_w, new_h))

            # 转换颜色
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb)
            photo = ImageTk.PhotoImage(pil_image)

            # 显示图像
            self.canvas.create_image(208, 208, image=photo)
            self.canvas.image = photo  # 保持引用

            # 画红框边框，表示这是截图区域
            self.canvas.create_rectangle(
                208 - new_w // 2, 208 - new_h // 2,
                208 + new_w // 2, 208 + new_h // 2,
                outline='red', width=2
            )

            # 显示截图区域信息
            if self.capture and self.capture.monitor:
                region = self.capture.monitor
                info_text = f"截图: {region['width']}x{region['height']} @ ({region['left']}, {region['top']})"
                self.canvas.create_text(
                    208, 208 - new_h // 2 - 15,
                    text=info_text,
                    fill='red',
                    font=('Arial', 9, 'bold')
                )

        except Exception as e:
            # Debug模式下显示错误
            if self.debug_mode.get():
                print(f"Preview update error: {e}")
            pass

    def _draw_detection_boxes(self, frame: np.ndarray) -> np.ndarray:
        """在画面上绘制检测框（Debug模式）"""
        debug_frame = frame.copy()

        try:
            # 绘制网格辅助线（半透明）
            h, w = debug_frame.shape[:2]
            grid_size = self.detector.GRID_SIZE if self.detector else 32

            # 绘制网格线（很淡的灰色）
            for x in range(0, w, grid_size):
                cv2.line(debug_frame, (x, 0), (x, h), (50, 50, 50), 1)
            for y in range(0, h, grid_size):
                cv2.line(debug_frame, (0, y), (w, y), (50, 50, 50), 1)

            # 绘制玩家检测框（绿色）
            player_detection = self.detector.get_last_player_detection()
            if player_detection:
                bbox = player_detection['bbox']
                center = player_detection['center']
                grid_pos = player_detection['grid_pos']

                # 绘制检测轮廓
                cv2.drawContours(debug_frame, [player_detection['contour']], -1, (0, 255, 0), 2)

                # 绘制边界框
                cv2.rectangle(debug_frame,
                             (bbox[0], bbox[1]),
                             (bbox[0] + bbox[2], bbox[1] + bbox[3]),
                             (0, 255, 0), 2)

                # 绘制中心点
                cv2.circle(debug_frame, center, 5, (0, 255, 0), -1)

                # 绘制网格位置标签
                label = f"Player: ({grid_pos[0]}, {grid_pos[1]})"
                cv2.putText(debug_frame, label, (bbox[0], bbox[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # 如果检测不到玩家，显示提示
            else:
                cv2.putText(debug_frame, "No Player Detected!", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        except Exception as e:
            print(f"Draw detection boxes error: {e}")

        return debug_frame

    def _update_status_from_thread(self):
        """从主线程更新状态显示（线程安全）"""
        # 始终调度下一次更新，确保循环不会中断
        self.root.after(100, self._update_status_from_thread)

        try:
            if self.state and self.state.player:
                player = self.state.player
                self.status_labels['floor'].config(text=str(player.floor))
                self.status_labels['hp'].config(text=f"{player.hp}/{player.max_hp}")
                self.status_labels['atk'].config(text=str(player.atk))
                self.status_labels['def'].config(text=str(player.defense))
                self.status_labels['gold'].config(text=str(player.gold))
                self.status_labels['keys'].config(text=f"Y{player.yellow_keys} B{player.blue_keys} R{player.red_keys}")

            # 更新决策显示
            if self.current_decision:
                self.decision_label.config(text=f"{self.current_decision.reason}")
                self._update_decision_detail_safe(self.current_decision, self.current_action)

            # 更新窗口信息
            self._update_window_info_from_thread()

        except Exception:
            pass

    def _update_window_info_from_thread(self):
        """从主线程更新窗口信息显示（线程安全）"""
        try:
            import win32gui

            if self.capture and self.capture.window_handle:
                # 获取窗口信息
                handle = self.capture.window_handle
                title = win32gui.GetWindowText(handle)
                rect = win32gui.GetWindowRect(handle)
                monitor = self.capture.monitor

                # 更新显示
                self.window_info_labels['title'].config(
                    text=f"{title[:40]}... (HWND: {handle})" if len(title) > 40 else title
                )
                self.window_info_labels['pos'].config(
                    text=f"({rect[0]}, {rect[1]})"
                )
                self.window_info_labels['size'].config(
                    text=f"{rect[2] - rect[0]}x{rect[3] - rect[1]}"
                )

                # 显示截图区域
                if monitor:
                    self.window_info_labels['capture'].config(
                        text=f"x:{monitor['left']}, y:{monitor['top']}, {monitor['width']}x{monitor['height']}"
                    )

        except Exception:
            pass

    def _update_status_ui(self):
        """更新状态显示 - 已废弃，使用线程安全版本"""
        pass

    def _update_decision_detail(self, plan, action):
        """更新决策详情 - 已废弃，使用线程安全版本"""
        pass

    def _update_decision_detail_safe(self, plan, action):
        """线程安全的决策详情更新"""
        try:
            self.detail_text.delete(1.0, tk.END)

            if action:
                self.detail_text.insert(tk.END, f"动作: {action.value}\n")
            self.detail_text.insert(tk.END, f"目标: ({plan.target_x}, {plan.target_y})\n")
            self.detail_text.insert(tk.END, f"消耗: {plan.expected_cost} 生命\n")
            self.detail_text.insert(tk.END, f"收益: {plan.expected_gain} 金币")
        except Exception:
            pass

    def _is_stable(self):
        """检查画面是否稳定"""
        # 简化版本，实际可以使用FrameBuffer
        return True

    def update_timer(self):
        """更新定时器"""
        # 始终调度下一次更新，确保循环不会中断
        self.root.after(100, self.update_timer)

        try:
            if self.start_time and self.running:
                elapsed = int(time.time() - self.start_time)
                self.time_var.set(f"运行: {elapsed}秒")
        except Exception:
            pass


class RegionSelector:
    """区域选择器 - 让用户在全屏窗口上拖拽选择区域"""

    def __init__(self, parent, callback):
        """
        初始化区域选择器

        Args:
            parent: 父窗口
            callback: 选择完成后的回调函数，参数为 {"top": y, "left": x, "width": w, "height": h}
        """
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.rect_id = None

        # 创建全屏窗口
        self.top = tk.Toplevel(parent)
        self.top.title("选择截图区域")
        self.top.attributes('-fullscreen', True)
        self.top.attributes('-alpha', 0.3)  # 半透明
        self.top.configure(bg='black')

        # 显示提示
        self.label = tk.Label(
            self.top,
            text="拖拽鼠标选择游戏截图区域 | Drag to select game capture region\n按ESC取消 | Press ESC to cancel",
            fg='white',
            bg='black',
            font=('Arial', 14)
        )
        self.label.place(relx=0.5, rely=0.05, anchor=tk.CENTER)

        # 创建画布
        self.canvas = tk.Canvas(self.top, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 绑定事件
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.top.bind('<Escape>', lambda e: self.cancel())

        # 获取屏幕尺寸
        self.screen_width = self.top.winfo_screenwidth()
        self.screen_height = self.top.winfo_screenheight()

    def on_mouse_down(self, event):
        """鼠标按下"""
        self.start_x = event.x
        self.start_y = event.y

        # 创建矩形
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2
        )

    def on_mouse_drag(self, event):
        """鼠标拖拽"""
        if self.rect_id:
            self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        """鼠标释放"""
        if self.rect_id:
            # 计算区域
            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)

            width = x2 - x1
            height = y2 - y1

            # 最小尺寸检查
            if width < 50 or height < 50:
                self.canvas.delete(self.rect_id)
                self.rect_id = None
                return

            # 保存区域
            region = {
                "top": y1,
                "left": x1,
                "width": width,
                "height": height
            }

            # 关闭窗口
            self.top.destroy()

            # 调用回调
            if self.callback:
                self.callback(region)

    def cancel(self):
        """取消选择"""
        self.top.destroy()
        print("Region selection cancelled")


def main():
    """主函数"""
    root = tk.Tk()
    MotaGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
