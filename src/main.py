"""
魔塔自动游玩脚本 - 主程序
"""
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from capture import ScreenCapture, FrameBuffer
from detector import GameElementDetector
from state import GameState
from planner import GamePlanner, AggressiveStrategy
from controller import Controller, SmartController, ReplayRecorder
from resource_manager import ResourceManager, ForwardPlanner
from shop import ShopAnalyzer


class MotaBot:
    """魔塔自动游玩机器人"""

    def __init__(self,
                 window_title: str = "魔塔",
                 strategy: str = "normal",
                 debug: bool = False):
        """
        初始化机器人

        Args:
            window_title: 游戏窗口标题
            strategy: 游戏策略 ("normal", "aggressive", "conservative")
            debug: 是否开启调试模式
        """
        self.window_title = window_title
        self.debug = debug
        self.running = False
        self.paused = False

        # 初始化各个模块
        print("初始化模块...")

        # 截图模块
        print("  - 截图模块")
        self.capture = ScreenCapture(window_title)

        # 帧缓冲（用于检测动画结束）
        self.frame_buffer = FrameBuffer(size=3)

        # 元素检测器
        print("  - 元素检测器")
        self.detector = GameElementDetector()

        # 游戏状态
        print("  - 游戏状态")
        self.state = GameState(max_floors=24)

        # 决策规划器
        print("  - 决策规划器")
        self.planner = GamePlanner(self.state)

        # 资源管理器（核心决策模块）
        print("  - 资源管理器")
        self.resource_manager = ResourceManager(self.state)

        # 控制器
        print("  - 控制器")
        self.controller = SmartController(
            key_delay=0.05,
            action_delay=0.15
        )

        # 录制器（可选）
        self.recorder = ReplayRecorder()

        # 统计信息
        self.loop_count = 0
        self.start_time = None

        print("初始化完成!\n")

    def start(self):
        """启动自动游玩"""
        self.running = True
        self.start_time = datetime.now()
        self.recorder.start()

        print("=" * 50)
        print("魔塔自动游玩机器人启动")
        print("=" * 50)
        print(f"窗口标题: {self.window_title}")
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 50)
        print("\n按 Ctrl+C 停止\n")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("\n\n收到停止信号，正在退出...")
        except Exception as e:
            print(f"\n\n错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def _main_loop(self):
        """主循环"""
        last_action = None
        action_repeat_count = 0
        MAX_REPEAT = 3  # 最大重复次数

        while self.running:
            self.loop_count += 1

            # 1. 截图
            frame = self.capture.capture()

            # 2. 检测画面是否稳定（动画是否结束）
            self.frame_buffer.add(frame)

            if not self.frame_buffer.is_stable(threshold=0.98):
                # 画面还在动画中，等待
                time.sleep(0.05)
                continue

            # 3. 识别游戏元素
            player = self.detector.detect_player(frame)
            if not player:
                print("无法检测到玩家位置，等待...")
                time.sleep(0.5)
                continue

            monsters = self.detector.detect_monsters(frame)
            doors = self.detector.detect_doors(frame)
            keys = self.detector.detect_keys(frame)
            stairs = self.detector.detect_stairs(frame)

            # 4. 更新游戏状态
            # 注意：这里简化处理，实际需要从状态栏读取完整信息
            self.state.update_player_position(player.x, player.y)

            current_floor = self.state.get_current_floor()
            current_floor.monsters = monsters
            current_floor.doors = doors
            current_floor.keys = keys
            current_floor.stairs = stairs

            # 更新网格地图
            for m in monsters:
                current_floor.set_cell_type(m.x, m.y, 3)
            for d in doors:
                current_floor.set_cell_type(d.x, d.y, 2)
            for k in keys:
                current_floor.set_cell_type(k.x, k.y, 4)
            if stairs.get('up'):
                current_floor.set_cell_type(stairs['up'].x, stairs['up'].y, 5)
            if stairs.get('down'):
                current_floor.set_cell_type(stairs['down'].x, stairs['down'].y, 5)

            # 5. 规划下一步动作（使用资源管理器）
            action, plan = self._plan_next_action()

            # 6. 检查是否陷入循环
            if action == last_action:
                action_repeat_count += 1
                if action_repeat_count >= MAX_REPEAT:
                    print(f"警告: 检测到动作重复 {MAX_REPEAT} 次，可能卡住")
                    # 尝试随机动作
                    action = self._get_random_action()
                    action_repeat_count = 0
            else:
                action_repeat_count = 0
                last_action = action

            # 7. 执行动作
            if self.debug:
                print(f"[{self.loop_count}] {action.value} -> {plan.reason}")
                print(f"  位置: ({self.state.player.x}, {self.state.player.y})")
                print(f"  目标: ({plan.target_x}, {plan.target_y})")
                if self.loop_count % 10 == 0:
                    print(f"  状态: {self.state}")

            self.controller.execute(action)
            self.recorder.record(action)

            # 8. 检查游戏是否结束
            if self._check_game_over():
                print("\n游戏结束！")
                break

            # 9. 检查胜利
            if self._check_victory():
                print("\n恭喜通关！")
                break

            # 10. 控制循环速度
            time.sleep(0.1)

    def _plan_next_action(self):
        """规划下一步动作"""
        from planner import Plan, Action

        # 使用资源管理器推荐行动
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

        # 备用：使用原始规划器
        plan = self.planner.plan_next_action()
        action = self.planner.get_next_step(plan)
        return action, plan

    def _get_random_action(self):
        """获取随机动作"""
        import random
        actions = [
            Action.UP, Action.DOWN, Action.LEFT, Action.RIGHT
        ]
        return random.choice(actions)

    def _check_game_over(self) -> bool:
        """检查游戏是否失败"""
        # 简单判断：血量为0
        return self.state.player.hp <= 0

    def _check_victory(self) -> bool:
        """检查是否胜利"""
        # 简单判断：到达24层或打败最终Boss
        return self.state.current_floor >= 24

    def pause(self):
        """暂停"""
        self.paused = True
        print("已暂停")

    def resume(self):
        """恢复"""
        self.paused = False
        print("已恢复")

    def stop(self):
        """停止"""
        self.running = False
        self.recorder.stop()

        # 保存录制
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        replay_file = f"logs/replay_{timestamp}.json"
        Path("logs").mkdir(exist_ok=True)
        self.recorder.save(replay_file)
        print(f"录制已保存: {replay_file}")

        # 保存最终状态
        state_file = f"logs/state_{timestamp}.json"
        self.state.save_state(state_file)
        print(f"状态已保存: {state_file}")

        # 打印统计信息
        self._print_stats()

    def _print_stats(self):
        """打印统计信息"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print("\n" + "=" * 50)
        print("统计信息")
        print("=" * 50)
        print(f"运行时间: {elapsed:.1f} 秒")
        print(f"循环次数: {self.loop_count}")
        print(f"执行动作: {self.controller.get_action_count()} 次")
        print(f"动作速度: {self.controller.get_actions_per_second():.1f} 次/秒")
        print(f"最终状态: {self.state}")
        print("=" * 50)


def test_detection():
    """测试检测功能"""
    print("测试检测功能...")

    capture = ScreenCapture()
    detector = GameElementDetector()

    print("按 Enter 键截图，按 q 退出...")

    while True:
        cmd = input()
        if cmd.lower() == 'q':
            break

        frame = capture.capture()
        print(f"截图尺寸: {frame.shape}")

        # 检测玩家
        player = detector.detect_player(frame)
        print(f"玩家位置: {(player.x, player.y) if player else '未检测到'}")

        # 检测怪物
        monsters = detector.detect_monsters(frame)
        print(f"怪物数量: {len(monsters)}")
        for m in monsters:
            print(f"  - {m.name} at ({m.x}, {m.y})")

        # 检测门
        doors = detector.detect_doors(frame)
        print(f"门数量: {len(doors)}")
        for d in doors:
            print(f"  - {d.color} door at ({d.x}, {d.y})")

        # 检测钥匙
        keys = detector.detect_keys(frame)
        print(f"钥匙数量: {len(keys)}")
        for k in keys:
            print(f"  - {k.color} key at ({k.x}, {k.y})")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='魔塔自动游玩脚本')
    parser.add_argument('--window', '-w', type=str, default='魔塔',
                        help='游戏窗口标题')
    parser.add_argument('--strategy', '-s', type=str,
                        choices=['normal', 'aggressive', 'conservative'],
                        default='normal',
                        help='游戏策略')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='开启调试模式')
    parser.add_argument('--test', '-t', action='store_true',
                        help='运行检测测试')

    args = parser.parse_args()

    if args.test:
        test_detection()
        return

    # 创建机器人
    bot = MotaBot(
        window_title=args.window,
        strategy=args.strategy,
        debug=args.debug
    )

    # 启动
    bot.start()


if __name__ == "__main__":
    main()
