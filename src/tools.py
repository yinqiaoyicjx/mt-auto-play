"""
工具脚本
用于收集怪物模板、固定窗口大小等
"""
import cv2
import numpy as np
import json
import os
from pathlib import Path

from capture import ScreenCapture
from detector import GameElementDetector


class WindowResizer:
    """窗口大小调整器"""

    # 魔塔推荐窗口大小
    DEFAULT_SIZE = (640, 480)  # (width, height)
    ALTERNATIVE_SIZE = (800, 600)

    def __init__(self, window_title: str = "魔塔"):
        import win32gui
        import win32con

        self.window_title = window_title
        self.hwnd = None
        self._find_window()

    def _find_window(self) -> bool:
        """查找游戏窗口"""
        import win32gui

        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title in title:
                    windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        if windows:
            self.hwnd = windows[0]
            return True
        return False

    def resize(self, width: int = None, height: int = None):
        """
        调整窗口大小

        Args:
            width: 窗口宽度
            height: 窗口高度
        """
        import win32gui
        import win32con

        if not self.hwnd:
            print("未找到游戏窗口")
            return False

        if width is None:
            width = self.DEFAULT_SIZE[0]
        if height is None:
            height = self.DEFAULT_SIZE[1]

        # 获取当前窗口位置
        rect = win32gui.GetWindowRect(self.hwnd)
        x = rect[0]
        y = rect[1]

        # 设置窗口大小和位置
        win32gui.SetWindowPos(
            self.hwnd,
            win32con.HWND_TOP,
            x, y, width, height,
            win32con.SWP_SHOWWINDOW
        )

        print(f"窗口已调整为: {width}x{height}")
        return True

    def get_size(self) -> tuple:
        """获取当前窗口大小"""
        import win32gui

        if not self.hwnd:
            return None

        rect = win32gui.GetWindowRect(self.hwnd)
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        return (width, height)


class MonsterBookCollector:
    """怪物手册模板收集器

    魔塔游戏中有怪物手册功能，可以查看所有怪物的信息
    这个工具用于从怪物手册中收集怪物模板图片
    """

    def __init__(self, template_dir: str = "data/templates"):
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self.capture = ScreenCapture()
        self.monster_data = self._load_monster_data()

    def _load_monster_data(self) -> dict:
        """加载怪物数据库"""
        data_file = Path("data/monsters.json")
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def collect_from_book(self):
        """从怪物手册收集模板

        使用说明：
        1. 在游戏中打开怪物手册（通常按M键或点击手册按钮）
        2. 手册会显示所有怪物的图片和属性
        3. 运行此函数，自动截取所有怪物图片
        """
        print("=" * 50)
        print("怪物手册模板收集工具")
        print("=" * 50)
        print("\n使用说明：")
        print("1. 在游戏中打开怪物手册")
        print("2. 确保手册显示第一个怪物")
        print("3. 按回车键开始收集")
        print("4. 按ESC键结束收集")
        print("\n")

        input("按回车键开始...")

        collected = 0
        skip_count = 0

        while True:
            # 截图
            frame = self.capture.capture()

            # 尝试识别当前怪物
            monster_info = self._parse_monster_book_page(frame)

            if monster_info:
                name = monster_info.get('name', '')
                icon = monster_info.get('icon', None)

                if name and icon is not None:
                    # 保存模板
                    filename = f"{name}_{collected + 1}.png"
                    filepath = self.template_dir / filename

                    # 检查是否已存在
                    if not filepath.exists():
                        cv2.imwrite(str(filepath), icon)
                        print(f"✓ 收集: {name} -> {filename}")
                        collected += 1
                    else:
                        print(f"⊘ 跳过: {name} (已存在)")
                        skip_count += 1

            # 显示预览
            cv2.imshow("Monster Book Collector", frame)
            cv2.waitKey(100)

            # 检查按键
            key = cv2.waitKey(100)
            if key == 27:  # ESC
                break

        cv2.destroyAllWindows()
        print(f"\n收集完成！")
        print(f"  新收集: {collected} 个")
        print(f"  跳过: {skip_count} 个")

    def _parse_monster_book_page(self, frame: np.ndarray) -> dict:
        """
        解析怪物手册的一页

        怪物手册通常包含：
        - 怪物图片（左侧或中央）
        - 怪物名称
        - 属性（攻击、防御、生命、金币、经验）

        Args:
            frame: 游戏画面

        Returns:
            怪物信息字典
        """
        h, w = frame.shape[:2]

        # 怪物手册通常在中央区域
        # 假设怪物图片在特定位置（需要根据实际游戏调整）

        # 方法1: 固定位置截取
        # 假设怪物图标在 (200, 100) 位置，大小 64x64
        icon_x, icon_y = 200, 100
        icon_size = 64

        if icon_x + icon_size < w and icon_y + icon_size < h:
            icon = frame[icon_y:icon_y + icon_size, icon_x:icon_x + icon_size]

            # 尝试OCR识别名称（需要安装pytesseract）
            name = self._extract_monster_name(frame)

            return {
                'name': name,
                'icon': icon,
            }

        return {}

    def _extract_monster_name(self, frame: np.ndarray) -> str:
        """从画面中提取怪物名称"""
        # 可以使用OCR识别
        # 或者根据在手册中的位置推断

        # 简化处理：返回默认名称
        return f"monster_{np.random.randint(1000, 9999)}"

    def collect_manual(self):
        """手动收集模板

        使用说明：
        1. 在游戏中找到怪物
        2. 把鼠标移到怪物上，会显示属性
        3. 按快捷键截图
        4. 手动标注名称和属性
        """
        print("=" * 50)
        print("手动模板收集工具")
        print("=" * 50)
        print("\n操作说明：")
        print("  c - 截图当前怪物")
        print("  q - 退出")
        print("\n")

        collected = 0

        while True:
            frame = self.capture.capture()

            # 显示画面
            display_frame = frame.copy()

            # 提示文字
            cv2.putText(display_frame, "Press 'c' to capture, 'q' to quit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Manual Collector", display_frame)

            key = cv2.waitKey(100) & 0xFF

            if key == ord('q'):
                break
            elif key == ord('c'):
                # 截图并保存
                monster_name = input(f"请输入怪物名称 (#{collected + 1}): ")

                if monster_name:
                    # 裁剪怪物图标（假设在中央）
                    h, w = frame.shape[:2]
                    icon_size = 64
                    icon_x = (w - icon_size) // 2
                    icon_y = (h - icon_size) // 2

                    icon = frame[icon_y:icon_y + icon_size, icon_x:icon_x + icon_size]

                    filename = f"{monster_name}.png"
                    filepath = self.template_dir / filename
                    cv2.imwrite(str(filepath), icon)

                    print(f"✓ 保存: {filename}")

                    # 询问属性
                    print("请输入怪物属性（留空跳过）:")
                    atk = input("  攻击力: ")
                    defense = input("  防御力: ")
                    hp = input("  生命值: ")
                    gold = input("  金币: ")

                    if atk or defense or hp:
                        # 更新怪物数据库
                        data = {
                            'name': monster_name,
                            'atk': int(atk) if atk else 0,
                            'defense': int(defense) if defense else 0,
                            'hp': int(hp) if hp else 0,
                            'gold': int(gold) if gold else 0,
                            'exp': 0
                        }

                        self.monster_data[monster_name] = data

                        # 保存数据库
                        data_file = Path("data/monsters.json")
                        with open(data_file, 'w', encoding='utf-8') as f:
                            json.dump(self.monster_data, f, indent=2, ensure_ascii=False)

                        print(f"✓ 已更新怪物数据库")

                    collected += 1

        cv2.destroyAllWindows()


class GridCalibrator:
    """网格校准器

    用于确定游戏中每个格子的实际像素大小
    """

    def __init__(self, window_title: str = "魔塔"):
        self.capture = ScreenCapture(window_title)

    def calibrate(self):
        """校准网格大小

        使用说明：
        1. 在游戏中找一个明显的网格点（比如墙角）
        2. 点击两个相邻的网格点
        3. 程序自动计算网格大小
        """
        print("=" * 50)
        print("网格校准工具")
        print("=" * 50)
        print("\n使用说明：")
        print("1. 点击画面中的一个网格交点")
        print("2. 点击相邻的网格交点")
        print("3. 程序计算网格大小")
        print("\n")

        # 鼠标回调
        clicks = []

        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                clicks.append((x, y))
                print(f"点击: ({x}, {y})")

                if len(clicks) >= 2:
                    # 计算距离
                    dx = abs(clicks[1][0] - clicks[0][0])
                    dy = abs(clicks[1][1] - clicks[0][1])
                    dist = max(dx, dy)

                    print(f"\n网格大小约为: {dist} 像素")
                    print(f"  dx: {dx}, dy: {dy}")

        cv2.namedWindow("Grid Calibrator")
        cv2.setMouseCallback("Grid Calibrator", on_mouse)

        while True:
            frame = self.capture.capture()

            # 显示点击点
            display_frame = frame.copy()
            for i, (x, y) in enumerate(clicks):
                cv2.circle(display_frame, (x, y), 5, (0, 255, 0), -1)
                cv2.putText(display_frame, str(i + 1), (x + 10, y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            cv2.imshow("Grid Calibrator", display_frame)

            key = cv2.waitKey(100) & 0xFF
            if key == 27:  # ESC
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='魔塔工具集')
    parser.add_argument('--resize', '-r', action='store_true',
                        help='调整窗口大小')
    parser.add_argument('--collect-book', '-b', action='store_true',
                        help='从怪物手册收集模板')
    parser.add_argument('--collect-manual', '-m', action='store_true',
                        help='手动收集模板')
    parser.add_argument('--calibrate', '-c', action='store_true',
                        help='校准网格大小')

    args = parser.parse_args()

    if args.resize:
        resizer = WindowResizer()
        resizer.resize()

    elif args.collect_book:
        collector = MonsterBookCollector()
        collector.collect_from_book()

    elif args.collect_manual:
        collector = MonsterBookCollector()
        collector.collect_manual()

    elif args.calibrate:
        calibrator = GridCalibrator()
        calibrator.calibrate()

    else:
        print("使用 --help 查看可用选项")
