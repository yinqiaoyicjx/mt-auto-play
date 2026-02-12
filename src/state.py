"""
游戏状态管理模块
负责维护游戏状态、地图记忆等
"""
import numpy as np
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

from detector import PlayerInfo, Monster, Door, Key, Point


@dataclass
class PlayerState:
    """玩家状态"""
    floor: int = 1
    x: int = 0
    y: int = 0
    hp: int = 1000
    max_hp: int = 1000
    atk: int = 10
    defense: int = 10
    yellow_keys: int = 1
    blue_keys: int = 0
    red_keys: int = 0
    gold: int = 0

    def copy(self) -> 'PlayerState':
        """创建状态的深拷贝"""
        return PlayerState(
            floor=self.floor,
            x=self.x,
            y=self.y,
            hp=self.hp,
            max_hp=self.max_hp,
            atk=self.atk,
            defense=self.defense,
            yellow_keys=self.yellow_keys,
            blue_keys=self.blue_keys,
            red_keys=self.red_keys,
            gold=self.gold
        )

    def can_afford_door(self, door: Door) -> bool:
        """检查是否有钥匙开门"""
        key_counts = {
            'yellow': self.yellow_keys,
            'blue': self.blue_keys,
            'red': self.red_keys
        }
        return key_counts.get(door.color, 0) > 0

    def use_key(self, color: str):
        """使用钥匙"""
        if color == 'yellow':
            self.yellow_keys -= 1
        elif color == 'blue':
            self.blue_keys -= 1
        elif color == 'red':
            self.red_keys -= 1

    def calculate_battle(self, monster: Monster) -> Tuple[int, int]:
        """
        计算与怪物的战斗结果

        Returns:
            (造成的伤害, 受到的伤害)
            如果无法战胜，返回 (-1, -1)
        """
        if self.atk <= monster.defense:
            return -1, -1

        # 玩家每回合伤害
        player_damage_per_hit = self.atk - monster.defense
        # 怪物每回合伤害
        monster_damage_per_hit = max(0, monster.atk - self.defense)

        # 需要的回合数
        hits_needed = (monster.hp + player_damage_per_hit - 1) // player_damage_per_hit

        # 总受到的伤害
        total_damage_taken = hits_needed * monster_damage_per_hit

        return hits_needed * player_damage_per_hit, total_damage_taken

    def can_defeat(self, monster: Monster) -> bool:
        """检查是否能战胜怪物"""
        _, damage_taken = self.calculate_battle(monster)
        return 0 <= damage_taken < self.hp

    def defeat_monster(self, monster: Monster):
        """战胜怪物后更新状态"""
        _, damage_taken = self.calculate_battle(monster)
        self.hp -= damage_taken
        self.gold += monster.gold
        # 经验值在魔塔中通常不直接显示


@dataclass
class FloorState:
    """单个楼层的完整状态"""
    floor_number: int
    width: int = 13
    height: int = 11
    # 网格地图: 0=空地, 1=墙, 2=门, 3=怪物, 4=钥匙, 5=楼梯, 6=商店
    grid: np.ndarray = field(default_factory=lambda: np.zeros((11, 13), dtype=int))
    monsters: List[Monster] = field(default_factory=list)
    doors: List[Door] = field(default_factory=list)
    keys: List[Key] = field(default_factory=list)
    stairs: Dict[str, Optional[Point]] = field(default_factory=dict)
    visited: Set[Tuple[int, int]] = field(default_factory=set)
    explored: bool = False

    def add_visited(self, x: int, y: int):
        """标记访问过的位置"""
        self.visited.add((x, y))

    def is_visited(self, x: int, y: int) -> bool:
        """检查位置是否访问过"""
        return (x, y) in self.visited

    def get_cell_type(self, x: int, y: int) -> int:
        """获取指定位置的单元格类型"""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.grid[y, x]
        return -1  # 越界

    def set_cell_type(self, x: int, y: int, cell_type: int):
        """设置指定位置的单元格类型"""
        if 0 <= y < self.height and 0 <= x < self.width:
            self.grid[y, x] = cell_type

    def remove_monster(self, x: int, y: int):
        """移除指定位置的怪物"""
        self.monsters = [m for m in self.monsters if not (m.x == x and m.y == y)]
        # 如果该位置没有其他东西，标记为空地
        if self.get_cell_type(x, y) == 3:
            self.set_cell_type(x, y, 0)

    def remove_door(self, x: int, y: int):
        """移除指定位置的门"""
        self.doors = [d for d in self.doors if not (d.x == x and d.y == y)]
        if self.get_cell_type(x, y) == 2:
            self.set_cell_type(x, y, 0)

    def remove_key(self, x: int, y: int):
        """移除指定位置的钥匙"""
        self.keys = [k for k in self.keys if not (k.x == x and k.y == y)]
        if self.get_cell_type(x, y) == 4:
            self.set_cell_type(x, y, 0)


class GameState:
    """游戏全局状态"""

    def __init__(self, max_floors: int = 24):
        """
        初始化游戏状态

        Args:
            max_floors: 最大楼层数
        """
        self.max_floors = max_floors
        self.player = PlayerState()
        self.floors: Dict[int, FloorState] = {}
        self.current_floor = 1
        self.game_over = False
        self.victory = False
        self.steps = 0
        self.start_time = datetime.now()
        self.last_action = ""

        # 初始化各楼层
        for i in range(1, max_floors + 1):
            self.floors[i] = FloorState(floor_number=i)

    def get_current_floor(self) -> FloorState:
        """获取当前楼层状态"""
        return self.floors.get(self.current_floor, FloorState(self.current_floor))

    def get_floor(self, floor_num: int) -> FloorState:
        """获取指定楼层状态"""
        if floor_num not in self.floors:
            self.floors[floor_num] = FloorState(floor_num)
        return self.floors[floor_num]

    def update_player_position(self, x: int, y: int):
        """更新玩家位置"""
        old_x, old_y = self.player.x, self.player.y
        self.player.x = x
        self.player.y = y

        # 标记当前位置为已访问
        current_floor = self.get_current_floor()
        current_floor.add_visited(x, y)

        self.steps += 1

    def move_player(self, dx: int, dy: int) -> bool:
        """
        移动玩家

        Args:
            dx: X方向移动 (-1, 0, 1)
            dy: Y方向移动 (-1, 0, 1)

        Returns:
            是否移动成功
        """
        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # 检查边界
        current_floor = self.get_current_floor()
        if not (0 <= new_x < current_floor.width and 0 <= new_y < current_floor.height):
            return False

        # 检查是否可以移动到目标位置
        cell_type = current_floor.get_cell_type(new_x, new_y)

        if cell_type == 1:  # 墙
            return False
        elif cell_type == 2:  # 门
            # 检查是否有钥匙
            door = next((d for d in current_floor.doors if d.x == new_x and d.y == new_y), None)
            if door and self.player.can_afford_door(door):
                self.player.use_key(door.color)
                current_floor.remove_door(new_x, new_y)
                self.update_player_position(new_x, new_y)
                self.last_action = f"开{door.color}门"
                return True
            return False
        elif cell_type == 3:  # 怪物
            # 检查是否能战胜
            monster = next((m for m in current_floor.monsters if m.x == new_x and m.y == new_y), None)
            if monster and self.player.can_defeat(monster):
                self.player.defeat_monster(monster)
                current_floor.remove_monster(new_x, new_y)
                self.update_player_position(new_x, new_y)
                self.last_action = f"击败{monster.name}"
                return True
            return False
        elif cell_type == 4:  # 钥匙
            key = next((k for k in current_floor.keys if k.x == new_x and k.y == new_y), None)
            if key:
                if key.color == 'yellow':
                    self.player.yellow_keys += 1
                elif key.color == 'blue':
                    self.player.blue_keys += 1
                elif key.color == 'red':
                    self.player.red_keys += 1
                current_floor.remove_key(new_x, new_y)
            self.update_player_position(new_x, new_y)
            self.last_action = f"拾取{key.color}钥匙" if key else "移动"
            return True
        elif cell_type == 5:  # 楼梯
            stairs = current_floor.stairs
            if stairs.get('up') and stairs['up'].x == new_x and stairs['up'].y == new_y:
                self.change_floor(self.current_floor + 1)
                self.last_action = "上楼"
            elif stairs.get('down') and stairs['down'].x == new_x and stairs['down'].y == new_y:
                self.change_floor(self.current_floor - 1)
                self.last_action = "下楼"
            return True
        else:  # 空地
            self.update_player_position(new_x, new_y)
            self.last_action = "移动"
            return True

    def change_floor(self, new_floor: int):
        """切换楼层"""
        if 1 <= new_floor <= self.max_floors:
            self.current_floor = new_floor
            self.player.floor = new_floor
            # 切换楼层后需要重新定位玩家位置
            # 通常在楼梯位置，这里简化处理

    def update_from_detection(self, player_info: PlayerInfo, monsters: List[Monster],
                             doors: List[Door], keys: List[Key], stairs: Dict[str, Optional[Point]]):
        """
        从检测结果更新游戏状态

        Args:
            player_info: 玩家信息
            monsters: 怪物列表
            doors: 门列表
            keys: 钥匙列表
            stairs: 楼梯位置
        """
        # 更新玩家状态
        self.player.floor = player_info.floor
        self.player.hp = player_info.hp
        self.player.max_hp = player_info.max_hp
        self.player.atk = player_info.atk
        self.player.defense = player_info.defense
        self.player.yellow_keys = player_info.yellow_keys
        self.player.blue_keys = player_info.blue_keys
        self.player.red_keys = player_info.red_keys
        self.player.gold = player_info.gold
        self.player.x = player_info.x
        self.player.y = player_info.y

        # 更新当前楼层状态
        current_floor = self.get_current_floor()

        # 更新怪物
        current_floor.monsters = monsters
        for monster in monsters:
            current_floor.set_cell_type(monster.x, monster.y, 3)

        # 更新门
        current_floor.doors = doors
        for door in doors:
            current_floor.set_cell_type(door.x, door.y, 2)

        # 更新钥匙
        current_floor.keys = keys
        for key in keys:
            current_floor.set_cell_type(key.x, key.y, 4)

        # 更新楼梯
        current_floor.stairs = stairs
        if stairs.get('up'):
            current_floor.set_cell_type(stairs['up'].x, stairs['up'].y, 5)
        if stairs.get('down'):
            current_floor.set_cell_type(stairs['down'].x, stairs['down'].y, 5)

    def is_exploration_complete(self) -> bool:
        """检查是否探索完所有可到达区域"""
        for floor in self.floors.values():
            if not floor.explored:
                return False
        return True

    def get_unvisited_reachable(self) -> List[Tuple[int, int, int]]:
        """
        获取所有未访问但可到达的位置

        Returns:
            [(floor, x, y), ...]
        """
        result = []
        for floor_num, floor in self.floors.items():
            for y in range(floor.height):
                for x in range(floor.width):
                    if not floor.is_visited(x, y) and floor.get_cell_type(x, y) != 1:
                        result.append((floor_num, x, y))
        return result

    def save_state(self, filepath: str):
        """
        保存游戏状态到文件

        保存内容包括:
        - 玩家状态（位置、属性、钥匙、金币等）
        - 各楼层地图（网格、已访问位置）
        - 怪物信息（位置、属性）
        - 门、钥匙、楼梯位置
        - 游戏进度（步数、当前楼层）
        """
        state_dict = {
            'version': '1.0',
            'save_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'player': {
                'floor': self.player.floor,
                'x': self.player.x,
                'y': self.player.y,
                'hp': self.player.hp,
                'max_hp': self.player.max_hp,
                'atk': self.player.atk,
                'defense': self.player.defense,
                'yellow_keys': self.player.yellow_keys,
                'blue_keys': self.player.blue_keys,
                'red_keys': self.player.red_keys,
                'gold': self.player.gold
            },
            'current_floor': self.current_floor,
            'steps': self.steps,
            'game_over': self.game_over,
            'victory': self.victory,
            'floors': {}
        }

        for floor_num, floor in self.floors.items():
            floor_dict = {
                'floor_number': floor.floor_number,
                'width': floor.width,
                'height': floor.height,
                'grid': floor.grid.tolist(),
                'visited': list(floor.visited),
                'explored': floor.explored,
                # 保存怪物信息
                'monsters': [
                    {
                        'x': m.x, 'y': m.y,
                        'name': m.name,
                        'atk': m.atk,
                        'defense': m.defense,
                        'hp': m.hp,
                        'gold': m.gold,
                        'exp': m.exp
                    }
                    for m in floor.monsters
                ],
                # 保存门信息
                'doors': [
                    {'x': d.x, 'y': d.y, 'color': d.color}
                    for d in floor.doors
                ],
                # 保存钥匙信息
                'keys': [
                    {'x': k.x, 'y': k.y, 'color': k.color}
                    for k in floor.keys
                ],
                # 保存楼梯信息
                'stairs': {
                    'up': {'x': floor.stairs.get('up').x, 'y': floor.stairs.get('up').y} if floor.stairs.get('up') else None,
                    'down': {'x': floor.stairs.get('down').x, 'y': floor.stairs.get('down').y} if floor.stairs.get('down') else None
                }
            }
            state_dict['floors'][str(floor_num)] = floor_dict

        # 确保目录存在
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False)

    def load_state(self, filepath: str) -> bool:
        """
        从文件加载游戏状态

        Returns:
            bool: 是否加载成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)

            # 恢复玩家状态
            p = state_dict['player']
            self.player = PlayerState(
                floor=p['floor'],
                x=p['x'],
                y=p['y'],
                hp=p['hp'],
                max_hp=p['max_hp'],
                atk=p['atk'],
                defense=p['defense'],
                yellow_keys=p['yellow_keys'],
                blue_keys=p['blue_keys'],
                red_keys=p['red_keys'],
                gold=p['gold']
            )

            self.current_floor = state_dict['current_floor']
            self.steps = state_dict['steps']
            self.game_over = state_dict.get('game_over', False)
            self.victory = state_dict.get('victory', False)

            # 恢复楼层状态
            for floor_num_str, floor_data in state_dict['floors'].items():
                floor_num = int(floor_num_str)
                floor = self.floors[floor_num]

                floor.floor_number = floor_data['floor_number']
                floor.width = floor_data.get('width', 13)
                floor.height = floor_data.get('height', 11)
                floor.grid = np.array(floor_data['grid'])
                floor.visited = set(tuple(v) for v in floor_data['visited'])
                floor.explored = floor_data.get('explored', False)

                # 恢复怪物
                floor.monsters = [
                    Monster(
                        x=m['x'], y=m['y'],
                        name=m['name'],
                        atk=m['atk'],
                        defense=m['defense'],
                        hp=m['hp'],
                        gold=m['gold'],
                        exp=m['exp']
                    )
                    for m in floor_data.get('monsters', [])
                ]

                # 恢复门
                floor.doors = [
                    Door(x=d['x'], y=d['y'], color=d['color'])
                    for d in floor_data.get('doors', [])
                ]

                # 恢复钥匙
                floor.keys = [
                    Key(x=k['x'], y=k['y'], color=k['color'])
                    for k in floor_data.get('keys', [])
                ]

                # 恢复楼梯
                stairs_data = floor_data.get('stairs', {})
                floor.stairs = {}
                if stairs_data.get('up'):
                    floor.stairs['up'] = Point(x=stairs_data['up']['x'], y=stairs_data['up']['y'])
                if stairs_data.get('down'):
                    floor.stairs['down'] = Point(x=stairs_data['down']['x'], y=stairs_data['down']['y'])

            return True

        except FileNotFoundError:
            print(f"Save file not found: {filepath}")
            return False
        except json.JSONDecodeError as e:
            print(f"Invalid save file format: {e}")
            return False
        except Exception as e:
            print(f"Error loading save: {e}")
            return False

    def get_save_info(self, filepath: str) -> dict:
        """
        获取存档文件的信息（不加载完整状态）

        Returns:
            dict: 存档信息，如果文件不存在返回None
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)

            p = state_dict['player']
            return {
                'save_time': state_dict.get('save_time', 'Unknown'),
                'floor': p['floor'],
                'hp': f"{p['hp']}/{p['max_hp']}",
                'atk': p['atk'],
                'defense': p['defense'],
                'gold': p['gold'],
                'keys': f"Y{p['yellow_keys']} B{p['blue_keys']} R{p['red_keys']}",
                'steps': state_dict.get('steps', 0)
            }
        except:
            return None

    def __str__(self) -> str:
        """返回状态摘要"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return (f"楼层: {self.current_floor}/{self.max_floors} | "
                f"HP: {self.player.hp}/{self.player.max_hp} | "
                f"攻: {self.player.atk} 防: {self.player.defense} | "
                f"钥匙: Y{self.player.yellow_keys} B{self.player.blue_keys} R{self.player.red_keys} | "
                f"金币: {self.player.gold} | "
                f"步数: {self.steps} | "
                f"用时: {elapsed:.1f}s")


if __name__ == "__main__":
    # 测试代码
    state = GameState(max_floors=24)
    print(state)
    print(f"\n可到达位置: {len(state.get_unvisited_reachable())}")
