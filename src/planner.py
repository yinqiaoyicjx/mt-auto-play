"""
路径规划和决策模块
负责计算最优路径和做出游戏决策
"""
import heapq
from typing import List, Tuple, Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum

from state import GameState, PlayerState, FloorState
from detector import Monster, Door, Key, Point


class Action(Enum):
    """动作类型"""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    WAIT = "WAIT"
    SHOP = "SHOP"


@dataclass
class Plan:
    """执行计划"""
    action: Action
    target_x: int
    target_y: int
    expected_cost: int  # 预期消耗（生命值）
    expected_gain: int  # 预期收益（金币/道具等）
    reason: str  # 决策理由


class PathFinder:
    """路径查找器"""

    @staticmethod
    def bfs(start: Tuple[int, int], goal: Tuple[int, int],
            floor: FloorState, obstacles: bool = True) -> Optional[List[Tuple[int, int]]]:
        """
        使用BFS查找最短路径

        Args:
            start: 起始坐标 (x, y)
            goal: 目标坐标 (x, y)
            floor: 楼层状态
            obstacles: 是否考虑障碍物

        Returns:
            路径点列表 [(x, y), ...] 或 None
        """
        if start == goal:
            return []

        queue = [(start, [])]
        visited = {start}

        while queue:
            (x, y), path = queue.pop(0)

            # 四个方向
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy

                if (nx, ny) == goal:
                    return path + [(nx, ny)]

                # 检查边界
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    continue

                # 检查是否访问过
                if (nx, ny) in visited:
                    continue

                # 检查障碍物
                if obstacles:
                    cell_type = floor.get_cell_type(nx, ny)
                    if cell_type == 1:  # 墙
                        continue

                visited.add((nx, ny))
                queue.append(((nx, ny), path + [(nx, ny)]))

        return None

    @staticmethod
    def a_star(start: Tuple[int, int], goal: Tuple[int, int],
               floor: FloorState, cost_func: Optional[Callable] = None) -> Optional[List[Tuple[int, int]]]:
        """
        使用A*算法查找路径

        Args:
            start: 起始坐标
            goal: 目标坐标
            floor: 楼层状态
            cost_func: 成本函数 (x, y) -> cost

        Returns:
            路径点列表或None
        """
        if start == goal:
            return []

        def heuristic(a, b):
            """曼哈顿距离启发式"""
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def default_cost(x, y):
            cell_type = floor.get_cell_type(x, y)
            # 默认成本: 空地=1, 其他=10
            return 1 if cell_type == 0 else 10

        if cost_func is None:
            cost_func = default_cost

        open_set = [(0, start)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], int] = {start: 0}
        f_score: Dict[Tuple[int, int], int] = {start: heuristic(start, goal)}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                # 重建路径
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            x, y = current

            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                neighbor = (nx, ny)

                # 检查边界
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    continue

                # 检查是否是墙
                if floor.get_cell_type(nx, ny) == 1:
                    continue

                tentative_g_score = g_score[current] + cost_func(nx, ny)

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None

    @staticmethod
    def find_reachable_area(start: Tuple[int, int], floor: FloorState,
                           player: PlayerState) -> Set[Tuple[int, int]]:
        """
        查找从起点可达的所有区域

        Args:
            start: 起始坐标
            floor: 楼层状态
            player: 玩家状态

        Returns:
            可达位置集合
        """
        reachable = set()
        queue = [start]
        reachable.add(start)

        while queue:
            x, y = queue.pop(0)

            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy

                if (nx, ny) in reachable:
                    continue

                # 检查边界
                if not (0 <= nx < floor.width and 0 <= ny < floor.height):
                    continue

                cell_type = floor.get_cell_type(nx, ny)

                # 检查是否可通过
                if cell_type == 1:  # 墙
                    continue
                elif cell_type == 2:  # 门
                    door = next((d for d in floor.doors if d.x == nx and d.y == ny), None)
                    if door and not player.can_afford_door(door):
                        continue
                elif cell_type == 3:  # 怪物
                    monster = next((m for m in floor.monsters if m.x == nx and m.y == ny), None)
                    if monster and not player.can_defeat(monster):
                        continue

                reachable.add((nx, ny))
                queue.append((nx, ny))

        return reachable


class GamePlanner:
    """游戏决策规划器"""

    def __init__(self, game_state: GameState):
        """
        初始化规划器

        Args:
            game_state: 游戏状态
        """
        self.state = game_state
        self.path_finder = PathFinder()

    def plan_next_action(self) -> Plan:
        """
        规划下一步动作

        Returns:
            执行计划
        """
        current_floor = self.state.get_current_floor()
        player = self.state.player

        # 优先级1: 检查是否需要回血
        if player.hp < player.max_hp * 0.3:
            plan = self._plan_heal()
            if plan:
                return plan

        # 优先级2: 换楼层（提升优先级！如果当前楼层无可探索内容，立即换楼层）
        plan = self._plan_change_floor()
        if plan:
            return plan

        # 优先级3: 拾取附近的钥匙（验证是否可达）
        plan = self._plan_collect_keys()
        if plan:
            return plan

        # 优先级4: 击败可战胜的怪物
        plan = self._plan_fight_monsters()
        if plan:
            return plan

        # 优先级5: 探索未访问区域
        plan = self._plan_explore()
        if plan:
            return plan

        # 默认: 等待
        return Plan(Action.WAIT, player.x, player.y, 0, 0, "无目标")

    def _plan_heal(self) -> Optional[Plan]:
        """规划回血路径"""
        # 查找商店
        current_floor = self.state.get_current_floor()

        # 商店通常在固定位置，这里简化处理
        # 实际需要根据游戏确定商店位置

        return None

    def _plan_collect_keys(self) -> Optional[Plan]:
        """规划收集钥匙（验证钥匙是否真实存在且可达）"""
        current_floor = self.state.get_current_floor()
        player = self.state.player

        if not current_floor.keys:
            return None

        # 过滤掉不可达的钥匙（被墙或其他障碍阻挡）
        valid_keys = []
        for key in current_floor.keys:
            # 检查钥匙位置是否可达
            path = self.path_finder.bfs(
                (player.x, player.y),
                (key.x, key.y),
                current_floor,
                obstacles=True  # 考虑障碍物
            )

            if path:
                valid_keys.append((key, len(path)))

        # 如果没有可达的钥匙，清除钥匙列表（可能是旧数据）
        if not valid_keys:
            current_floor.keys = []
            return None

        # 找最近的钥匙
        valid_keys.sort(key=lambda x: x[1])
        closest_key, dist = valid_keys[0]

        # 如果距离太远（超过20步），优先考虑换楼层
        if dist > 20:
            return None

        return Plan(
            Action.WAIT,  # 动作将在执行时确定
            closest_key.x,
            closest_key.y,
            0,
            10,  # 钥匙的价值
            f"拾取{closest_key.color}钥匙"
        )

    def _plan_fight_monsters(self) -> Optional[Plan]:
        """规划战斗"""
        current_floor = self.state.get_current_floor()
        player = self.state.player

        if not current_floor.monsters:
            return None

        # 找最优战斗目标
        best_monster = None
        best_score = float('-inf')

        for monster in current_floor.monsters:
            if not player.can_defeat(monster):
                continue

            # 计算战斗价值
            _, damage_taken = player.calculate_battle(monster)
            score = monster.gold - damage_taken * 2  # 简单的价值评估

            # 考虑距离
            path = self.path_finder.bfs(
                (player.x, player.y),
                (monster.x, monster.y),
                current_floor,
                obstacles=False
            )

            if path:
                distance_cost = len(path)
                score -= distance_cost

                if score > best_score:
                    best_score = score
                    best_monster = monster

        if best_monster:
            _, damage_taken = player.calculate_battle(best_monster)
            return Plan(
                Action.WAIT,
                best_monster.x,
                best_monster.y,
                damage_taken,
                best_monster.gold,
                f"击败{best_monster.name}"
            )

        return None

    def _plan_explore(self) -> Optional[Plan]:
        """规划探索"""
        current_floor = self.state.get_current_floor()
        player = self.state.player

        # 找最近的未访问位置
        unvisited = []
        for y in range(current_floor.height):
            for x in range(current_floor.width):
                if not current_floor.is_visited(x, y) and current_floor.get_cell_type(x, y) != 1:
                    unvisited.append((x, y))

        if not unvisited:
            return None

        # 找最近的未访问位置
        closest_pos = None
        closest_dist = float('inf')

        for pos in unvisited:
            path = self.path_finder.bfs(
                (player.x, player.y),
                pos,
                current_floor,
                obstacles=False
            )

            if path and len(path) < closest_dist:
                closest_dist = len(path)
                closest_pos = pos

        if closest_pos:
            return Plan(
                Action.WAIT,
                closest_pos[0],
                closest_pos[1],
                0,
                5,  # 探索的固定价值
                "探索"
            )

        return None

    def _plan_change_floor(self) -> Optional[Plan]:
        """规划换楼层"""
        current_floor = self.state.get_current_floor()
        player = self.state.player
        stairs = current_floor.stairs

        # 优先向上
        if stairs.get('up'):
            return Plan(
                Action.UP,
                stairs['up'].x,
                stairs['up'].y,
                0,
                20,  # 上楼的价值
                "上楼探索"
            )

        # 其次向下
        if stairs.get('down'):
            return Plan(
                Action.DOWN,
                stairs['down'].x,
                stairs['down'].y,
                0,
                10,
                "下楼探索"
            )

        return None

    def get_next_step(self, plan: Plan) -> Action:
        """
        根据计划获取下一步动作

        Args:
            plan: 执行计划

        Returns:
            下一步动作
        """
        if plan.action in [Action.UP, Action.DOWN]:
            return plan.action

        # 计算路径
        current_floor = self.state.get_current_floor()
        path = self.path_finder.bfs(
            (self.state.player.x, self.state.player.y),
            (plan.target_x, plan.target_y),
            current_floor,
            obstacles=False
        )

        if not path or len(path) == 0:
            return Action.WAIT

        next_pos = path[0]
        dx = next_pos[0] - self.state.player.x
        dy = next_pos[1] - self.state.player.y

        if dy == -1:
            return Action.UP
        elif dy == 1:
            return Action.DOWN
        elif dx == -1:
            return Action.LEFT
        elif dx == 1:
            return Action.RIGHT

        return Action.WAIT

    def simulate_battle(self, player: PlayerState, monster: Monster) -> Tuple[bool, int]:
        """
        模拟战斗结果

        Args:
            player: 玩家状态
            monster: 怪物信息

        Returns:
            (是否胜利, 受到的伤害)
        """
        if player.atk <= monster.defense:
            return False, -1

        player_damage = player.atk - monster.defense
        monster_damage = max(0, monster.atk - player.defense)

        hits = (monster.hp + player_damage - 1) // player_damage
        total_damage = hits * monster_damage

        return total_damage < player.hp, total_damage


class Strategy:
    """游戏策略基类"""

    def __init__(self, game_state: GameState):
        self.state = game_state
        self.planner = GamePlanner(game_state)

    def decide(self) -> Action:
        """做出决策"""
        plan = self.planner.plan_next_action()
        return self.planner.get_next_step(plan)


class ConservativeStrategy(Strategy):
    """保守策略：优先生存"""

    def decide(self) -> Action:
        current_floor = self.state.get_current_floor()
        player = self.state.player

        # 血量低时优先回血
        if player.hp < player.max_hp * 0.5:
            # 寻找商店或楼梯
            pass

        return super().decide()


class AggressiveStrategy(Strategy):
    """激进策略：优先战斗和探索"""

    def decide(self) -> Action:
        # 提高战斗优先级
        return super().decide()


if __name__ == "__main__":
    # 测试代码
    from state import GameState

    state = GameState()
    planner = GamePlanner(state)

    # 模拟一些游戏状态
    floor = state.get_current_floor()
    floor.set_cell_type(5, 5, 4)  # 放置钥匙

    plan = planner.plan_next_action()
    print(f"计划: {plan.action}, 目标: ({plan.target_x}, {plan.target_y}), 理由: {plan.reason}")
