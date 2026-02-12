"""
资源管理与决策模块
魔塔是资源分配游戏，核心在于合理分配有限资源（血量、钥匙、金币）
"""
import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import heapq

from state import GameState, PlayerState, FloorState
from detector import Monster, Door, Key


class ResourceType(Enum):
    """资源类型"""
    HP = "hp"              # 生命值
    ATTACK = "attack"      # 攻击力
    DEFENSE = "defense"    # 防御力
    GOLD = "gold"          # 金币
    YELLOW_KEY = "yellow_key"
    BLUE_KEY = "blue_key"
    RED_KEY = "red_key"


@dataclass
class ResourceCost:
    """资源消耗"""
    hp_cost: int = 0
    yellow_key_cost: int = 0
    blue_key_cost: int = 0
    red_key_cost: int = 0
    gold_cost: int = 0

    def __add__(self, other):
        return ResourceCost(
            hp_cost=self.hp_cost + other.hp_cost,
            yellow_key_cost=self.yellow_key_cost + other.yellow_key_cost,
            blue_key_cost=self.blue_key_cost + other.blue_key_cost,
            red_key_cost=self.red_key_cost + other.red_key_cost,
            gold_cost=self.gold_cost + other.gold_cost
        )


@dataclass
class ResourceGain:
    """资源获取"""
    hp_gain: int = 0
    attack_gain: int = 0
    defense_gain: int = 0
    gold_gain: int = 0
    yellow_key_gain: int = 0
    blue_key_gain: int = 0
    red_key_gain: int = 0

    def __add__(self, other):
        return ResourceGain(
            hp_gain=self.hp_gain + other.hp_gain,
            attack_gain=self.attack_gain + other.attack_gain,
            defense_gain=self.defense_gain + other.defense_gain,
            gold_gain=self.gold_gain + other.gold_gain,
            yellow_key_gain=self.yellow_key_gain + other.yellow_key_gain,
            blue_key_gain=self.blue_key_gain + other.blue_key_gain,
            red_key_gain=self.red_key_gain + other.red_key_gain
        )


@dataclass
class Action:
    """行动"""
    type: str  # 'move', 'fight', 'open_door', 'take_key', 'shop', 'stairs'
    target_floor: int
    target_x: int
    target_y: int
    cost: ResourceCost
    gain: ResourceGain
    description: str = ""
    required_keys: Set[str] = field(default_factory=set)


@dataclass
class Node:
    """搜索节点"""
    floor: int
    x: int
    y: int
    player_state: PlayerState
    cost: ResourceCost
    gain: ResourceGain
    path: List[Action]
    visited: Set[Tuple[int, int, int]] = field(default_factory=set)

    def __lt__(self, other):
        # 用于优先队列排序
        return True


class ResourceEvaluator:
    """资源价值评估器"""

    # 不同资源的权重（可以根据游戏阶段调整）
    DEFAULT_WEIGHTS = {
        'hp': 1.0,           # 1点生命 = 1金币
        'attack': 50.0,      # 1点攻击 = 50金币
        'defense': 30.0,     # 1点防御 = 30金币
        'gold': 1.0,
        'yellow_key': 20.0,
        'blue_key': 50.0,
        'red_key': 150.0,
    }

    def __init__(self, weights: dict = None):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def evaluate_cost(self, cost: ResourceCost) -> float:
        """评估资源消耗的价值"""
        value = 0
        value += cost.hp_cost * self.weights['hp']
        value += cost.yellow_key_cost * self.weights['yellow_key']
        value += cost.blue_key_cost * self.weights['blue_key']
        value += cost.red_key_cost * self.weights['red_key']
        value += cost.gold_cost * self.weights['gold']
        return value

    def evaluate_gain(self, gain: ResourceGain) -> float:
        """评估资源获取的价值"""
        value = 0
        value += gain.hp_gain * self.weights['hp']
        value += gain.attack_gain * self.weights['attack']
        value += gain.defense_gain * self.weights['defense']
        value += gain.gold_gain * self.weights['gold']
        value += gain.yellow_key_gain * self.weights['yellow_key']
        value += gain.blue_key_gain * self.weights['blue_key']
        value += gain.red_key_gain * self.weights['red_key']
        return value

    def evaluate_action(self, action: Action, player: PlayerState) -> float:
        """
        评估一个行动的净价值

        考虑因素：
        1. 直接收益：获取的资源
        2. 直接成本：消耗的资源
        3. 战斗风险：血量越低，战斗价值越低
        4. 开启新区域：击败怪物或开门后可能到达新区域
        """
        cost_value = self.evaluate_cost(action.cost)
        gain_value = self.evaluate_gain(action.gain)

        # 战斗风险修正
        if action.type == 'fight':
            hp_ratio = player.hp / player.max_hp
            if hp_ratio < 0.3:
                # 血量低时，战斗价值大幅降低
                gain_value *= 0.5
            elif hp_ratio < 0.5:
                gain_value *= 0.7

        return gain_value - cost_value


class BattleCalculator:
    """战斗计算器"""

    @staticmethod
    def can_defeat(player: PlayerState, monster: Monster) -> bool:
        """检查是否能战胜怪物"""
        if player.atk <= monster.defense:
            return False

        player_damage = player.atk - monster.defense
        monster_damage = max(0, monster.atk - player.defense)

        hits = (monster.hp + player_damage - 1) // player_damage
        total_damage = hits * monster_damage

        return total_damage < player.hp

    @staticmethod
    def calculate_battle(player: PlayerState, monster: Monster) -> Tuple[int, int]:
        """
        计算战斗结果

        Returns:
            (受到的伤害, 需要的回合数)
            如果无法战胜，返回 (-1, -1)
        """
        if player.atk <= monster.defense:
            return -1, -1

        player_damage = player.atk - monster.defense
        monster_damage = max(0, monster.atk - player.defense)

        hits = (monster.hp + player_damage - 1) // player_damage
        total_damage = hits * monster_damage

        return total_damage, hits

    @staticmethod
    def calculate_required_stats(monster: Monster) -> Tuple[int, int, int]:
        """
        计算战胜怪物所需的最低属性

        Returns:
            (最低攻击, 最低防御, 最低生命)
        """
        # 攻击必须大于防御
        min_attack = monster.defense + 1

        # 防御可以减少伤害，但不能完全避免
        # 最优防御是让怪物只造成1点伤害
        min_defense = max(0, monster.atk - 1)

        # 生命值需要足够承受战斗
        # 假设防御为0时的 worst case
        max_damage_per_hit = monster.atk
        hits_with_min_attack = (monster.hp + 1 - 1) // 1  # 使用最低攻击
        min_hp = hits_with_min_attack * max_damage_per_hit + 1

        return min_attack, min_defense, min_hp


class ResourceManager:
    """资源管理器 - 核心决策模块"""

    def __init__(self, game_state: GameState):
        self.state = game_state
        self.evaluator = ResourceEvaluator()
        self.battle_calc = BattleCalculator()

        # 加载商店配置
        self.shop_items = self._load_shop_config()

    def _load_shop_config(self) -> Dict:
        """加载商店物品配置"""
        # 魔塔商店通常出售：
        # - 攻击力提升
        # - 防御力提升
        # - 生命值提升
        # - 钥匙
        return {
            'attack': {
                'base_price': 20,  # 基础价格
                'price_scale': 1.5,  # 价格增长倍数
            },
            'defense': {
                'base_price': 20,
                'price_scale': 1.5,
            },
            'hp': {
                'base_price': 50,
                'price_scale': 2.0,
                'hp_per_item': 800,
            },
            'yellow_key': {
                'price': 10,
            },
            'blue_key': {
                'price': 50,
            },
            'red_key': {
                'price': 100,
            },
        }

    def evaluate_global_resources(self) -> Dict:
        """
        评估全局资源

        分析：
        1. 所有可到达的怪物
        2. 所有可获取的钥匙
        3. 所有可开启的门
        4. 商店位置和物品
        """
        resources = {
            'monsters': [],  # (floor, x, y, monster, can_defeat)
            'keys': [],  # (floor, x, y, key)
            'doors': [],  # (floor, x, y, door, can_open, behind_door)
            'shop_items': [],  # (floor, item_type, price, value)
        }

        for floor_num, floor in self.state.floors.items():
            # 怪物
            for monster in floor.monsters:
                can_defeat = self.battle_calc.can_defeat(self.state.player, monster)
                resources['monsters'].append({
                    'floor': floor_num,
                    'x': monster.x,
                    'y': monster.y,
                    'monster': monster,
                    'can_defeat': can_defeat,
                })

            # 钥匙
            for key in floor.keys:
                resources['keys'].append({
                    'floor': floor_num,
                    'x': key.x,
                    'y': key.y,
                    'key': key,
                })

            # 门
            for door in floor.doors:
                can_open = self.state.player.can_afford_door(door)
                resources['doors'].append({
                    'floor': floor_num,
                    'x': door.x,
                    'y': door.y,
                    'door': door,
                    'can_open': can_open,
                    'behind_door': self._check_behind_door(floor_num, door.x, door.y),
                })

        return resources

    def _check_behind_door(self, floor_num: int, door_x: int, door_y: int) -> List:
        """检查门后面有什么"""
        # 简化处理：检查门周围的格子
        floor = self.state.get_floor(floor_num)
        results = []

        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = door_x + dx, door_y + dy
            if 0 <= nx < floor.width and 0 <= ny < floor.height:
                cell_type = floor.get_cell_type(nx, ny)
                if cell_type != 0:  # 不是空地
                    results.append({'x': nx, 'y': ny, 'type': cell_type})

        return results

    def plan_key_usage(self) -> List[Action]:
        """
        规划钥匙使用策略

        原则：
        1. 黄门通常比蓝门优先
        2. 评估开门后的收益
        3. 考虑钥匙的稀缺性
        """
        actions = []
        resources = self.evaluate_global_resources()

        # 按优先级排序门
        door_priority = []

        for door_info in resources['doors']:
            if not door_info['can_open']:
                continue

            door = door_info['door']
            behind = door_info['behind_door']

            # 计算开门价值
            value = 0

            # 检查门后面有什么
            for item in behind:
                # 如果后面有怪物，计算战斗价值
                if item['type'] == 3:  # 怪物
                    monster = next(
                        (m for m in self.state.get_floor(door_info['floor']).monsters
                         if m.x == item['x'] and m.y == item['y']),
                        None
                    )
                    if monster and self.battle_calc.can_defeat(self.state.player, monster):
                        value += monster.gold

                # 如果后面有钥匙
                elif item['type'] == 4:  # 钥匙
                    if door.color == 'yellow':
                        value += 30  # 黄门后通常是蓝钥匙或红钥匙
                    elif door.color == 'blue':
                        value += 100  # 蓝门后通常是红钥匙或重要道具

            # 考虑钥匙稀缺性
            key_count = 0
            if door.color == 'yellow':
                key_count = self.state.player.yellow_keys
                value *= 1.0
            elif door.color == 'blue':
                key_count = self.state.player.blue_keys
                value *= 2.0  # 蓝钥匙更稀有，优先开蓝门
            elif door.color == 'red':
                key_count = self.state.player.red_keys
                value *= 5.0  # 红钥匙最稀有

            if key_count > 0 and value > 0:
                heapq.heappush(door_priority, (-value, door_info))

        # 返回优先级最高的开门动作
        while door_priority:
            neg_value, door_info = heapq.heappop(door_priority)
            door = door_info['door']

            cost = ResourceCost()
            if door.color == 'yellow':
                cost.yellow_key_cost = 1
            elif door.color == 'blue':
                cost.blue_key_cost = 1
            elif door.color == 'red':
                cost.red_key_cost = 1

            actions.append(Action(
                type='open_door',
                target_floor=door_info['floor'],
                target_x=door.x,
                target_y=door.y,
                cost=cost,
                gain=ResourceGain(),  # 开门本身不直接获得资源
                description=f"开{door.color}门",
                required_keys={door.color}
            ))

        return actions

    def plan_combat(self) -> List[Action]:
        """
        规划战斗策略

        考虑：
        1. 战斗收益（金币、经验）
        2. 战斗成本（生命值）
        3. 是否开启新区域
        4. 风险评估
        """
        actions = []
        resources = self.evaluate_global_resources()

        for monster_info in resources['monsters']:
            if not monster_info['can_defeat']:
                continue

            monster = monster_info['monster']
            damage, hits = self.battle_calc.calculate_battle(self.state.player, monster)

            if damage < 0:
                continue

            cost = ResourceCost(hp_cost=damage)
            gain = ResourceGain(gold_gain=monster.gold)

            # 计算价值
            net_value = self.evaluator.evaluate_action(Action(
                type='fight',
                target_floor=monster_info['floor'],
                target_x=monster.x,
                target_y=monster.y,
                cost=cost,
                gain=gain,
                description=f"击败{monster.name}"
            ), self.state.player)

            actions.append(Action(
                type='fight',
                target_floor=monster_info['floor'],
                target_x=monster.x,
                target_y=monster.y,
                cost=cost,
                gain=gain,
                description=f"击败{monster.name}",
                value=net_value
            ))

        # 按价值排序
        actions.sort(key=lambda a: getattr(a, 'value', 0), reverse=True)
        return actions

    def should_visit_shop(self, shop_floor: int, shop_items: List[Dict]) -> Optional[Dict]:
        """
        决定是否应该访问商店及购买什么

        Args:
            shop_floor: 商店所在楼层
            shop_items: 商店物品列表

        Returns:
            购买建议或None
        """
        if not shop_items:
            return None

        best_purchase = None
        best_value = float('-inf')

        for item in shop_items:
            item_type = item.get('type')
            price = item.get('price', 0)

            if self.state.player.gold < price:
                continue

            # 计算购买价值
            if item_type == 'attack':
                # 攻击力提升的价值 = 能击败的新怪物的收益总和
                # 简化计算：假设每1点攻击能多获得X金币
                value_gain = 50  # 基础价值
            elif item_type == 'defense':
                # 防御力提升的价值 = 减少的未来战斗伤害
                value_gain = 30
            elif item_type == 'hp':
                # 生命值提升的价值
                value_gain = 40
            elif item_type in ['yellow_key', 'blue_key', 'red_key']:
                # 钥匙价值
                value_gain = {'yellow_key': 20, 'blue_key': 50, 'red_key': 100}[item_type]
            else:
                continue

            net_value = value_gain - price

            if net_value > best_value:
                best_value = net_value
                best_purchase = item

        return best_purchase

    def calculate_required_stats_for_boss(self, boss_monster: Monster) -> Tuple[int, int, int]:
        """
        计算击败Boss所需的属性

        这是一个逆向规划的起点：
        知道最终需要什么属性，可以倒推需要收集哪些资源
        """
        return self.battle_calc.calculate_required_stats(boss_monster)

    def plan_progression(self) -> List[Action]:
        """
        规划整体进度

        这是最高层次的规划，结合所有因素：
        1. 当前状态
        2. 可获取资源
        3. 长期目标
        4. 资源约束
        """
        # 评估所有可能的行动
        possible_actions = []

        # 战斗行动
        combat_actions = self.plan_combat()
        possible_actions.extend(combat_actions)

        # 开门行动
        door_actions = self.plan_key_usage()
        possible_actions.extend(door_actions)

        # 拾取钥匙
        resources = self.evaluate_global_resources()
        for key_info in resources['keys']:
            key = key_info['key']
            gain = ResourceGain()
            if key.color == 'yellow':
                gain.yellow_key_gain = 1
            elif key.color == 'blue':
                gain.blue_key_gain = 1
            elif key.color == 'red':
                gain.red_key_gain = 1

            possible_actions.append(Action(
                type='take_key',
                target_floor=key_info['floor'],
                target_x=key.x,
                target_y=key.y,
                cost=ResourceCost(),
                gain=gain,
                description=f"拾取{key.color}钥匙"
            ))

        # 评估并排序
        scored_actions = []
        for action in possible_actions:
            score = self.evaluator.evaluate_action(action, self.state.player)
            scored_actions.append((score, action))

        # 按分数排序
        scored_actions.sort(key=lambda x: x[0], reverse=True)

        return [action for score, action in scored_actions]

    def recommend_action(self) -> Optional[Action]:
        """推荐下一步行动"""
        # 获取所有可能的行动
        actions = self.plan_progression()

        if not actions:
            return None

        # 检查血量是否过低
        if self.state.player.hp < self.state.player.max_hp * 0.3:
            # 血量低，优先找商店或血瓶
            # TODO: 实现寻找商店的逻辑
            pass

        # 返回价值最高的行动
        return actions[0]


class ForwardPlanner:
    """前向规划器 - 使用搜索算法找到最优行动序列"""

    def __init__(self, game_state: GameState, max_depth: int = 10):
        self.state = game_state
        self.max_depth = max_depth
        self.resource_manager = ResourceManager(game_state)
        self.evaluator = ResourceEvaluator()

    def search_best_action_sequence(self) -> List[Action]:
        """
        搜索最优行动序列

        使用带资源约束的搜索
        """
        initial_node = Node(
            floor=self.state.current_floor,
            x=self.state.player.x,
            y=self.state.player.y,
            player_state=self.state.player.copy(),
            cost=ResourceCost(),
            gain=ResourceGain(),
            path=[],
            visited={(self.state.current_floor, self.state.player.x, self.state.player.y)}
        )

        best_sequence = []
        best_value = float('-inf')

        # 使用优先队列搜索
        queue = [(0, initial_node)]
        visited_states = set()

        iterations = 0
        max_iterations = 1000  # 防止搜索过久

        while queue and iterations < max_iterations:
            iterations += 1
            neg_value, node = heapq.heappop(queue)

            # 生成可能的下一步行动
            actions = self.resource_manager.plan_progression()

            for action in actions[:5]:  # 只考虑前5个最佳行动
                # 检查是否可以执行
                if not self._can_execute_action(node, action):
                    continue

                # 创建新节点
                new_player = node.player_state.copy()
                self._apply_action(new_player, action)

                new_cost = node.cost + action.cost
                new_gain = node.gain + action.gain
                new_path = node.path + [action]

                # 计算价值
                gain_value = self.evaluator.evaluate_gain(new_gain)
                cost_value = self.evaluator.evaluate_cost(new_cost)
                total_value = gain_value - cost_value

                if total_value > best_value:
                    best_value = total_value
                    best_sequence = new_path

                # 继续搜索
                if len(new_path) < self.max_depth:
                    new_node = Node(
                        floor=action.target_floor,
                        x=action.target_x,
                        y=action.target_y,
                        player_state=new_player,
                        cost=new_cost,
                        gain=new_gain,
                        path=new_path,
                        visited=node.visited | {(action.target_floor, action.target_x, action.target_y)}
                    )
                    heapq.heappush(queue, (-total_value, new_node))

        return best_sequence

    def _can_execute_action(self, node: Node, action: Action) -> bool:
        """检查是否可以执行行动"""
        player = node.player_state

        # 检查钥匙
        if 'yellow' in action.required_keys and player.yellow_keys < action.cost.yellow_key_cost:
            return False
        if 'blue' in action.required_keys and player.blue_keys < action.cost.blue_key_cost:
            return False
        if 'red' in action.required_keys and player.red_keys < action.cost.red_key_cost:
            return False

        # 检查血量
        if player.hp <= action.cost.hp_cost:
            return False

        # 检查是否访问过
        if (action.target_floor, action.target_x, action.target_y) in node.visited:
            return False

        return True

    def _apply_action(self, player: PlayerState, action: Action):
        """应用行动到玩家状态"""
        player.hp -= action.cost.hp_cost
        player.yellow_keys -= action.cost.yellow_key_cost
        player.blue_keys -= action.cost.blue_key_cost
        player.red_keys -= action.cost.red_key_cost
        player.gold -= action.cost.gold_cost

        player.hp += action.gain.hp_gain
        player.atk += action.gain.attack_gain
        player.defense += action.gain.defense_gain
        player.gold += action.gain.gold_gain
        player.yellow_keys += action.gain.yellow_key_gain
        player.blue_keys += action.gain.blue_key_gain
        player.red_keys += action.gain.red_key_gain


if __name__ == "__main__":
    # 测试
    from state import GameState

    state = GameState()
    manager = ResourceManager(state)

    # 测试战斗计算
    from detector import Monster

    test_monster = Monster(x=5, y=5, name="test", atk=50, defense=10, hp=100, gold=50, exp=10)
    state.player.atk = 20
    state.player.defense = 5
    state.player.hp = 500

    print(f"能否战胜: {manager.battle_calc.can_defeat(state.player, test_monster)}")
    damage, hits = manager.battle_calc.calculate_battle(state.player, test_monster)
    print(f"战斗结果: 受到{damage}伤害, 需要{hits}回合")

    # 测试行动推荐
    action = manager.recommend_action()
    if action:
        print(f"推荐行动: {action.description}")
    else:
        print("无推荐行动")
