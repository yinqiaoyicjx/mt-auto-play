"""
游戏基础数据库模块
保存和加载游戏的静态数据（地图、怪物、物品位置等）
支持探索后保存，下次直接使用
"""
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

from detector import Monster, Door, Key, Point


@dataclass
class FloorData:
    """单个楼层的完整数据"""
    floor_number: int
    width: int = 13
    height: int = 11
    # 网格地图: 0=空地, 1=墙, 2=门, 3=怪物, 4=钥匙, 5=楼梯, 6=商店, 7=物品(血瓶/攻击/防御)
    grid: List[List[int]] = None
    monsters: List[Dict] = None
    doors: List[Dict] = None
    keys: List[Dict] = None
    stairs: Dict[str, Dict] = None
    items: List[Dict] = None  # 地上的物品：血瓶、攻击、防御等

    def __post_init__(self):
        if self.grid is None:
            self.grid = [[0] * self.width for _ in range(self.height)]
        if self.monsters is None:
            self.monsters = []
        if self.doors is None:
            self.doors = []
        if self.keys is None:
            self.keys = []
        if self.stairs is None:
            self.stairs = {}
        if self.items is None:
            self.items = []

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'floor_number': self.floor_number,
            'width': self.width,
            'height': self.height,
            'grid': self.grid,
            'monsters': self.monsters,
            'doors': self.doors,
            'keys': self.keys,
            'stairs': self.stairs,
            'items': self.items
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FloorData':
        """从字典创建"""
        return cls(
            floor_number=data['floor_number'],
            width=data['width'],
            height=data['height'],
            grid=data['grid'],
            monsters=data['monsters'],
            doors=data['doors'],
            keys=data['keys'],
            stairs=data['stairs'],
            items=data.get('items', [])
        )


class GameDatabase:
    """游戏基础数据库"""

    def __init__(self, db_path: str = "data/game_database.json"):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.floors: Dict[int, FloorData] = {}
        self.metadata = {
            'version': '1.0',
            'created': None,
            'last_updated': None,
            'total_floors': 0,
            'explored_floors': []
        }

    def is_empty(self) -> bool:
        """检查数据库是否为空"""
        return len(self.floors) == 0

    def has_floor(self, floor_num: int) -> bool:
        """检查是否已探索某楼层"""
        return floor_num in self.floors

    def get_floor(self, floor_num: int) -> Optional[FloorData]:
        """获取楼层数据"""
        return self.floors.get(floor_num)

    def update_floor_from_detection(self, floor_num: int, width: int, height: int,
                                   monsters: List[Monster], doors: List[Door],
                                   keys: List[Key], stairs: Dict[str, Optional[Point]],
                                   grid: np.ndarray = None):
        """
        从检测结果更新楼层数据

        Args:
            floor_num: 楼层号
            width: 楼层宽度
            height: 楼层高度
            monsters: 怪物列表
            doors: 门列表
            keys: 钥匙列表
            stairs: 楼梯位置
            grid: 网格数据（可选）
        """
        # 如果楼层不存在，创建新的
        if floor_num not in self.floors:
            self.floors[floor_num] = FloorData(
                floor_number=floor_num,
                width=width,
                height=height
            )
            if floor_num not in self.metadata['explored_floors']:
                self.metadata['explored_floors'].append(floor_num)

        floor = self.floors[floor_num]

        # 转换网格数据
        if grid is not None:
            floor.grid = grid.tolist()

        # 更新怪物数据（合并，不重复）
        existing_monsters = {(m['x'], m['y']) for m in floor.monsters}
        for monster in monsters:
            key = (monster.x, monster.y)
            if key not in existing_monsters:
                floor.monsters.append({
                    'x': monster.x,
                    'y': monster.y,
                    'name': monster.name,
                    'atk': monster.atk,
                    'defense': monster.defense,
                    'hp': monster.hp,
                    'gold': monster.gold,
                    'exp': monster.exp
                })
                existing_monsters.add(key)

        # 更新门数据
        existing_doors = {(d['x'], d['y']) for d in floor.doors}
        for door in doors:
            key = (door.x, door.y)
            if key not in existing_doors:
                floor.doors.append({
                    'x': door.x,
                    'y': door.y,
                    'color': door.color
                })
                existing_doors.add(key)

        # 更新钥匙数据
        existing_keys = {(k['x'], k['y']) for k in floor.keys}
        for key in keys:
            key_pos = (key.x, key.y)
            if key_pos not in existing_keys:
                floor.keys.append({
                    'x': key.x,
                    'y': key.y,
                    'color': key.color
                })
                existing_keys.add(key_pos)

        # 更新楼梯数据
        if stairs.get('up'):
            floor.stairs['up'] = {'x': stairs['up'].x, 'y': stairs['up'].y}
        if stairs.get('down'):
            floor.stairs['down'] = {'x': stairs['down'].x, 'y': stairs['down'].y}

        # 更新元数据
        self.metadata['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.metadata['total_floors'] = len(self.floors)
        if self.metadata['created'] is None:
            self.metadata['created'] = self.metadata['last_updated']

    def mark_item_collected(self, floor_num: int, x: int, y: int):
        """标记某位置的物品已被收集"""
        if floor_num in self.floors:
            floor = self.floors[floor_num]
            # 从物品列表中移除
            floor.items = [item for item in floor.items if not (item['x'] == x and item['y'] == y)]

            # 如果是钥匙，也从钥匙列表中移除
            floor.keys = [key for key in floor.keys if not (key['x'] == x and key['y'] == y)]

    def mark_monster_defeated(self, floor_num: int, x: int, y: int):
        """标记某位置的怪物已被击败"""
        if floor_num in self.floors:
            floor = self.floors[floor_num]
            floor.monsters = [m for m in floor.monsters if not (m['x'] == x and m['y'] == y)]

    def mark_door_opened(self, floor_num: int, x: int, y: int):
        """标记某位置的门已被打开"""
        if floor_num in self.floors:
            floor = self.floors[floor_num]
            floor.doors = [d for d in floor.doors if not (d['x'] == x and d['y'] == y)]

    def get_monster_at(self, floor_num: int, x: int, y: int) -> Optional[Dict]:
        """获取指定位置的怪物信息"""
        if floor_num in self.floors:
            for monster in self.floors[floor_num].monsters:
                if monster['x'] == x and monster['y'] == y:
                    return monster
        return None

    def get_door_at(self, floor_num: int, x: int, y: int) -> Optional[Dict]:
        """获取指定位置的门信息"""
        if floor_num in self.floors:
            for door in self.floors[floor_num].doors:
                if door['x'] == x and door['y'] == y:
                    return door
        return None

    def get_key_at(self, floor_num: int, x: int, y: int) -> Optional[Dict]:
        """获取指定位置的钥匙信息"""
        if floor_num in self.floors:
            for key in self.floors[floor_num].keys:
                if key['x'] == x and key['y'] == y:
                    return key
        return None

    def get_cell_type(self, floor_num: int, x: int, y: int) -> int:
        """获取指定位置的单元格类型"""
        if floor_num in self.floors:
            floor = self.floors[floor_num]
            if 0 <= y < floor.height and 0 <= x < floor.width:
                return floor.grid[y][x]
        return -1  # 未知

    def save(self):
        """保存数据库到文件"""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)

        data = {
            'metadata': self.metadata,
            'floors': {
                str(floor_num): floor_data.to_dict()
                for floor_num, floor_data in self.floors.items()
            }
        }

        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self) -> bool:
        """
        从文件加载数据库

        Returns:
            bool: 是否加载成功
        """
        if not os.path.exists(self.db_path):
            return False

        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.metadata = data.get('metadata', {})

            for floor_num_str, floor_data in data.get('floors', {}).items():
                floor_num = int(floor_num_str)
                self.floors[floor_num] = FloorData.from_dict(floor_data)

            return True
        except Exception as e:
            print(f"Failed to load database: {e}")
            return False

    def reset(self):
        """重置数据库"""
        self.floors.clear()
        self.metadata = {
            'version': '1.0',
            'created': None,
            'last_updated': None,
            'total_floors': 0,
            'explored_floors': []
        }

    def export_summary(self) -> str:
        """导出数据库摘要"""
        lines = []
        lines.append("=" * 60)
        lines.append("Game Database Summary")
        lines.append("=" * 60)
        lines.append(f"Version: {self.metadata['version']}")
        lines.append(f"Created: {self.metadata.get('created', 'Never')}")
        lines.append(f"Last Updated: {self.metadata.get('last_updated', 'Never')}")
        lines.append(f"Total Floors: {self.metadata['total_floors']}")
        lines.append(f"Explored Floors: {', '.join(map(str, sorted(self.metadata['explored_floors'])))}")
        lines.append("")

        for floor_num in sorted(self.floors.keys()):
            floor = self.floors[floor_num]
            lines.append(f"Floor {floor_num}:")
            lines.append(f"  Size: {floor.width}x{floor.height}")
            lines.append(f"  Monsters: {len(floor.monsters)}")
            lines.append(f"  Doors: {len(floor.doors)}")
            lines.append(f"  Keys: {len(floor.keys)}")
            lines.append(f"  Items: {len(floor.items)}")
            lines.append(f"  Stairs: {len(floor.stairs)}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def get_monsters_summary(self) -> Dict[str, int]:
        """获取怪物统计摘要"""
        summary = {}
        for floor in self.floors.values():
            for monster in floor.monsters:
                name = monster['name']
                summary[name] = summary.get(name, 0) + 1
        return summary


def main():
    """测试代码"""
    db = GameDatabase("test_db.json")

    # 测试保存
    print("Testing database save...")

    # 模拟第1层数据
    from detector import Monster, Door, Key, Point

    monsters = [
        Monster(5, 3, "Slime", 10, 5, 50, 10, 5),
        Monster(8, 7, "Bat", 15, 3, 30, 15, 8)
    ]

    doors = [
        Door(6, 5, "yellow"),
        Door(10, 2, "blue")
    ]

    keys = [
        Key(3, 3, "yellow"),
        Key(7, 8, "blue")
    ]

    stairs = {
        'up': Point(6, 1),
        'down': Point(6, 9)
    }

    grid = np.zeros((11, 13), dtype=int)
    grid[5][6] = 2  # 门

    db.update_floor_from_detection(1, 13, 11, monsters, doors, keys, stairs, grid)
    db.save()

    print("Database saved!")
    print(db.export_summary())

    # 测试加载
    print("\nTesting database load...")
    db2 = GameDatabase("test_db.json")
    if db2.load():
        print("Database loaded!")
        print(db2.export_summary())

    # 清理测试文件
    if os.path.exists("test_db.json"):
        os.remove("test_db.json")
        print("\nTest file cleaned up.")


if __name__ == "__main__":
    main()
