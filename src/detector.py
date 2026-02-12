"""
游戏元素识别模块
负责从截图中识别游戏元素（玩家、怪物、门、钥匙等）
"""
import cv2
import numpy as np
import json
import os
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class Point:
    """坐标点"""
    x: int
    y: int


@dataclass
class Monster:
    """怪物信息"""
    x: int
    y: int
    name: str
    atk: int
    defense: int
    hp: int
    gold: int
    exp: int
    icon: Optional[np.ndarray] = None


@dataclass
class Door:
    """门信息"""
    x: int
    y: int
    color: str  # 'yellow', 'blue', 'red'


@dataclass
class Key:
    """钥匙信息"""
    x: int
    y: int
    color: str  # 'yellow', 'blue', 'red'


@dataclass
class PlayerInfo:
    """玩家信息"""
    floor: int
    hp: int
    max_hp: int
    atk: int
    defense: int
    yellow_keys: int
    blue_keys: int
    red_keys: int
    gold: int
    x: int
    y: int


class GameElementDetector:
    """游戏元素检测器"""

    # 颜色定义 (BGR格式)
    COLORS = {
        'yellow_door_lower': np.array([20, 100, 100]),
        'yellow_door_upper': np.array([40, 255, 255]),
        'blue_door_lower': np.array([100, 50, 50]),
        'blue_door_upper': np.array([130, 255, 255]),
        'red_door_lower': np.array([0, 50, 50]),
        'red_door_upper': np.array([10, 255, 255]),
    }

    # 游戏网格设置
    GRID_SIZE = 32  # 每个格子的大小（像素）

    def __init__(self, template_dir: str = "data/templates"):
        """
        初始化检测器

        Args:
            template_dir: 模板图片目录
        """
        self.template_dir = template_dir
        self.monster_templates: Dict[str, np.ndarray] = {}
        self.monster_data: Dict[str, Dict] = {}
        self._load_templates()
        self._load_monster_data()

    def _load_templates(self):
        """加载怪物模板图片"""
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir)
            print(f"创建模板目录: {self.template_dir}")
            return

        for filename in os.listdir(self.template_dir):
            if filename.endswith('.png'):
                name = filename[:-4]
                template = cv2.imread(os.path.join(self.template_dir, filename))
                if template is not None:
                    self.monster_templates[name] = template
                    print(f"加载模板: {name}")

    def _load_monster_data(self):
        """加载怪物数据库"""
        data_file = os.path.join("data", "monsters.json")
        if os.path.exists(data_file):
            with open(data_file, 'r', encoding='utf-8') as f:
                self.monster_data = json.load(f)
            print(f"加载怪物数据: {len(self.monster_data)} 条")

    def detect_player(self, frame: np.ndarray) -> Optional[Point]:
        """
        检测玩家位置

        Args:
            frame: 游戏画面

        Returns:
            玩家坐标 (网格坐标)
        """
        # 魔塔中玩家通常是蓝色的圆形或人形
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 蓝色范围 (玩家衣服颜色)
        lower_blue = np.array([100, 80, 80])
        upper_blue = np.array([130, 255, 255])

        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # 找到最大的轮廓（玩家）
        max_contour = max(contours, key=cv2.contourArea)

        if cv2.contourArea(max_contour) < 100:
            return None

        # 获取中心点
        M = cv2.moments(max_contour)
        if M['m00'] == 0:
            return None

        cx = int(M['m10'] / M['m00'])
        cy = int(M['m01'] / M['m00'])

        # 转换为网格坐标
        grid_x = cx // self.GRID_SIZE
        grid_y = cy // self.GRID_SIZE

        # 保存检测调试信息
        self._last_player_detection = {
            'contour': max_contour,
            'center': (cx, cy),
            'grid_pos': (grid_x, grid_y),
            'bbox': cv2.boundingRect(max_contour)
        }

        return Point(grid_x, grid_y)

    def get_last_player_detection(self):
        """获取最后一次玩家检测的调试信息"""
        return getattr(self, '_last_player_detection', None)

    def detect_monsters(self, frame: np.ndarray) -> List[Monster]:
        """
        检测画面中的所有怪物

        Args:
            frame: 游戏画面

        Returns:
            怪物列表
        """
        monsters = []

        # 将画面分割成网格，逐个检测
        h, w = frame.shape[:2]
        rows = h // self.GRID_SIZE
        cols = w // self.GRID_SIZE

        for row in range(rows):
            for col in range(cols):
                # 提取当前格子
                x1 = col * self.GRID_SIZE
                y1 = row * self.GRID_SIZE
                x2 = x1 + self.GRID_SIZE
                y2 = y1 + self.GRID_SIZE

                cell = frame[y1:y2, x1:x2]

                # 检查是否是怪物
                monster = self._identify_monster(cell, col, row)
                if monster:
                    monsters.append(monster)

        return monsters

    def _identify_monster(self, cell: np.ndarray, x: int, y: int) -> Optional[Monster]:
        """
        识别单个格子中的怪物

        Args:
            cell: 格子图像
            x: 网格X坐标
            y: 网格Y坐标

        Returns:
            怪物信息或None
        """
        if cell.size == 0:
            return None

        # 方法1: 模板匹配
        for name, template in self.monster_templates.items():
            if template.shape[:2] != cell.shape[:2]:
                continue

            # 计算相似度
            result = cv2.matchTemplate(cell, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > 0.8:  # 相似度阈值
                # 从数据库获取怪物属性
                data = self.monster_data.get(name, {})
                return Monster(
                    x=x, y=y,
                    name=name,
                    atk=data.get('atk', 0),
                    defense=data.get('defense', 0),
                    hp=data.get('hp', 0),
                    gold=data.get('gold', 0),
                    exp=data.get('exp', 0),
                    icon=cell.copy()
                )

        # 方法2: 颜色特征识别（备用方案）
        # 怪物通常有特定的颜色组合
        hsv = cv2.cvtColor(cell, cv2.COLOR_BGR2HSV)

        # 检查是否是怪物区域（有特殊颜色）
        # 这里可以根据具体游戏调整

        return None

    def detect_doors(self, frame: np.ndarray) -> List[Door]:
        """
        检测画面中的所有门

        Args:
            frame: 游戏画面

        Returns:
            门列表
        """
        doors = []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 定义不同颜色门的范围
        door_colors = {
            'yellow': (np.array([20, 100, 100]), np.array([40, 255, 255])),
            'blue': (np.array([100, 50, 50]), np.array([130, 255, 255])),
            'red': (np.array([0, 50, 50]), np.array([10, 255, 255])),
        }

        h, w = frame.shape[:2]
        rows = h // self.GRID_SIZE
        cols = w // self.GRID_SIZE

        for color_name, (lower, upper) in door_colors.items():
            mask = cv2.inRange(hsv, lower, upper)

            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)

                # 门的面积应该在一定范围内
                if 200 < area < 800:
                    # 获取边界框
                    x, y, w_box, h_box = cv2.boundingRect(contour)

                    # 计算中心点
                    cx = x + w_box // 2
                    cy = y + h_box // 2

                    # 转换为网格坐标
                    grid_x = cx // self.GRID_SIZE
                    grid_y = cy // self.GRID_SIZE

                    doors.append(Door(x=grid_x, y=grid_y, color=color_name))

        return doors

    def detect_keys(self, frame: np.ndarray) -> List[Key]:
        """
        检测画面中的所有钥匙

        Args:
            frame: 游戏画面

        Returns:
            钥匙列表
        """
        keys = []
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 钥匙颜色范围（与门相同）
        key_colors = {
            'yellow': (np.array([20, 100, 100]), np.array([40, 255, 255])),
            'blue': (np.array([100, 50, 50]), np.array([130, 255, 255])),
            'red': (np.array([0, 50, 50]), np.array([10, 255, 255])),
        }

        h, w = frame.shape[:2]
        rows = h // self.GRID_SIZE
        cols = w // self.GRID_SIZE

        for color_name, (lower, upper) in key_colors.items():
            mask = cv2.inRange(hsv, lower, upper)

            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)

                # 钥匙的面积较小
                if 50 < area < 300:
                    x, y, w_box, h_box = cv2.boundingRect(contour)
                    cx = x + w_box // 2
                    cy = y + h_box // 2

                    grid_x = cx // self.GRID_SIZE
                    grid_y = cy // self.GRID_SIZE

                    keys.append(Key(x=grid_x, y=grid_y, color=color_name))

        return keys

    def detect_stairs(self, frame: np.ndarray) -> Dict[str, Optional[Point]]:
        """
        检测楼梯位置

        Args:
            frame: 游戏画面

        Returns:
            {'up': Point或None, 'down': Point或None}
        """
        result = {'up': None, 'down': None}

        # 楼梯通常有特定的形状和颜色
        # 上楼楼梯：通常在上方，箭头向上
        # 下楼楼梯：通常在下方，箭头向下

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 使用边缘检测
        edges = cv2.Canny(gray, 50, 150)

        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = frame.shape[:2]
        rows = h // self.GRID_SIZE
        cols = w // self.GRID_SIZE

        for contour in contours:
            area = cv2.contourArea(contour)

            if 300 < area < 1000:
                x, y, w_box, h_box = cv2.boundingRect(contour)
                cx = x + w_box // 2
                cy = y + h_box // 2

                grid_x = cx // self.GRID_SIZE
                grid_y = cy // self.GRID_SIZE

                # 根据位置判断是上楼还是下楼
                if grid_y < rows // 3:  # 上部区域
                    result['up'] = Point(grid_x, grid_y)
                elif grid_y > rows * 2 // 3:  # 下部区域
                    result['down'] = Point(grid_x, grid_y)

        return result

    def parse_player_stats(self, frame: np.ndarray) -> Optional[PlayerInfo]:
        """
        解析玩家状态栏

        Args:
            frame: 游戏画面

        Returns:
            玩家信息
        """
        # 状态栏通常在顶部或底部
        h, w = frame.shape[:2]

        # 假设状态栏在顶部，高度约60像素
        stats_region = frame[0:60, :]

        # 使用OCR识别文字（需要安装pytesseract）
        # 或者通过固定位置解析

        # 这里简化处理，返回默认值
        # 实际使用时需要根据具体游戏界面调整

        return PlayerInfo(
            floor=1,
            hp=1000,
            max_hp=1000,
            atk=10,
            defense=10,
            yellow_keys=1,
            blue_keys=0,
            red_keys=0,
            gold=0,
            x=0,
            y=0
        )

    def parse_monster_dialog(self, frame: np.ndarray) -> Optional[Dict]:
        """
        解析战斗对话框中的怪物信息

        Args:
            frame: 游戏画面

        Returns:
            怪物属性字典
        """
        # 对话框通常在中央
        h, w = frame.shape[:2]
        dialog_region = frame[h//2-100:h//2+100, w//2-150:w//2+150]

        # 使用OCR识别
        # 或者通过模板匹配识别数字

        # 这里需要根据实际对话框格式解析
        # 返回格式: {'atk': 20, 'def': 10, 'hp': 100}

        return None

    def build_grid_map(self, frame: np.ndarray) -> np.ndarray:
        """
        将游戏画面转换为网格地图

        Args:
            frame: 游戏画面

        Returns:
            网格地图数组
            0: 空地, 1: 墙, 2: 门, 3: 怪物, 4: 钥匙, 5: 楼梯
        """
        h, w = frame.shape[:2]
        rows = h // self.GRID_SIZE
        cols = w // self.GRID_SIZE

        grid_map = np.zeros((rows, cols), dtype=int)

        # 识别各种元素并标记
        # 这里简化处理
        # 实际使用时需要调用上面的检测方法

        return grid_map


def save_template(frame: np.ndarray, name: str, x: int, y: int, size: int = 32):
    """
    保存模板图片

    Args:
        frame: 游戏画面
        name: 模板名称
        x: 网格X坐标
        y: 网格Y坐标
        size: 格子大小
    """
    x1 = x * size
    y1 = y * size
    template = frame[y1:y1+size, x1:x1+size]

    os.makedirs("data/templates", exist_ok=True)
    cv2.imwrite(f"data/templates/{name}.png", template)
    print(f"保存模板: {name}")


if __name__ == "__main__":
    # 测试代码
    print("游戏元素检测器")
    detector = GameElementDetector()
    print(f"已加载 {len(detector.monster_templates)} 个模板")
