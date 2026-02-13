"""
控制执行模块
负责向游戏发送键盘输入
"""
import pyautogui
import time
from typing import Optional, Set
from enum import Enum
import win32gui
import win32con

from planner import Action


class Controller:
    """游戏控制器"""

    # 默认设置
    DEFAULT_KEY_DELAY = 0.05  # 按键间隔（秒）
    DEFAULT_ACTION_DELAY = 0.2  # 动作完成后等待时间（秒）

    def __init__(self, key_delay: float = None, action_delay: float = None, window_title: str = "魔塔"):
        """
        初始化控制器

        Args:
            key_delay: 按键间隔时间（秒）
            action_delay: 动作间隔时间（秒）
            window_title: 游戏窗口标题
        """
        # 禁用pyautogui的安全检查（需要快速输入时）
        pyautogui.FAILSAFE = False

        self.key_delay = key_delay if key_delay is not None else self.DEFAULT_KEY_DELAY
        self.action_delay = action_delay if action_delay is not None else self.DEFAULT_ACTION_DELAY
        self.window_title = window_title

        # 按键映射
        self.key_map = {
            Action.UP: 'up',
            Action.DOWN: 'down',
            Action.LEFT: 'left',
            Action.RIGHT: 'right',
            Action.WAIT: 'space',
            Action.SHOP: 'space',
        }

        # 统计信息
        self.total_actions = 0
        self.action_history: list = []

    def activate_window(self) -> bool:
        """
        激活游戏窗口（使其获得焦点）

        Returns:
            是否成功激活
        """
        try:
            # 查找游戏窗口
            hwnd = win32gui.FindWindow(None, self.window_title)

            if not hwnd:
                # 尝试模糊匹配
                def window_callback(hwnd, windows):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if self.window_title in title:
                            windows.append(hwnd)
                    return True

                windows = []
                win32gui.EnumWindows(window_callback, windows)

                if windows:
                    hwnd = windows[0]
                else:
                    print(f"警告: 未找到窗口 '{self.window_title}'")
                    return False

            # 激活窗口
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)

            # 等待窗口激活
            time.sleep(0.1)

            return True

        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False

    def press_key(self, key: str, duration: float = 0.05):
        """
        按下并释放一个键

        Args:
            key: 按键名称
            duration: 按住持续时间
        """
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)
        time.sleep(self.key_delay)

    def execute(self, action: Action, repeats: int = 1, activate: bool = True) -> bool:
        """
        执行一个动作

        Args:
            action: 要执行的动作
            repeats: 重复次数
            activate: 是否激活游戏窗口

        Returns:
            是否执行成功
        """
        try:
            key = self.key_map.get(action)
            if not key:
                print(f"未知动作: {action}")
                return False

            # 注意：网页游戏需要手动点击网页聚焦，不要自动激活窗口
            # if activate and hasattr(self, 'window_title'):
            #     self.activate_window()

            for _ in range(repeats):
                self.press_key(key)

            self.total_actions += 1
            self.action_history.append({
                'action': action,
                'time': time.time()
            })

            # 动作完成后等待
            time.sleep(self.action_delay)

            return True

        except Exception as e:
            print(f"执行动作失败: {e}")
            return False

    def move_to(self, target_x: int, target_y: int,
                current_x: int, current_y: int) -> bool:
        """
        自动移动到目标位置（单步）

        Args:
            target_x: 目标X坐标
            target_y: 目标Y坐标
            current_x: 当前X坐标
            current_y: 当前Y坐标

        Returns:
            是否移动成功
        """
        dx, dy = target_x - current_x, target_y - current_y

        if dx == 0 and dy == 0:
            return True

        # 确定移动方向（每次只移动一格）
        if abs(dx) > abs(dy):
            action = Action.RIGHT if dx > 0 else Action.LEFT
        else:
            action = Action.DOWN if dy > 0 else Action.UP

        return self.execute(action)

    def move_path(self, path: list[tuple[int, int]],
                  current_x: int, current_y: int) -> bool:
        """
        沿着路径移动

        Args:
            path: 路径点列表 [(x, y), ...]
            current_x: 当前X坐标
            current_y: 当前Y坐标

        Returns:
            是否移动成功
        """
        for pos in path:
            if not self.move_to(pos[0], pos[1], current_x, current_y):
                return False
            current_x, current_y = pos

        return True

    def wait(self, duration: float = 1.0):
        """
        等待指定时间

        Args:
            duration: 等待时长（秒）
        """
        time.sleep(duration)

    def press_confirm(self):
        """按下确认键（空格或回车）"""
        self.press_key('space')

    def press_cancel(self):
        """按下取消键（ESC）"""
        self.press_key('esc')

    def open_shop(self):
        """打开商店"""
        self.press_confirm()
        time.sleep(0.5)

    def close_dialog(self):
        """关闭对话框"""
        self.press_confirm()
        time.sleep(0.3)

    def buy_item(self, item_index: int):
        """
        购买商店物品

        Args:
            item_index: 物品索引（0-3）
        """
        # 按方向键选择物品
        if item_index == 0:
            self.press_key('up')
        elif item_index == 1:
            self.press_key('down')
        elif item_index == 2:
            self.press_key('left')
        elif item_index == 3:
            self.press_key('right')

        # 确认购买
        self.press_confirm()
        time.sleep(0.2)
        self.press_confirm()

    def get_action_count(self) -> int:
        """获取已执行的动作总数"""
        return self.total_actions

    def get_actions_per_second(self) -> float:
        """获取每秒动作数"""
        if not self.action_history:
            return 0.0

        now = time.time()
        # 统计最近10秒的动作数
        recent = [a for a in self.action_history if now - a['time'] < 10]
        return len(recent) / 10.0

    def reset_stats(self):
        """重置统计信息"""
        self.total_actions = 0
        self.action_history = []


class SmartController(Controller):
    """智能控制器：具有错误检测和恢复功能"""

    def __init__(self, key_delay: float = None, action_delay: float = None, window_title: str = "魔塔"):
        super().__init__(key_delay, action_delay, window_title)
        self.retry_count = 0
        self.max_retries = 3

    def execute_with_retry(self, action: Action,
                          check_func: Optional[callable] = None) -> bool:
        """
        执行动作，支持重试

        Args:
            action: 要执行的动作
            check_func: 检查函数，返回True表示动作生效

        Returns:
            是否执行成功
        """
        for attempt in range(self.max_retries):
            self.execute(action)

            # 如果有检查函数，等待并验证
            if check_func:
                time.sleep(0.1)
                if check_func():
                    self.retry_count = 0
                    return True
            else:
                return True

            self.retry_count += 1
            print(f"动作未生效，重试 {attempt + 1}/{self.max_retries}")

        return False

    def execute_sequence(self, actions: list[Action],
                        wait_between: float = 0.1) -> bool:
        """
        执行动作序列

        Args:
            actions: 动作列表
            wait_between: 动作之间的等待时间

        Returns:
            是否全部执行成功
        """
        for action in actions:
            if not self.execute(action):
                return False
            time.sleep(wait_between)

        return True


class ReplayRecorder:
    """操作录制器"""

    def __init__(self):
        self.recording: list[dict] = []
        self.start_time = None
        self.is_recording = False

    def start(self):
        """开始录制"""
        self.recording = []
        self.start_time = time.time()
        self.is_recording = True

    def record(self, action: Action):
        """
        录制一个动作

        Args:
            action: 动作
        """
        if not self.is_recording:
            return

        timestamp = time.time() - self.start_time
        self.recording.append({
            'timestamp': timestamp,
            'action': action
        })

    def stop(self):
        """停止录制"""
        self.is_recording = False

    def save(self, filepath: str):
        """
        保存录制到文件

        Args:
            filepath: 文件路径
        """
        import json

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'start_time': self.start_time,
                'actions': self.recording
            }, f, indent=2)

    def load(self, filepath: str):
        """
        从文件加载录制

        Args:
            filepath: 文件路径
        """
        import json

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.start_time = data['start_time']
            self.recording = data['actions']


class ReplayPlayer:
    """操作回放器"""

    def __init__(self, controller: Controller):
        self.controller = controller
        self.recording: list[dict] = []
        self.start_time = None

    def load(self, filepath: str):
        """加载录制文件"""
        recorder = ReplayRecorder()
        recorder.load(filepath)
        self.recording = recorder.recording

    def play(self, speed: float = 1.0) -> bool:
        """
        回放录制

        Args:
            speed: 播放速度倍数

        Returns:
            是否播放成功
        """
        if not self.recording:
            print("没有可回放的录制")
            return False

        self.start_time = time.time()
        last_timestamp = 0

        for record in self.recording:
            # 计算等待时间
            delay = (record['timestamp'] - last_timestamp) / speed
            if delay > 0:
                time.sleep(delay)

            # 执行动作
            action = Action(record['action'])
            self.controller.execute(action)

            last_timestamp = record['timestamp']

        return True


if __name__ == "__main__":
    # 测试代码
    print("游戏控制器测试")

    controller = Controller()
    print(f"按键延迟: {controller.key_delay}s")
    print(f"动作延迟: {controller.action_delay}s")

    # 测试按键映射
    print("\n按键映射:")
    for action, key in controller.key_map.items():
        print(f"  {action.value} -> {key}")
