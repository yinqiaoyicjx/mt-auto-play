"""
商店决策模块
处理商店购买决策
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from state import PlayerState, GameState


class ShopItemType(Enum):
    """商店物品类型"""
    ATTACK = "attack"        # 攻击力提升
    DEFENSE = "defense"      # 防御力提升
    HP = "hp"                # 生命值提升（血瓶）
    YELLOW_KEY = "yellow_key"
    BLUE_KEY = "blue_key"
    RED_KEY = "red_key"
    SPECIAL = "special"      # 特殊道具


@dataclass
class ShopItem:
    """商店物品"""
    type: ShopItemType
    name: str
    price: int
    value: int = 0           # 属性提升值
    description: str = ""

    # 预估值（用于决策）
    estimated_value: float = 0.0  # 购买后的预期收益


@dataclass
class ShopPurchase:
    """购买建议"""
    item: ShopItem
    reason: str
    expected_benefit: float  # 预期收益
    priority: int  # 优先级 1-10


class ShopAnalyzer:
    """商店分析器"""

    # 魔塔商店配置（不同楼层可能有不同价格）
    SHOP_CONFIG = {
        1: {  # 1层商店
            'attack': {'price': 20, 'value': 3},
            'defense': {'price': 20, 'value': 3},
            'hp': {'price': 50, 'value': 800},
        },
        4: {  # 4层商店
            'attack': {'price': 50, 'value': 3},
            'defense': {'price': 50, 'value': 3},
            'hp': {'price': 100, 'value': 800},
        },
        # 其他楼层...
    }

    def __init__(self, game_state: GameState):
        self.state = game_state

    def analyze_shop(self, floor: int, player: PlayerState,
                     available_items: List[ShopItem]) -> List[ShopPurchase]:
        """
        分析商店，给出购买建议

        Args:
            floor: 商店所在楼层
            player: 玩家状态
            available_items: 可购买的物品列表

        Returns:
            购买建议列表（按优先级排序）
        """
        purchases = []

        for item in available_items:
            # 检查是否买得起
            if player.gold < item.price:
                continue

            # 评估购买价值
            benefit, reason = self._evaluate_purchase(floor, player, item)

            if benefit > 0:
                purchases.append(ShopPurchase(
                    item=item,
                    reason=reason,
                    expected_benefit=benefit,
                    priority=self._calculate_priority(item, benefit, player)
                ))

        # 按优先级排序
        purchases.sort(key=lambda p: p.priority, reverse=True)
        return purchases

    def _evaluate_purchase(self, floor: int, player: PlayerState,
                          item: ShopItem) -> Tuple[float, str]:
        """
        评估购买一个物品的价值

        Returns:
            (预期收益, 原因说明)
        """
        if item.type == ShopItemType.ATTACK:
            return self._evaluate_attack(player, item)
        elif item.type == ShopItemType.DEFENSE:
            return self._evaluate_defense(player, item)
        elif item.type == ShopItemType.HP:
            return self._evaluate_hp(player, item)
        elif item.type in [ShopItemType.YELLOW_KEY, ShopItemType.BLUE_KEY, ShopItemType.RED_KEY]:
            return self._evaluate_key(player, item)
        else:
            return 0.0, "未知物品类型"

    def _evaluate_attack(self, player: PlayerState, item: ShopItem) -> Tuple[float, str]:
        """
        评估购买攻击力

        攻击力价值 = 能击败的新怪物的金币收益 - 当前金币消耗
        """
        current_atk = player.atk
        new_atk = current_atk + item.value

        # 找出因为攻击力不足而无法击败的怪物
        # 这些怪物在提升攻击力后可以击败
        new_monsters = self._find_new_defeatable_monsters(current_atk, new_atk, player.defense, player.hp)

        # 计算这些怪物的总收益
        total_gold = sum(m.gold for m in new_monsters)

        # 减去购买成本
        net_value = total_gold - item.price

        # 考虑战斗消耗（生命值）
        # 简化：假设平均每场战斗消耗10%生命值
        hp_cost = len(new_monsters) * player.max_hp * 0.1
        net_value -= hp_cost

        reason = f"提升攻击力后可击败{len(new_monsters)}个新怪物，预计获得{total_gold}金币"

        return net_value, reason

    def _find_new_defeatable_monsters(self, old_atk: int, new_atk: int,
                                      defense: int, hp: int) -> List:
        """找出提升攻击力后可以击败的新怪物"""
        from detector import Monster
        from resource_manager import BattleCalculator

        new_monsters = []

        # 遍历所有楼层的怪物
        for floor in self.state.floors.values():
            for monster in floor.monsters:
                # 旧状态下无法击败
                old_player = PlayerState(atk=old_atk, defense=defense, hp=hp)
                if not BattleCalculator.can_defeat(old_player, monster):
                    # 新状态下可以击败
                    new_player = PlayerState(atk=new_atk, defense=defense, hp=hp)
                    if BattleCalculator.can_defeat(new_player, monster):
                        new_monsters.append(monster)

        return new_monsters

    def _evaluate_defense(self, player: PlayerState, item: ShopItem) -> Tuple[float, str]:
        """
        评估购买防御力

        防御力价值 = 未来战斗减少的生命值消耗
        """
        current_def = player.defense
        new_def = current_def + item.value

        # 计算所有可击败怪物在当前防御和新防御下的伤害差异
        total_saved_hp = 0

        from resource_manager import BattleCalculator

        for floor in self.state.floors.values():
            for monster in floor.monsters:
                if BattleCalculator.can_defeat(player, monster):
                    old_damage, _ = BattleCalculator.calculate_battle(player, monster)

                    # 使用新防御计算
                    test_player = PlayerState(
                        atk=player.atk,
                        defense=new_def,
                        hp=player.hp
                    )
                    new_damage, _ = BattleCalculator.calculate_battle(test_player, monster)

                    if old_damage > 0 and new_damage >= 0:
                        saved = old_damage - new_damage
                        total_saved_hp += saved

        # 生命值的价值
        hp_value = total_saved_hp * 1.0  # 1点生命 = 1金币
        net_value = hp_value - item.price

        reason = f"提升防御力后可节省约{total_saved_hp}点生命值"

        return net_value, reason

    def _evaluate_hp(self, player: PlayerState, item: ShopItem) -> Tuple[float, str]:
        """
        评估购买血瓶

        血瓶价值 = 恢复的生命值价值
        """
        hp_missing = player.max_hp - player.hp
        hp_restore = min(hp_missing, item.value)

        # 血量越低，买血越有价值
        hp_ratio = player.hp / player.max_hp
        urgency_multiplier = 1.0
        if hp_ratio < 0.3:
            urgency_multiplier = 2.0  # 危急状态
        elif hp_ratio < 0.5:
            urgency_multiplier = 1.5

        value = hp_restore * urgency_multiplier
        net_value = value - item.price

        reason = f"恢复{hp_restore}点生命值"

        return net_value, reason

    def _evaluate_key(self, player: PlayerState, item: ShopItem) -> Tuple[float, str]:
        """
        评估购买钥匙

        钥匙价值 = 开门后可获得资源的价值
        """
        key_type = item.type.value

        # 统计需要该钥匙的门后面的资源
        behind_doors_value = 0
        door_count = 0

        for floor in self.state.floors.values():
            for door in floor.doors:
                if door.color == key_type.replace('_key', ''):
                    # 简化计算：每扇门后面平均有100金币价值
                    behind_doors_value += 100
                    door_count += 1

        # 考虑钥匙的稀缺性
        if key_type == 'yellow_key':
            scarcity = 1.0
        elif key_type == 'blue_key':
            scarcity = 2.0
        else:  # red_key
            scarcity = 5.0

        value = behind_doors_value * scarcity
        net_value = value - item.price

        reason = f"可打开{door_count}扇门，预计获得{behind_doors_value}金币价值"

        return net_value, reason

    def _calculate_priority(self, item: ShopItem, benefit: float,
                           player: PlayerState) -> int:
        """
        计算购买优先级 (1-10)

        考虑因素：
        - 收益大小
        - 玩家当前状态
        - 物品类型
        """
        priority = 5  # 基础优先级

        # 根据收益调整
        if benefit > 200:
            priority += 3
        elif benefit > 100:
            priority += 2
        elif benefit > 50:
            priority += 1
        elif benefit < 0:
            priority -= 3

        # 根据物品类型调整
        if item.type == ShopItemType.ATTACK:
            # 攻击力通常是优先购买的
            priority += 1
        elif item.type == ShopItemType.HP:
            # 血量低时优先级高
            hp_ratio = player.hp / player.max_hp
            if hp_ratio < 0.3:
                priority += 3
            elif hp_ratio < 0.5:
                priority += 2

        # 限制范围
        return max(1, min(10, priority))


class ShopDetector:
    """商店检测器 - 从画面中识别商店物品"""

    def __init__(self):
        # 商店位置通常固定
        # 不同楼层的商店位置可能不同
        self.shop_positions = {
            1: {'x': 5, 'y': 5},
            4: {'x': 8, 'y': 3},
            # 其他楼层...
        }

    def detect_shop(self, frame, floor: int) -> bool:
        """
        检测当前画面是否是商店界面

        商店界面特征：
        - 绿色背景或特殊颜色
        - 显示物品和价格
        - 有购买提示
        """
        # 简化：通过颜色检测
        import cv2
        import numpy as np

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 商店通常有绿色背景
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([80, 255, 255])

        mask = cv2.inRange(hsv, lower_green, upper_green)
        green_ratio = mask.sum() / (frame.shape[0] * frame.shape[1])

        # 如果绿色区域占比超过阈值，可能是商店
        return green_ratio > 0.1

    def parse_shop_items(self, frame, floor: int) -> List[ShopItem]:
        """
        解析商店中的物品

        需要识别：
        - 物品类型
        - 价格
        - 属性提升值
        """
        # 简化：返回预设物品
        # 实际使用时需要通过OCR识别
        items = []

        if floor == 1:
            items = [
                ShopItem(ShopItemType.ATTACK, "攻击力+3", 20, 3),
                ShopItem(ShopItemType.DEFENSE, "防御力+3", 20, 3),
                ShopItem(ShopItemType.HP, "血瓶", 50, 800),
            ]
        elif floor == 4:
            items = [
                ShopItem(ShopItemType.ATTACK, "攻击力+3", 50, 3),
                ShopItem(ShopItemType.DEFENSE, "防御力+3", 50, 3),
                ShopItem(ShopItemType.HP, "血瓶", 100, 800),
            ]

        return items


# 与resource_manager集成
def integrate_shop_with_resource_manager():
    """将商店决策整合到资源管理器中"""
    from resource_manager import ResourceManager, ResourceGain, ResourceCost

    class EnhancedResourceManager(ResourceManager):
        """增强的资源管理器，包含商店决策"""

        def __init__(self, game_state: GameState):
            super().__init__(game_state)
            self.shop_analyzer = ShopAnalyzer(game_state)

        def evaluate_shop_visit(self, floor: int) -> Optional[ShopPurchase]:
            """评估是否应该访问商店"""
            # 检查是否有商店
            shop_items = self._get_shop_items(floor)
            if not shop_items:
                return None

            # 分析购买建议
            purchases = self.shop_analyzer.analyze_shop(
                floor,
                self.state.player,
                shop_items
            )

            if not purchases:
                return None

            # 返回最佳购买建议
            return purchases[0]

        def _get_shop_items(self, floor: int) -> List[ShopItem]:
            """获取指定楼层的商店物品"""
            detector = ShopDetector()
            # 这里需要从实际画面获取
            # 简化：返回配置
            items = []

            config = self.SHOP_CONFIG.get(floor, {})
            for item_type, data in config.items():
                items.append(ShopItem(
                    type=ShopItemType(item_type),
                    name=f"{item_type.capitalize()}+{data['value']}",
                    price=data['price'],
                    value=data['value']
                ))

            return items

    return EnhancedResourceManager


if __name__ == "__main__":
    # 测试
    from state import GameState, PlayerState

    state = GameState()
    player = PlayerState(
        floor=1,
        x=1,
        y=1,
        hp=500,
        max_hp=1000,
        atk=20,
        defense=10,
        yellow_keys=1,
        blue_keys=0,
        red_keys=0,
        gold=100
    )
    state.player = player

    analyzer = ShopAnalyzer(state)

    # 测试商店物品
    items = [
        ShopItem(ShopItemType.ATTACK, "攻击力+3", 20, 3),
        ShopItem(ShopItemType.DEFENSE, "防御力+3", 20, 3),
        ShopItem(ShopItemType.HP, "血瓶", 50, 800),
    ]

    purchases = analyzer.analyze_shop(1, player, items)

    print("商店购买建议：")
    for p in purchases:
        print(f"  [{p.priority}/10] {p.item.name}: {p.reason}")
        print(f"           预期收益: {p.expected_benefit:.1f}金币")
