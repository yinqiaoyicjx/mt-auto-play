# 魔塔自动游玩脚本

基于图像识别的《魔塔24层》自动游玩Python脚本。

## 功能特点

- **图像识别**：通过OpenCV识别游戏元素（玩家、怪物、门、钥匙等）
- **自动寻路**：使用BFS/A*算法进行路径规划
- **智能决策**：自动计算战斗收益，选择最优行动
- **战斗模拟**：预先计算战斗结果，避免死亡
- **操作录制**：记录游戏过程，支持回放
- **状态保存**：保存游戏进度，支持断点续玩
- **GUI界面**：图形化界面，实时显示决策和状态 ⭐新增

## 目录结构

```
mota/
├── scripts/             # 启动脚本目录
│   ├── start.bat        # 命令行模式启动
│   ├── start_debug.bat  # 命令行调试模式
│   ├── start_gui.bat    # GUI模式启动 ⭐推荐
│   ├── tools.bat        # 工具集菜单
│   ├── install.bat      # 安装依赖
│   └── check.bat        # 系统检查
├── src/                 # 源代码目录
│   ├── main.py          # 主程序入口
│   ├── gui_launcher.py  # GUI启动器 ⭐新增
│   ├── capture.py       # 屏幕截图模块
│   ├── detector.py      # 游戏元素识别
│   ├── state.py         # 游戏状态管理
│   ├── planner.py       # 路径规划和决策
│   ├── controller.py    # 键盘控制执行
│   ├── resource_manager.py  # 资源管理与决策（核心）
│   ├── shop.py          # 商店购买决策
│   ├── tools.py         # 工具集
│   └── config.py        # 配置文件
├── data/
│   ├── monsters.json    # 怪物数据库
│   └── templates/       # 怪物模板图片（需自行收集）
├── logs/                # 日志和录制文件
├── requirements.txt     # 依赖包
├── README.md            # 使用说明
└── PROGRESS.md          # 项目进度
```

## 快速开始（Windows）

### 1. 安装依赖

双击运行 `install.bat`，或在命令行执行：

```bash
pip install -r requirements.txt
```

### 2. 系统检查

双击运行 `check.bat` 检查环境是否正常。

### 3. 收集怪物模板

双击运行 `tools.bat`，选择功能1（手动收集）或功能2（从手册收集）。

### 4. 启动自动游玩

推荐使用 **GUI模式**（图形界面）：

- 双击 `start_gui.bat` - GUI模式 ⭐**推荐**
  - 实时游戏画面预览
  - 开始/暂停/停止控制
  - 实时显示游戏状态（楼层、血量、攻防等）
  - 显示当前决策内容和原因
  - 活动日志输出

其他模式：

- 双击 `start.bat` - 命令行模式
- 双击 `start_debug.bat` - 调试模式（显示详细决策信息）

---

## 详细使用说明

### 环境要求

- Python 3.8+
- Windows 10/11
- 魔塔游戏（网页版或客户端版）

### 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

1. 启动魔塔游戏
2. 运行脚本：

```bash
python main.py
```

### 命令行参数

```
python main.py [选项]

选项:
  --window, -w   游戏窗口标题（默认："魔塔"）
  --strategy, -s 游戏策略
                 - normal: 正常策略
                 - aggressive: 激进策略
                 - conservative: 保守策略
  --debug, -d    开启调试模式
  --test, -t     运行检测测试
```

### 示例

```bash
# 使用默认配置运行
python main.py

# 指定窗口标题
python main.py --window "魔塔V1.2"

# 使用激进策略
python main.py --strategy aggressive

# 开启调试模式
python main.py --debug

# 运行检测测试
python main.py --test
```

## 配置

编辑 `config.py` 修改配置：

```python
# 游戏窗口标题
WINDOW_TITLE = "魔塔"

# 网格大小（每个格子的像素）
GRID_SIZE = 32

# 按键延迟（秒）
CONTROL = {
    'key_delay': 0.05,
    'action_delay': 0.15,
}

# 检测阈值
DETECTION = {
    'template_match_threshold': 0.8,
    'stability_threshold': 0.98,
}
```

## 怪物模板

脚本需要怪物模板图片才能识别。有两种收集方式：

### 方式1：使用工具集（推荐）

双击运行 `tools.bat`，选择：
- **功能1**：手动收集 - 在游戏中找到怪物，按 `c` 截图
- **功能2**：从手册收集 - 打开游戏中的怪物手册，自动截取

### 方式2：手动收集

1. 在游戏中找到怪物
2. 截取怪物的图像（32x32像素）
3. 保存到 `data/templates/` 目录
4. 命名格式：`怪物名称.png`

### 其他工具

`tools.bat` 还提供：
- **功能3**：调整游戏窗口大小为640x480
- **功能4**：校准网格大小
- **功能5**：测试检测功能

## 游戏策略

### Normal（正常策略）

- 平衡战斗和探索
- 血量低于50%时考虑撤退
- 优先收集钥匙和道具

### Aggressive（激进策略）

- 优先战斗和获取金币
- 更高的风险承受度

### Conservative（保守策略）

- 优先保证生存
- 避免危险战斗
- 充分探索后再推进

## 路径规划

脚本使用以下算法：

- **BFS**：无权图最短路径
- **A\***：带权重的最优路径

## 战斗系统

脚本会自动计算：

- 战斗需要的回合数
- 预期受到的伤害
- 是否能战胜怪物
- 战斗收益评估

## 录制和回放

每次运行会自动保存：

- `logs/replay_YYYYMMDD_HHMMSS.json` - 操作录制
- `logs/state_YYYYMMDD_HHMMSS.json` - 游戏状态

## GUI界面功能

GUI模式提供可视化操作界面：

```
┌─────────────────────────────────────────────┐
│ [Select Region|Start|Pause|Stop|Exit] ☑Debug│ 控制按钮
├─────────────────────────────────────────────┤
│                                              │
│            Game Preview                      │  游戏画面
│           (416x416 实时)                     │
│                                              │
├─────────────────────────────────────────────┤
│  Floor: 1  HP: 1000/1000  Atk: 10           │  游戏状态
│  Def: 10   Gold: 0    Keys: Y1 B0 R0       │
├─────────────────────────────────────────────┤
│  Current Decision:                           │  当前决策
│  Move to (5, 5) to collect yellow key       │
├─────────────────────────────────────────────┤
│  Action: RIGHT                               │  决策详情
│  Target: (5, 5)                              │
│  Cost: 0 HP                                  │
│  Gain: 20 Gold                               │
├─────────────────────────────────────────────┤
│  Activity Log                                │  活动日志
│  [10:30:15] Step 1: Move to (5, 5)         │
│  [10:30:16] Step 2: Defeated slime         │
│  ...                                         │
├─────────────────────────────────────────────┤
│  Running    Running: 45s                    │  状态栏
└─────────────────────────────────────────────┘
```

**功能说明：**

- **Select Region** - 手动选择截图区域（调试用）
  - 点击后会出现全屏半透明窗口
  - 用鼠标拖拽选择游戏截图区域
  - 适合分屏调试：左边放游戏，右边放GUI
- **Start** - 启动自动游玩
- **Pause** - 暂停/恢复
- **Stop** - 停止运行
- **Debug Mode** - 开启后显示更详细的决策信息
- **Game Preview** - 实时显示游戏画面（红框标记截图区域）
- **Game Status** - 显示楼层、血量、攻防、金币、钥匙
- **Current Decision** - 显示当前决策内容和原因
- **Decision Details** - 显示动作、目标、消耗、收益
- **Activity Log** - 记录每步操作和重要事件

## 注意事项

1. **游戏窗口位置**：
   - 自动模式：游戏窗口必须在前台，不要移动窗口
   - 手动模式：点击"Select Region"选择截图区域后，可以自由调整窗口位置

2. **推荐调试布局**：
   ```
   ┌────────────────┬────────────────┐
   │  游戏窗口       │   GUI窗口       │
   │  (左边一半)     │   (右边一半)    │
   │                │                │
   └────────────────┴────────────────┘
   ```

3. 首次使用需要收集怪物模板

4. 网格大小（GRID_SIZE）可能需要根据游戏版本调整

## 故障排除

### 无法找到游戏窗口

- 确认游戏窗口标题正确
- 使用 `--window` 参数指定完整标题

### 检测不到玩家/怪物

- 检查 `GRID_SIZE` 设置
- 确认游戏分辨率
- 收集更多怪物模板

### 动作不生效

- 增加 `key_delay` 和 `action_delay`
- 确认游戏窗口有焦点

### GUI界面问题

- **界面无法启动**：检查tkinter是否安装（`python -c "import tkinter"`）
- **画面不显示**：确认游戏窗口在前台
- **界面卡顿**：关闭Debug Mode，降低画面预览刷新频率

## 开发

### 模块说明

| 模块 | 功能 |
|------|------|
| [main.py](src/main.py) | 命令行模式主程序 |
| [gui_launcher.py](src/gui_launcher.py) | GUI图形界面启动器 |
| [capture.py](src/capture.py) | 屏幕截图，窗口定位和大小固定 |
| [detector.py](src/detector.py) | 游戏元素识别 |
| [state.py](src/state.py) | 游戏状态管理 |
| [planner.py](src/planner.py) | 路径规划和决策 |
| [controller.py](src/controller.py) | 键盘控制 |
| [resource_manager.py](src/resource_manager.py) | 资源管理与决策（核心） |
| [shop.py](src/shop.py) | 商店购买决策 |
| [tools.py](src/tools.py) | 工具集 |
| [config.py](src/config.py) | 配置文件 |

### 扩展功能

1. **添加新怪物**：编辑 `data/monsters.json`
2. **自定义策略**：继承 `Strategy` 类
3. **优化检测**：调整颜色范围和模板匹配阈值

## 许可

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 相关资源

- [魔塔游戏](https://www.baidu.com/s?wd=魔塔游戏)
- [OpenCV文档](https://docs.opencv.org/)
- [PyAutoGUI文档](https://pyautogui.readthedocs.io/)
