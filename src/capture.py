"""
屏幕截图模块
负责捕获游戏窗口画面
"""
import mss
import numpy as np
import win32gui
import win32con
import win32process
import threading
from typing import Optional, Dict


class ScreenCapture:
    """屏幕截图类"""

    # 推荐窗口大小
    DEFAULT_SIZE = (640, 480)  # (width, height)

    def __init__(self, window_title: str = "魔塔", fixed_size: tuple = None, manual_region: dict = None):
        """
        初始化截图器

        Args:
            window_title: 游戏窗口标题
            fixed_size: 固定窗口大小 (width, height)，None表示不调整
            manual_region: 手动指定的截图区域 {"top": y, "left": x, "width": w, "height": h}
        """
        self.window_title = window_title
        self.fixed_size = fixed_size or self.DEFAULT_SIZE
        # 不保存 mss 实例，因为它不是线程安全的
        # 每次截图时会创建新的实例
        self.monitor = None
        self.window_handle = None
        self.initial_rect = None  # 记录初始窗口位置，用于检测移动
        self.manual_region = manual_region  # 手动指定的区域
        self.use_manual = manual_region is not None  # 是否使用手动区域
        self._lock = threading.Lock()  # 添加线程锁

        if self.use_manual:
            # 使用手动指定的区域
            self.monitor = manual_region
            print(f"使用手动截图区域: {manual_region}")
        else:
            # 自动查找窗口
            self._find_window()
            self._activate_window()  # 激活窗口

    def set_manual_region(self, region: dict):
        """
        设置手动截图区域

        Args:
            region: {"top": y, "left": x, "width": w, "height": h}
        """
        self.manual_region = region
        self.monitor = region
        self.use_manual = True
        print(f"截图区域已更新: {region}")

    def get_current_region(self) -> dict:
        """获取当前使用的截图区域"""
        return self.monitor

    def _find_window(self) -> bool:
        """
        查找游戏窗口

        Returns:
            是否找到窗口
        """
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title in title:
                    windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if not windows:
            print(f"警告: 未找到标题包含 '{self.window_title}' 的窗口")
            print("将使用全屏截图模式")
            # 使用全屏作为默认
            monitor = self.sct.monitors[0]  # 主显示器
            self.monitor = {
                "top": monitor["top"],
                "left": monitor["left"],
                "width": monitor["width"],
                "height": monitor["height"]
            }
            return False

        self.window_handle = windows[0]
        self._resize_window()
        self._update_monitor_rect()

        # 记录初始位置，用于检测窗口移动
        self.initial_rect = win32gui.GetWindowRect(self.window_handle)

        return True

    def _update_monitor_rect(self):
        """更新窗口监视区域"""
        if not self.window_handle:
            return

        # 获取窗口位置和大小
        rect = win32gui.GetWindowRect(self.window_handle)
        left, top, right, bottom = rect

        # 获取客户区大小（去除标题栏和边框）
        client_rect = win32gui.GetClientRect(self.window_handle)
        client_width = client_rect[2]
        client_height = client_rect[3]

        # 计算边框偏移
        border_x = (right - left - client_width) // 2
        border_y = bottom - top - client_height - border_x

        self.monitor = {
            "top": top + border_y,
            "left": left + border_x,
            "width": client_width,
            "height": client_height
        }

        print(f"游戏窗口位置: {self.monitor}")

    def _resize_window(self):
        """调整窗口大小到固定尺寸"""
        if not self.window_handle:
            return

        try:
            # 获取当前窗口位置
            rect = win32gui.GetWindowRect(self.window_handle)
            x = rect[0]
            y = rect[1]

            # 获取客户区大小（去除标题栏和边框）
            client_rect = win32gui.GetClientRect(self.window_handle)
            current_width = client_rect[2]
            current_height = client_rect[3]

            target_width, target_height = self.fixed_size

            # 如果大小不符，调整窗口
            if current_width != target_width or current_height != target_height:
                # 设置窗口大小（包含边框的尺寸）
                # 计算需要的窗口总大小
                border_x = (rect[2] - rect[0] - current_width) // 2
                border_y = rect[3] - rect[1] - current_height - border_x

                window_width = target_width + 2 * border_x
                window_height = target_height + border_y + border_x

                win32gui.SetWindowPos(
                    self.window_handle,
                    None,
                    x, y, window_width, window_height,
                    win32con.SWP_NOZORDER
                )
                print(f"窗口已调整为: {target_width}x{target_height}")
        except Exception as e:
            print(f"调整窗口大小失败: {e}")

    def _activate_window(self):
        """激活游戏窗口，确保窗口在前台"""
        if not self.window_handle:
            return

        try:
            # 检查窗口是否最小化
            if win32gui.IsIconic(self.window_handle):
                win32gui.ShowWindow(self.window_handle, win32con.SW_RESTORE)

            # 将窗口置顶
            win32gui.SetForegroundWindow(self.window_handle)
            win32gui.SetFocus(self.window_handle)

            print(f"已激活游戏窗口 (HWND: {self.window_handle})")
        except Exception as e:
            print(f"激活窗口失败: {e}")

    def check_window_moved(self) -> bool:
        """
        检查窗口是否移动了

        Returns:
            True表示窗口已移动，False表示未移动
        """
        if not self.window_handle or not self.initial_rect:
            return False

        try:
            current_rect = win32gui.GetWindowRect(self.window_handle)
            # 允许5像素的误差
            tolerance = 5
            moved = (
                abs(current_rect[0] - self.initial_rect[0]) > tolerance or
                abs(current_rect[1] - self.initial_rect[1]) > tolerance
            )

            if moved:
                print(f"警告: 检测到窗口已移动!")
                print(f"  初始位置: {self.initial_rect}")
                print(f"  当前位置: {current_rect}")
                print(f"  请勿移动游戏窗口，或点击Stop后重新启动")
                return True

            return False
        except Exception:
            return False

    def capture(self) -> np.ndarray:
        """
        截取游戏画面

        Returns:
            BGR格式的图像数组
        """
        with self._lock:  # 使用线程锁确保线程安全
            if not self.monitor:
                self._find_window()

            # 每次创建新的 mss 实例，因为 mss 不是线程安全的
            sct = mss.mss()
            screenshot = sct.grab(self.monitor)
            frame = np.array(screenshot)

            # mss返回的是RGBA，需要转换为BGR
            frame = cvt_rgba_to_bgr(frame)

            return frame

    def capture_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """
        截取指定区域

        Args:
            x: 相对于游戏窗口的X坐标
            y: 相对于游戏窗口的Y坐标
            width: 宽度
            height: 高度

        Returns:
            BGR格式的图像数组
        """
        with self._lock:  # 使用线程锁确保线程安全
            if not self.monitor:
                self._find_window()

            region = {
                "top": self.monitor["top"] + y,
                "left": self.monitor["left"] + x,
                "width": width,
                "height": height
            }

            # 每次创建新的 mss 实例
            sct = mss.mss()
            screenshot = sct.grab(region)
            frame = np.array(screenshot)
            frame = cvt_rgba_to_bgr(frame)

            return frame

    def refresh_window(self):
        """刷新窗口位置（游戏窗口移动后调用）"""
        self._find_window()


def cvt_rgba_to_bgr(frame: np.ndarray) -> np.ndarray:
    """
    将RGBA转换为BGR

    Args:
        frame: RGBA图像

    Returns:
        BGR图像
    """
    # 去掉alpha通道
    if frame.shape[2] == 4:
        frame = frame[:, :, :3]
    # RGBA到BGR
    frame = frame[:, :, ::-1]
    return frame


class FrameBuffer:
    """帧缓冲区，用于处理连续帧"""

    def __init__(self, size: int = 3):
        """
        初始化缓冲区

        Args:
            size: 缓冲区大小
        """
        self.size = size
        self.frames: list[np.ndarray] = []

    def add(self, frame: np.ndarray):
        """添加一帧"""
        self.frames.append(frame)
        if len(self.frames) > self.size:
            self.frames.pop(0)

    def get_latest(self) -> Optional[np.ndarray]:
        """获取最新一帧"""
        return self.frames[-1] if self.frames else None

    def is_stable(self, threshold: float = 0.99) -> bool:
        """
        检查画面是否稳定（用于判断动画是否结束）

        Args:
            threshold: 相似度阈值

        Returns:
            画面是否稳定
        """
        if len(self.frames) < 2:
            return False

        # 比较最后两帧
        frame1 = cvt_gray(self.frames[-2])
        frame2 = cvt_gray(self.frames[-1])

        # 计算相似度
        diff = np.abs(frame1.astype(float) - frame2.astype(float))
        similarity = 1 - (diff.mean() / 255.0)

        return similarity > threshold


def cvt_gray(frame: np.ndarray) -> np.ndarray:
    """转换为灰度图"""
    if len(frame.shape) == 3:
        return np.mean(frame, axis=2).astype(np.uint8)
    return frame
