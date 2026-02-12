"""
配置文件
"""
import os

# 游戏窗口配置
WINDOW_TITLE = "魔塔"
WINDOW_CLASS = None  # 可选，用于更精确的窗口匹配

# 网格配置
GRID_SIZE = 32  # 每个格子的像素大小
DEFAULT_GRID_WIDTH = 13  # 默认网格宽度
DEFAULT_GRID_HEIGHT = 11  # 默认网格高度

# 游戏元素颜色 (HSV范围)
COLORS = {
    'player': {
        'lower': [100, 80, 80],
        'upper': [130, 255, 255]
    },
    'yellow_door': {
        'lower': [20, 100, 100],
        'upper': [40, 255, 255]
    },
    'blue_door': {
        'lower': [100, 50, 50],
        'upper': [130, 255, 255]
    },
    'red_door': {
        'lower': [0, 50, 50],
        'upper': [10, 255, 255]
    },
    'yellow_key': {
        'lower': [20, 100, 100],
        'upper': [40, 255, 255]
    },
    'blue_key': {
        'lower': [100, 50, 50],
        'upper': [130, 255, 255]
    },
    'red_key': {
        'lower': [0, 50, 50],
        'upper': [10, 255, 255]
    },
}

# 检测阈值
DETECTION = {
    'template_match_threshold': 0.8,  # 模板匹配相似度阈值
    'stability_threshold': 0.98,  # 画面稳定判断阈值
    'max_retries': 3,  # 最大重试次数
}

# 控制配置
CONTROL = {
    'key_delay': 0.05,  # 按键间隔（秒）
    'action_delay': 0.15,  # 动作完成后等待时间（秒）
    'animation_wait': 0.3,  # 动画等待时间（秒）
}

# 战斗配置
COMBAT = {
    'hp_retreat_threshold': 0.5,  # 血量低于此比例时考虑撤退
    'safety_margin': 1.1,  # 安全余量（实际血量需要是预期伤害的倍数）
}

# 路径规划配置
PATHFINDING = {
    'algorithm': 'bfs',  # 'bfs' 或 'a_star'
    'max_path_length': 100,  # 最大路径长度
}

# 日志配置
LOG = {
    'enabled': True,
    'level': 'INFO',  # 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    'save_replay': True,  # 是否保存回放
    'save_state': True,  # 是否保存游戏状态
    'log_dir': 'logs',
}

# 调试配置
DEBUG = {
    'show_detection': False,  # 是否显示检测框
    'show_path': False,  # 是否显示规划路径
    'verbose': False,  # 详细输出
}

# 文件路径
PATHS = {
    'template_dir': 'data/templates',
    'monster_data': 'data/monsters.json',
    'log_dir': 'logs',
}

# 确保目录存在
for path in PATHS.values():
    if path.endswith('s') or 'dir' in path or 'log' in path:
        os.makedirs(path, exist_ok=True)
    else:
        os.makedirs(os.path.dirname(path), exist_ok=True)
