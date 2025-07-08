import time
import random
from enum import Enum, auto
from PyQt5.QtCore import Qt, QPoint, QTimer, QRect
from PyQt5.QtGui import QPixmap # Import QPixmap
import os
from PyQt5.QtWidgets import QApplication
import win32gui
import win32con
from pet_tomato_timer import TomatoState, PetTomatoTimer

class PetState(Enum):
    """
    定义桌宠的所有可能状态。
    状态分为两大类：
    1. 核心状态：表示桌宠的基本状态，可以持续存在
    2. 过渡动画：表示从一个核心状态转换到另一个核心状态时的动画过程
    """
    # ===== 核心状态 =====
    # 这些状态是桌宠可以持续存在的基本状态
    
    # --- 基础状态 ---
    IDLE = auto()           # 待机/空闲状态：桌宠的默认状态，会播放呼吸或眨眼等日常动画
    SLEEP = auto()          # 睡眠状态：长时间无交互后进入，播放睡眠动画
    STAND = auto()          # 站立状态：从IDLE状态点击后进入，表示注意力集中
    CATCH = auto()          # 抓取状态：被鼠标拖动时的状态
    HAPPY_LOOP = auto()     # 开心循环状态：Victory手势触发后的循环动画
    BREAK = auto()          # 休息提醒状态：每小时提醒一次休息
    DRINK = auto()          # 喝水状态：提醒喝水
    
    # --- 移动状态 ---
    WALK = auto()           # 行走状态：在屏幕上从左向右移动，同时播放行走循环动画
    FALL = auto()          # 下坠状态：当没有落脚点时进入此状态
    
    # --- 互动状态 ---
    DANCE = auto()          # 跳舞状态：检测到音乐时触发，播放跳舞循环动画
    
    # --- 番茄钟状态 ---
    TOMATO_WORKING = auto()  # 番茄钟工作状态
    TOMATO_BREAK = auto()    # 番茄钟休息过渡动画
    TOMATO_RESTING = auto()  # 番茄钟休息状态
    TOMATO_COMPLETED = auto() # 番茄钟完成状态
    # --- 拖拽专用 ---
    TOMATO_DRAG = auto()
    BREAK_DRAG = auto()
    HAPPY_DRAG = auto()
    
    # --- 喝水状态 ---
    DRINK_LOOP = auto()     # 喝水循环状态：喝水状态的循环动画
    
    # ===== 过渡动画 =====
    # 这些状态表示状态转换过程中的临时动画
    # 通常播放一次后会自动切换到目标状态
    
    # --- 睡眠相关 ---
    AWAKENING = auto()      # 从 SLEEP -> IDLE：被点击唤醒时的动画
    
    # --- 站立相关 ---
    IDLE_TO_STAND = auto()  # 从 IDLE -> STAND：开始站立的动画
    STAND_TO_IDLE = auto()  # 从 STAND -> IDLE：结束站立的动画
    
    # --- 跳舞相关 ---
    STAND_TO_DANCE = auto()
    DANCE_TO_STAND = auto() # 从 DANCE -> STAND：结束跳舞的动画
    
    # --- 行走相关 ---
    WALK_BEGIN = auto()     # 从 IDLE -> WALK：开始行走的动画
    WALK_END = auto()       # 从 WALK -> IDLE：结束行走的动画

    # --- 下落相关 ---
    FALL_END = auto()       # 从 FALL -> IDLE：结束下落的动画
    
    # --- 开心相关 ---
    HAPPY_BEGIN = auto()    # 从 STAND -> HAPPY_LOOP：开始开心的动画
    
    # --- 番茄钟相关 ---
    IDLE_TO_TOMATO = auto()  # 从其他状态 -> TOMATO_WORKING：开始番茄钟工作状态

    @classmethod
    def is_core_state(cls, state):
        """
        判断一个状态是否为核心状态。
        核心状态可以持续存在，而过渡动画状态通常只是临时的。
        """
        return state in [
            cls.IDLE,
            cls.SLEEP,
            cls.STAND,
            cls.WALK,
            cls.DANCE,
            cls.FALL,
            cls.CATCH,
            cls.HAPPY_LOOP,
            cls.TOMATO_WORKING,
            cls.TOMATO_BREAK,
            cls.TOMATO_RESTING,
            cls.TOMATO_COMPLETED,
            cls.BREAK,
            cls.DRINK,
            cls.DRINK_LOOP,
            cls.TOMATO_DRAG,
            cls.BREAK_DRAG,
            cls.HAPPY_DRAG
        ]

    @classmethod
    def get_animation_end_state(cls, state):
        """
        获取过渡动画结束后应该进入的目标状态。
        仅适用于过渡动画状态。
        """
        animation_targets = {
            cls.AWAKENING: cls.IDLE,        # 唤醒动画 -> 空闲状态
            cls.IDLE_TO_STAND: cls.STAND,   # 起立动画 -> 站立状态
            cls.STAND_TO_IDLE: cls.IDLE,    # 坐下动画 -> 空闲状态
            cls.STAND_TO_DANCE: cls.DANCE,  # 开始跳舞 -> 跳舞状态
            cls.DANCE_TO_STAND: cls.STAND,  # 停止跳舞 -> 站立状态
            cls.WALK_BEGIN: cls.WALK,       # 开始行走 -> 行走状态
            cls.WALK_END: cls.IDLE,         # 停止行走 -> 空闲状态
            cls.FALL_END: cls.IDLE,         # 结束下落 -> 空闲状态
            cls.HAPPY_BEGIN: cls.HAPPY_LOOP, # 开始开心 -> 开心循环
            cls.IDLE_TO_TOMATO: cls.TOMATO_WORKING,  # 开始番茄钟 -> 工作状态
            cls.TOMATO_BREAK: cls.TOMATO_RESTING,    # 休息过渡 -> 休息状态
            cls.BREAK: cls.IDLE,
            cls.DRINK: cls.DRINK_LOOP,
            cls.DRINK_LOOP: cls.IDLE,
            cls.TOMATO_DRAG: cls.TOMATO_WORKING,
            cls.BREAK_DRAG: cls.TOMATO_BREAK,
            cls.HAPPY_DRAG: cls.HAPPY_LOOP
        }
        return animation_targets.get(state)


class PetInteraction:
    """
    处理宠物的交互逻辑、状态管理以及动画播放。
    这个类不直接与窗口显示打交道，而是通过PetDisplay实例来更新宠物的视觉表现。
    """
    def __init__(self, pet_window, initial_state=PetState.IDLE):
        """
        初始化宠物交互处理器。

        Args:
            pet_window (PetDisplay): 宠物的显示窗口实例。
            initial_state (PetState): 宠物的初始状态，默认为IDLE。
        """
        # 基础组件设置
        self.pet_window = pet_window          # 显示窗口实例
        self.current_state = initial_state    # 当前状态
        self.drag_position = QPoint()         # 拖动位置
        self.is_music_playing = False         # 音乐播放状态标志
        self.music_detection_enabled = True   # 音乐检测功能开关状态
        
        # 休息提醒配置
        self.break_config = {
            "enabled": False,                 # 默认关闭休息提醒
            "interval": 60,                   # 休息间隔（分钟）
            "duration": 5,                    # 休息时长（分钟）
            "last_break": time.time()         # 上次休息时间
        }
        
        # 喝水提醒配置
        self.water_config = {
            "enabled": False,                 # 默认关闭喝水提醒
            "interval": 60,                   # 喝水间隔（分钟）
            "duration": 60,                   # 喝水提醒持续时间（秒）
            "last_water": time.time()         # 上次喝水时间
        }
        
        # 创建喝水检查定时器
        self.water_timer = QTimer()
        self.water_timer.timeout.connect(self._check_water_time)
        self.water_timer.setInterval(60000)  # 每分钟检查一次
        
        # 状态时间戳管理
        self.state_timestamps = {
            "last_interaction": time.time(),  # 上次交互时间
            "last_state_change": time.time()  # 上次状态改变时间
        }
        
        # 初始化番茄钟计时器
        self.tomato_timer = PetTomatoTimer(self)
        
        # 状态转换配置
        self.state_transitions = {
            # IDLE状态的转换配置
            PetState.IDLE: {
                "check": self._check_idle_timeout,     # 检查方法
                "next_state": PetState.SLEEP,          # 超时后的目标状态
                "threshold": 10                        # 空闲到睡眠的阈值（10秒）
            },
            # STAND状态的转换配置
            PetState.STAND: {
                "check": self._check_stand_timeout,    # 检查方法
                "next_state": PetState.STAND_TO_IDLE,  # 超时后的目标状态
                "threshold": 5                         # 站立到空闲的阈值（5秒）
            },
            # DANCE状态不需要自动转换，由音乐状态控制
        }

        # --- 动画配置中心 (animations_config) ---
        # 定义了每个 PetState 对应的动画细节。
        #   "frames_dir": (str) 存放该状态动画帧图片的子目录路径 (相对于项目根目录, e.g., "sprites/idle/")。
        #   "prefix":     (str) 该状态动画帧图片文件名的通用前缀 (e.g., "idle_")。
        #                       程序会查找如 prefix + "0.png", prefix + "1.png", ... 的文件。
        #   "count":      (int) 该动画的总帧数。
        #   "frame_duration": (int) 每帧的显示时长 (单位: 毫秒)。 值越小，动画越快。
        #   "loops":      (int) 动画循环次数:
        #                       -1: 无限循环。
        #                        0: 播放一次，然后停留在该动画的最后一帧。
        #                       N>0: 播放 N 次，然后停留在该动画的最后一帧。
        #   "next_state": (PetState, 可选) 当动画播放完成 (loops为0或N>0时)，自动转换到的下一个PetState。
        #                             如果未定义此项，动画播完后将保持在当前状态（显示最后一帧）。
        self.animations_config = {
            # --- IDLE (待机) 状态动画 ---
            PetState.IDLE: {
                "frames_dir": "sprites/idle/", 
                "prefix": "idle_", 
                "count": 3,
                "frame_duration": 125, # 8 FPS
                "loops": -1 # 无限循环
            },
            # --- BREAK (休息提醒) 状态动画 ---
            PetState.BREAK: {
                "frames_dir": "sprites/break/", 
                "prefix": "break_", 
                "count": 1,  # 修改为实际的帧数
                "frame_duration": 125,  # 8 FPS
                "loops": -1  # 无限循环播放
            },
            # --- HAPPY_BEGIN (开始开心) 动画 ---
            PetState.HAPPY_BEGIN: {
                "frames_dir": "sprites/happy/begin/", 
                "prefix": "begin_", 
                "count": 6,
                "frame_duration": 125,  # 8 FPS
                "loops": 0,  # 播放一次
                "next_state": PetState.HAPPY_LOOP  # 播放完后进入循环状态
            },
            # --- HAPPY_LOOP (开心循环) 状态动画 ---
            PetState.HAPPY_LOOP: {
                "frames_dir": "sprites/happy/loop/", 
                "prefix": "loop_", 
                "count": 8,
                "frame_duration": 125,  # 8 FPS
                "loops": -1  # 无限循环
            },
            # --- SLEEP (睡眠) 状态动画 ---
            PetState.SLEEP: {
                "frames_dir": "sprites/sleep/", 
                "prefix": "sleep_", 
                "count": 11,
                "frame_duration": 125,
                "loops": 0 # 播放一次，然后停留在最后一帧
            },
            # --- STAND (站立) 状态动画/图像 ---
            PetState.STAND: {
                "frames_dir": "sprites/stand/", 
                "prefix": "stand_", 
                "count": 1, 
                "frame_duration": 200,
                "loops": 0 # 播放一次
            },
            # --- AWAKENING (唤醒) 动画: SLEEP -> IDLE ---
            PetState.AWAKENING: {
                "frames_dir": "sprites/sleep/",  # 重用睡眠状态的动画帧
                "prefix": "sleep_", 
                "count": 4, 
                "frame_duration": 150, 
                "loops": 0, # 播放一次
                "next_state": PetState.IDLE, # 播放完毕后进入IDLE状态
                "reverse_playback": True  # 倒放动画
            },
            # --- IDLE_TO_STAND (待机到站立的过渡) 动画: IDLE -> STAND ---
            PetState.IDLE_TO_STAND: {
                "frames_dir": "sprites/idle_to_stand/", 
                "prefix": "T_",      
                "count": 9,            
                "frame_duration": 125, 
                "loops": 0,           # 播放一次
                "next_state": PetState.STAND  # 播放完毕后进入STAND状态
            },
            # --- STAND_TO_IDLE (站立到待机) 动画 ---
            PetState.STAND_TO_IDLE: {
                "frames_dir": "sprites/idle_to_stand/", # 重用idle_to_stand的动画帧
                "prefix": "T_", 
                "count": 9, 
                "frame_duration": 150, 
                "loops": 0, # 播放一次
                "next_state": PetState.IDLE, # 播放完毕后进入IDLE状态
                "reverse_playback": True  # 反向播放idle_to_stand的动画
            },
            # --- DANCE (跳舞) 状态动画 ---
            PetState.DANCE: {
                "frames_dir": "sprites/dance/loop/", 
                "prefix": "loop_", 
                "count": 8,
                "frame_duration": 125,  # 8 FPS
                "loops": -1  # 无限循环
            },
            # --- STAND_TO_DANCE (站立到跳舞) 动画 ---
            PetState.STAND_TO_DANCE: {
                "frames_dir": "sprites/dance/begin/", 
                "prefix": "dance_",
                "count": 6,
                "frame_duration": 125,
                "loops": 0,  # 播放一次
                "next_state": PetState.DANCE  # 过渡到跳舞状态
            },
            # --- DANCE_TO_STAND (跳舞到站立) 动画 ---
            PetState.DANCE_TO_STAND: {
                "frames_dir": "sprites/dance/end/", 
                "prefix": "end_",
                "count": 6,
                "frame_duration": 125,
                "loops": 0,  # 播放一次
                "next_state": PetState.STAND  # 返回站立状态
            },
            # --- WALK_BEGIN (开始行走) 动画 ---
            PetState.WALK_BEGIN: {
                "frames_dir": "sprites/walk/begin/", 
                "prefix": "begin_",
                "count": 4,
                "frame_duration": 250,  
                "loops": 0,  # 播放一次
                "next_state": PetState.WALK  # 播放完后进入行走状态
            },
            # --- WALK (行走循环) 状态动画 ---
            PetState.WALK: {
                "frames_dir": "sprites/walk/loop/", 
                "prefix": "loop_",
                "count": 8,
                "frame_duration": 167,  # 6 FPS (1000ms/6)
                "loops": -1  # 无限循环
            },
            # --- WALK_END (结束行走) 动画 ---
            PetState.WALK_END: {
                "frames_dir": "sprites/walk/end/", 
                "prefix": "end_",
                "count": 5,
                "frame_duration": 250,  
                "loops": 0,  # 播放一次
                "next_state": PetState.IDLE  # 返回空闲状态
            },
            # --- FALL (下坠) 动画 ---
            PetState.FALL: {
                "frames_dir": "sprites/fall/",
                "prefix": "fall_",
                "count": 2,
                "frame_duration": 33,  # 约30FPS，确保平滑的下落动画
                "loops": -1  # 无限循环直到着陆
            },
            # --- FALL_END (结束下落) 动画 ---
            PetState.FALL_END: {
                "frames_dir": "sprites/fall/end/",
                "prefix": "end_",
                "count": 4,
                "frame_duration": 167,  
                "loops": 0,  # 播放一次
                "next_state": PetState.IDLE  # 播放完毕后进入IDLE状态
            },
            # --- CATCH (抓取) 动画 ---
            PetState.CATCH: {
                "frames_dir": "sprites/catch/",
                "prefix": "catch_",
                "count": 2,
                "frame_duration": 167,  # 约6FPS
                "loops": -1  # 无限循环直到释放
            },
            # --- 番茄钟工作状态动画 ---
            PetState.TOMATO_WORKING: {
                "frames_dir": "sprites/tomato/",
                "prefix": "tomato_",
                "count": 4,  # 4个帧：tomato_0.png 到 tomato_3.png
                "frame_duration": 125,  # 8 FPS
                "loops": -1  # 无限循环
            },
            # --- 番茄钟休息过渡动画 ---
            PetState.TOMATO_BREAK: {
                "frames_dir": "sprites/tomato_break/",
                "prefix": "tomato_",
                "count": 8,  # 8个帧：tomato_0.png 到 tomato_7.png
                "frame_duration": 125,  # 8 FPS
                "loops": 0,  # 播放一次
                "next_state": PetState.TOMATO_RESTING  # 过渡到休息状态
            },
            # --- 番茄钟休息状态动画 ---
            PetState.TOMATO_RESTING: {
                "frames_dir": "sprites/break/",
                "prefix": "break_",
                "count": 1,
                "frame_duration": 125,  # 8 FPS
                "loops": -1  # 无限循环
            },
            # --- 番茄钟完成状态动画 ---
            PetState.TOMATO_COMPLETED: {
                "frames_dir": "sprites/happy/loop/",
                "prefix": "loop_",
                "count": 8,
                "frame_duration": 125,  # 8 FPS
                "loops": 10,  # 播放10次
                "next_state": PetState.IDLE  # 播放完后回到IDLE状态
            },
            # --- 从其他状态到番茄钟工作状态的过渡动画 ---
            PetState.IDLE_TO_TOMATO: {
                "frames_dir": "sprites/idle_to_stand/",
                "prefix": "T_",
                "count": 9,
                "frame_duration": 125,  # 8 FPS
                "loops": 0,  # 播放一次
                "next_state": PetState.TOMATO_WORKING  # 过渡到工作状态
            },
            # --- DRINK (喝水) 状态动画 ---
            PetState.DRINK: {
                "frames_dir": "sprites/drink/begin/",  # 开始喝水的动画
                "prefix": "begin_",
                "count": 3,
                "frame_duration": 125,  # 8 FPS
                "loops": 0,  # 播放一次
                "next_state": PetState.DRINK_LOOP
            },
            # --- DRINK_LOOP (喝水循环) 状态动画 ---
            PetState.DRINK_LOOP: {
                "frames_dir": "sprites/drink/loop/",  # 喝水循环动画
                "prefix": "loop_",
                "count": 2,
                "frame_duration": 125,  # 8 FPS
                "loops": -1,  # 无限循环，直到定时器触发切换状态
                "next_state": None  # 不自动切换状态，由定时器控制
            },
            PetState.TOMATO_DRAG: {
                "frames_dir": "sprites/tomato/",
                "prefix": "tomato_",
                "count": 4,
                "frame_duration": 125,
                "loops": -1
            },
            PetState.BREAK_DRAG: {
                "frames_dir": "sprites/break/",
                "prefix": "break_",
                "count": 1,
                "frame_duration": 125,
                "loops": -1
            },
            PetState.HAPPY_DRAG: {
                "frames_dir": "sprites/happy/loop/",
                "prefix": "loop_",
                "count": 8,
                "frame_duration": 125,
                "loops": -1
            }
        }
        
        # Preload all pixmaps
        self.loaded_pixmaps = {}
        for state, config in self.animations_config.items():
            frame_paths = self._generate_frame_paths(config)
            self.loaded_pixmaps[state] = self._load_animation_pixmaps(frame_paths)
            if not self.loaded_pixmaps[state]:
                 print(f"严重警告: 状态 {state} 未能加载任何动画帧! 请检查路径 {config.get('frames_dir','')}{config.get('prefix','')} 和图片文件。")
                 self.loaded_pixmaps[state] = []

        # 动画播放定时器
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._tick_animation) # 定时器触发时调用_tick_animation
        
        # 当前动画播放相关的状态变量
        self.current_animation_pixmaps = []    # 当前播放动画的帧路径列表
        self.current_frame_index = 0          # 当前显示的是第几帧
        self.current_animation_loops_done = 0 # 当前动画已经循环了多少次
        self.current_animation_active_config = {}    # 当前播放动画的配置

        # Default/fallback pixmap (e.g., first frame of IDLE)
        self.default_pixmap = None
        if self.loaded_pixmaps.get(PetState.IDLE) and self.loaded_pixmaps[PetState.IDLE]:
            self.default_pixmap = self.loaded_pixmaps[PetState.IDLE][0]
        else:
            print("严重警告: 无法加载IDLE状态的默认Pixmap (通常是 sprites/idle/idle_0.png)。程序可能无法正常显示初始图像。")
            # Create a tiny blank pixmap as a last resort if even default fails
            self.default_pixmap = QPixmap(1, 1)
            self.default_pixmap.fill(Qt.transparent)

        # 添加行走相关的配置
        self.walk_config = {
            "enabled": False,           # 是否启用自动随机行走
            "walk_chance": 0.3,        # 在空闲状态下开始行走的概率
            "min_walk_time": 5,        # 最短行走时间（秒）
            "max_walk_time": 60,       # 最长行走时间（秒）
            "walk_speed": 5,          # 行走速度（像素/帧）
            "walk_direction": "right",  # 行走方向 ("left" 或 "right")
            "last_walk_time": 0,       # 上次行走的时间戳
            "current_walk_duration": 0, # 当前行走持续时间
            "next_walk_time": 0,       # 下次行走的时间戳
            "walk_cooldown": 5,        # 两次行走之间的最小间隔（秒）
            "is_manual_walking": False  # 是否是手动控制的行走
        }
        
        # 修改下坠相关的配置
        self.fall_config = {
            "enabled": True,           # 是否启用下坠功能
            "platforms": [],           # 平台列表，每个元素是 {"rect": QRect, "type": str} 字典
            "interactive_windows": [],  # 互动窗口列表，每个元素是 {"title": str, "class_name": str} 字典
            "fall_speed": 10,          # 每帧下落的像素数
            "animation_interval": 33    # 下坠动画的更新间隔（毫秒）
        }
        
        # 添加定时器用于检查下坠状态和更新平台
        self.fall_check_timer = QTimer()
        self.fall_check_timer.timeout.connect(self._check_falling)
        self.fall_check_timer.start(self.fall_config["animation_interval"])  # 约30FPS
        
        # 添加定时器用于更新平台位置
        self.platform_update_timer = QTimer()
        self.platform_update_timer.timeout.connect(self._update_platforms)
        self.platform_update_timer.start(1000)  # 每秒更新一次平台位置
        
        # 初始化时获取任务栏位置
        self._update_platforms()
        
        # 创建休息提醒定时器
        self.break_timer = QTimer()
        self.break_timer.timeout.connect(self._check_break_time)
        self.break_timer.start(1000)  # 每秒检查一次
        
        # 番茄钟锁定模式标志
        self.tomato_lock_mode = False
        
        # 提醒队列系统
        self.reminder_queue = []  # 存储待执行的提醒
        self.is_reminder_active = False  # 标记是否有提醒正在显示
        
        self._set_state(initial_state)

    def _generate_frame_paths(self, config):
        """
        内部辅助方法：根据动画配置生成该动画所有帧图片文件的完整路径列表。

        Args:
            config (dict): 特定状态的动画配置字典。

        Returns:
            list: 包含该动画所有帧图片完整路径的列表。
        """
        if not config: return []
        frames_dir = config.get("frames_dir", "")
        prefix = config.get("prefix", "")
        count = config.get("count", 0)
        
        if frames_dir and not frames_dir.endswith('/'):
            frames_dir += '/'
        
        # 假设图片格式为.png, 实际项目中可以考虑将格式也加入配置
        return [f"{frames_dir}{prefix}{i}.png" for i in range(count)]

    def _load_animation_pixmaps(self, frame_paths):
        """
        内部辅助方法：根据提供的帧图片路径列表，加载所有图片为QPixmap对象。

        Args:
            frame_paths (list): 包含待加载图片完整路径的列表。

        Returns:
            list: 包含已加载QPixmap对象的列表。如果某张图片加载失败，会打印警告且不会添加到列表中。
        """
        pixmaps = []
        for path in frame_paths:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                print(f"警告: 无法从路径加载Pixmap: {path}")
            else:
                pixmaps.append(pixmap)
        return pixmaps

    def _check_idle_timeout(self):
        """检查IDLE状态是否超时应该进入睡眠。"""
        current_time = time.time()
        idle_time = current_time - self.state_timestamps["last_interaction"]
        threshold = self.state_transitions[PetState.IDLE]["threshold"]
        should_sleep = idle_time > threshold
        
        if should_sleep:
            print(f"DPet Debug: IDLE超时 {idle_time:.1f}秒 > {threshold}秒，准备进入睡眠状态")
        return should_sleep

    def _check_stand_timeout(self):
        """检查STAND状态是否超时应该返回IDLE。"""
        current_time = time.time()
        stand_time = current_time - self.state_timestamps["last_state_change"]
        threshold = self.state_transitions[PetState.STAND]["threshold"]
        should_return = stand_time > threshold
        
        if should_return:
            print(f"DPet Debug: STAND超时 {stand_time:.1f}秒 > {threshold}秒，准备返回IDLE状态")
        return should_return

    def _handle_tomato_state_change(self, state):
        """根据番茄钟状态切换宠物状态，并处理锁定/解锁和 UI 更新。"""
        if state == TomatoState.WORKING:
            # 工作阶段：进入锁定模式并切换到工作动画
            if not self.tomato_lock_mode:
                self._save_pre_tomato_state()
                self._enter_tomato_lock_mode()
            self._set_state(PetState.TOMATO_WORKING)
        elif state == TomatoState.RESTING:
            # 休息阶段：保持锁定模式并切换到休息动画
            if not self.tomato_lock_mode:
                self._save_pre_tomato_state()
                self._enter_tomato_lock_mode()
            self._set_state(PetState.TOMATO_RESTING)
        elif state in (TomatoState.COMPLETED, TomatoState.IDLE):
            # 完成或重置：解除锁定，切换到对应状态
            self._exit_tomato_lock_mode()
            target = PetState.TOMATO_COMPLETED if state == TomatoState.COMPLETED else PetState.IDLE
            self._set_state(target)
            # 隐藏倒计时和进度窗口
            self.pet_window.hide_tomato_timer()
            self.pet_window.tomato_progress_window.hide()
    
    def _handle_tomato_time_update(self, remaining_time):
        """处理番茄钟时间更新"""
        time_str = self.tomato_timer.get_formatted_time()
        self.pet_window.update_timer_display(time_str)
    
    def _handle_tomato_completed(self):
        """处理单个番茄钟完成"""
        current, total = self.tomato_timer.get_progress()
        self.pet_window.update_progress_display(current, total)
    
    def _handle_all_tomatoes_completed(self):
        """处理所有番茄钟完成"""
        # 播放10秒的happy动画
        self._set_state(PetState.TOMATO_COMPLETED)
    
    def start_tomato_timer(self):
        """开始番茄钟"""
        # 保存当前状态
        self._save_pre_tomato_state()
        
        # 进入番茄钟锁定模式
        self._enter_tomato_lock_mode()
        
        self.tomato_timer.start()
        # 显示倒计时窗口
        self.pet_window.tomato_timer_window.show()
    
    def pause_tomato_timer(self):
        """暂停番茄钟"""
        self.tomato_timer.pause()
    
    def resume_tomato_timer(self):
        """恢复番茄钟"""
        self.tomato_timer.resume()
    
    def reset_tomato_timer(self):
        """重置番茄钟"""
        self.tomato_timer.reset()
        # 隐藏倒计时窗口和进度显示
        self.pet_window.tomato_timer_window.hide()
        self.pet_window.tomato_progress_window.hide()
        
        # 退出番茄钟锁定模式
        self._exit_tomato_lock_mode()
    
    def configure_tomato_timer(self, work_minutes: int, rest_minutes: int, total_tomatoes: int):
        """配置番茄钟参数"""
        self.tomato_timer.configure(work_minutes, rest_minutes, total_tomatoes)
    
    def _set_state(self, new_state):
        """
        核心方法：设置宠物的新状态，并启动/准备与该状态关联的动画。

        Args:
            new_state (PetState): 要转换到的新PetState。
        """
        print(f"DPet Debug: 开始状态转换 {self.current_state} -> {new_state}")
        
        old_state = self.current_state
        self.current_state = new_state
        
        # 如果是FALL_END状态，且在番茄钟模式下，修改next_state为对应的番茄钟状态
        if new_state == PetState.FALL_END and self.tomato_lock_mode:
            if hasattr(self, 'pending_tomato_state'):
                if self.pending_tomato_state == TomatoState.WORKING:
                    next_state = PetState.TOMATO_WORKING
                elif self.pending_tomato_state == TomatoState.RESTING:
                    next_state = PetState.TOMATO_RESTING
                elif self.pending_tomato_state == TomatoState.COMPLETED:
                    next_state = PetState.TOMATO_COMPLETED
                else:
                    next_state = PetState.IDLE
                # 更新动画配置的next_state
                self.animations_config[PetState.FALL_END] = {
                    **self.animations_config[PetState.FALL_END],
                    "next_state": next_state
                }
                delattr(self, 'pending_tomato_state')
        
        # 更新状态改变时间戳
        # 只在真正进入STAND状态时更新时间戳，而不是在过渡动画时
        if new_state == PetState.STAND:
            print("DPet Debug: 进入STAND状态，更新状态时间戳")
            self.state_timestamps["last_state_change"] = time.time()
            
            # 如果随机行走功能开启，重置下次行走时间，使其可以很快再次触发随机行走
            if self.walk_config["enabled"] and not self.tomato_lock_mode:
                print("DPet Debug: 随机行走功能已开启，重置下次行走时间")
                # 设置一个短暂的延迟（3秒）后可以再次触发随机行走
                self.walk_config["next_walk_time"] = time.time() + 3
            
            # 如果音乐正在播放，立即转换到跳舞状态
            if self.is_music_playing:
                print("DPet Debug: 音乐正在播放，继续转换到跳舞状态")
                self._set_state(PetState.STAND_TO_DANCE)
                return
        
        # 如果从AWAKENING转换到IDLE，且音乐正在播放，继续转换到站立状态
        if old_state == PetState.AWAKENING and new_state == PetState.IDLE and self.is_music_playing:
            print("DPet Debug: 从睡眠唤醒后检测到音乐正在播放，继续转换到站立状态")
            self._set_state(PetState.IDLE_TO_STAND)
            return
        
        # 某些状态改变也视为交互
        if new_state in [PetState.IDLE, PetState.STAND]:
            self.state_timestamps["last_interaction"] = time.time()
            
        self.animation_timer.stop()

        # 获取新状态的动画配置
        pixmaps_for_state = self.loaded_pixmaps.get(new_state)
        current_config = self.animations_config.get(new_state)

        if not pixmaps_for_state or not current_config:
            print(f"DPet Debug: 警告 - 状态 {new_state} 没有找到预加载的Pixmaps或有效的动画配置")
            self.pet_window.update_image_pixmap(self.default_pixmap)
            return

        # 获取当前状态的动画配置
        self.current_animation_active_config = current_config
        
        # 准备动画帧序列
        current_pixmap_sequence = list(pixmaps_for_state)
        if self.current_animation_active_config.get("reverse_playback", False):
            current_pixmap_sequence.reverse()
        
        self.current_animation_pixmaps = current_pixmap_sequence
        self.current_frame_index = 0
        self.current_animation_loops_done = 0
        
        if self.current_animation_pixmaps:
            print(f"DPet Debug: 更新显示图像 - 状态: {new_state}, 帧数: {len(self.current_animation_pixmaps)}")
            self.pet_window.update_image_pixmap(self.current_animation_pixmaps[0])
        else:
            print(f"DPet Debug: 错误 - 状态 {new_state} 的动画帧列表为空")
            self.pet_window.update_image_pixmap(self.default_pixmap)
            return

        # 如果有多个帧且设置了帧持续时间，或者是下坠状态，启动动画
        if (len(self.current_animation_pixmaps) > 1 and self.current_animation_active_config.get("frame_duration", 0) > 0) or new_state == PetState.FALL:
            frame_duration = self.current_animation_active_config.get("frame_duration", 33)  # 默认33ms
            print(f"DPet Debug: 启动动画定时器 - 帧间隔: {frame_duration}ms")
            self.animation_timer.start(frame_duration)
            
        # 如果是过渡动画完成后需要切换到下一个状态
        elif self.current_animation_active_config.get("next_state") and self.current_animation_active_config.get("loops", -1) == 0:
            next_state = self.current_animation_active_config["next_state"]
            print(f"DPet Debug: 过渡动画完成，准备切换到下一个状态: {next_state}")
            self._set_state(next_state)

        # 如果是番茄钟完成状态，播放10次后回到IDLE
        if new_state == PetState.TOMATO_COMPLETED:
            self.current_animation_active_config = {
                **self.animations_config[new_state],
                "next_state": PetState.IDLE
            }

    def _tick_animation(self):
        """动画定时器的回调函数。处理帧的切换、循环逻辑，以及在动画播放完成后的状态转换。"""
        if not self.current_animation_pixmaps:  # 安全检查: 如果当前没有动画帧，则停止定时器
            self.animation_timer.stop()
            return

        # 如果是下坠状态，每帧更新位置
        if self.current_state == PetState.FALL:
            current_pos = self.pet_window.pos()
            window_size = self.pet_window.size()
            new_y = current_pos.y() + self.fall_config["fall_speed"]  # 使用配置的下落速度
            
            # 检查是否会落到平台上
            landed = False
            landing_y = new_y
            
            # 检查所有平台（包括任务栏和互动窗口）
            for platform in self.fall_config["platforms"]:
                platform_rect = platform["rect"]
                # 检查是否会碰到平台
                if (new_y + window_size.height() >= platform_rect.y() and
                        current_pos.y() + window_size.height() < platform_rect.y() and
                        current_pos.x() + window_size.width() > platform_rect.x() and
                        current_pos.x() < platform_rect.x() + platform_rect.width()):
                    # 落到平台上，精确对齐到平台顶部
                    print(f"落在{platform['type']}平台上，位置: {platform_rect.y()}")
                    landed = True
                    landing_y = platform_rect.y() - window_size.height()
                    break
            
            # 更新位置
            if landed:
                self.pet_window.move(current_pos.x(), landing_y)
                # 番茄钟模式下直接恢复到对应状态
                if self.tomato_lock_mode:
                    self._handle_tomato_fall_end()
                else:
                    self._set_state(PetState.FALL_END)
                return
            
            # 检查是否到达屏幕底部
            screen = QApplication.primaryScreen().geometry()
            if new_y + window_size.height() > screen.height():
                new_y = screen.height() - window_size.height()
                self.pet_window.move(current_pos.x(), new_y)
                # 番茄钟模式下直接恢复到对应状态
                if self.tomato_lock_mode:
                    self._handle_tomato_fall_end()
                else:
                    self._set_state(PetState.FALL_END)
                return
            
            # 继续下落
            self.pet_window.move(current_pos.x(), new_y)
            return
        
        # 更新动画帧
        self.current_frame_index += 1
        if self.current_frame_index >= len(self.current_animation_pixmaps):
            # 一轮动画播放完成
            self.current_frame_index = 0
            self.current_animation_loops_done += 1
            
            # 检查是否需要继续播放
            max_loops = self.current_animation_active_config.get("loops", -1)
            if max_loops >= 0 and self.current_animation_loops_done >= max_loops:
                # 动画播放完成，检查是否需要切换到下一个状态
                next_state = self.current_animation_active_config.get("next_state")
                if next_state:
                    self._set_state(next_state)
                    return
                else:
                    # 没有下一个状态，停止动画
                    self.animation_timer.stop()
                    return
        
        # 更新显示的帧
        flip_horizontal = self.current_animation_active_config.get("flip_horizontal", False)
        # 如果是行走状态，根据方向决定是否翻转
        if self.current_state in [PetState.WALK, PetState.WALK_BEGIN, PetState.WALK_END]:
            flip_horizontal = self.walk_config["walk_direction"] == "left"
            
            # 如果是行走状态，在每帧更新时移动位置
            if self.current_state == PetState.WALK:
                current_pos = self.pet_window.pos()
                move_distance = self.walk_config["walk_speed"]
                if self.walk_config["walk_direction"] == "left":
                    move_distance = -move_distance
                new_x = current_pos.x() + move_distance
                
                # 检查是否到达屏幕边界
                screen = QApplication.primaryScreen().geometry()
                if ((self.walk_config["walk_direction"] == "right" and 
                     new_x > screen.width() - self.pet_window.width()) or
                    (self.walk_config["walk_direction"] == "left" and new_x < 0)):
                    self._set_state(PetState.WALK_END)
                    return
                
                self.pet_window.move(new_x, current_pos.y())
        
        self.pet_window.update_image_pixmap(
            self.current_animation_pixmaps[self.current_frame_index],
            flip_horizontal
        )

    def handle_mouse_press(self, event):
        """
        处理鼠标按下事件。
        """
        if self.tomato_lock_mode and event.button() != Qt.RightButton:
            # 只允许拖拽
            if event.button() == Qt.LeftButton:
                # 拖拽区域判断
                click_pos = event.pos()
                window_height = self.pet_window.height()
                drag_area_height = window_height - 20
                catch_zone_end = window_height * 0.60
                if click_pos.y() < catch_zone_end:
                    # 番茄钟模式下统一使用CATCH动画
                    self._set_state(PetState.CATCH)
                return
            else:
                return

        # 更新最后交互时间
        self.state_timestamps["last_interaction"] = time.time()
        
        # 获取点击位置和窗口信息
        click_pos = event.pos()
        window_height = self.pet_window.height()
        drag_area_height = window_height - 20  # 底部20像素是透明区域
        
        # 计算拖动位置（用于实际移动窗口）
        self.drag_position = event.globalPos() - self.pet_window.frameGeometry().topLeft()

        # 如果在下落状态，只允许触发抓取
        if self.current_state == PetState.FALL:
            if click_pos.y() < drag_area_height:  # 点击非透明区域
                self._set_state(PetState.CATCH)
            return

        # 计算分界线位置（窗口高度的60%处）
        catch_zone_end = window_height * 0.60

        # 判断点击区域并触发相应状态
        if click_pos.y() >= drag_area_height:
            # 点击透明区域，不做任何响应
            return
        elif click_pos.y() < catch_zone_end:
            # 上部分（0 ~ 60%）触发抓取状态
            self._set_state(PetState.CATCH)
        else:
            # 下部分（60% ~ 底部）触发站立相关状态
            if self.current_state == PetState.SLEEP:
                self._set_state(PetState.AWAKENING)     # 睡眠 -> 唤醒 -> 空闲
            elif self.current_state == PetState.IDLE:
                self._set_state(PetState.IDLE_TO_STAND) # 空闲 -> 站立
            elif self.current_state == PetState.STAND:
                self._set_state(PetState.STAND_TO_IDLE) # 站立 -> 空闲
            elif self.current_state in [PetState.WALK, PetState.WALK_BEGIN]:
                self._set_state(PetState.WALK_END)      # 行走 -> 停止 -> 空闲

    def handle_mouse_move(self, event):
        """
        处理来自PetDisplay的鼠标移动事件，用于实现窗口拖动功能。

        Args:
            event (QMouseEvent): 鼠标事件对象。
        """
        if event.buttons() & Qt.LeftButton:  # 如果鼠标左键被按下并移动
            self.state_timestamps["last_interaction"] = time.time()  # 拖动也算作用户交互，防止拖动时睡着
            # 移动窗口到新的位置 (鼠标当前全局位置 - 拖动起始时鼠标在窗口内的偏移)
            self.pet_window.move(event.globalPos() - self.drag_position)

    def handle_mouse_release(self, event):
        """
        处理鼠标释放事件。
        """
        if self.tomato_lock_mode:
            # 拖拽释放后恢复到番茄钟原状态
            if event.button() == Qt.LeftButton and self.current_state == PetState.CATCH:
                # 先检查是否需要下落 - 这里只检查物理下落，无需区分互动窗口
                if self._check_falling():
                    # 如果需要下落，设置一个标记，在下落结束后恢复番茄钟状态
                    self.pending_tomato_state = self.tomato_timer.state
                else:
                    # 不需要下落，直接恢复番茄钟状态
                    if self.tomato_timer.state == TomatoState.WORKING:
                        self._set_state(PetState.TOMATO_WORKING)
                    elif self.tomato_timer.state == TomatoState.RESTING:
                        self._set_state(PetState.TOMATO_RESTING)
                    elif self.tomato_timer.state == TomatoState.COMPLETED:
                        self._set_state(PetState.TOMATO_COMPLETED)
                    else:
                        self._set_state(PetState.IDLE)
            return

        if event.button() == Qt.LeftButton and self.current_state == PetState.CATCH:
            print("从CATCH状态释放，检查下落和音乐状态")
            # 更新状态时间戳
            self.state_timestamps["last_interaction"] = time.time()
            
            # 检查是否需要下落
            if self._check_falling():
                # 如果需要下落，不执行其他状态转换
                return
            
            # 检查当前窗口是否是最顶层窗口 - 这部分现在是多余的，因为平台列表已经只包含最顶层窗口
            # 但保留这段代码可以增加程序的健壮性
            current_pos = self.pet_window.pos()
            window_size = self.pet_window.size()
            is_on_platform, platform = self._is_on_platform(
                current_pos.x(), current_pos.y(),
                window_size.width(), window_size.height()
            )
            
            # 如果在平台上但不是最顶层窗口，不触发交互（回到IDLE状态）
            if is_on_platform and platform.get("type") == "window" and not platform.get("is_top_window", False):
                print(f"释放在非最顶层窗口上: {platform.get('title')}, 不触发音乐交互")
                self._set_state(PetState.IDLE)
                return
            
            # 检查音乐是否在播放
            if self.music_detection_enabled and self.is_music_playing:
                print("DPet Debug: 拖拽结束后检测到音乐仍在播放，恢复跳舞状态")
                # 从IDLE开始转换到跳舞状态
                self._set_state(PetState.IDLE_TO_STAND)
            else:
                # 没有音乐播放，恢复到IDLE状态
                self._set_state(PetState.IDLE)

    def handle_mouse_press_at(self, x, y):
        """
        在指定位置处理鼠标按下事件（用于手势控制）。
        
        Args:
            x (int): 屏幕X坐标
            y (int): 屏幕Y坐标
        """
        # 将屏幕坐标转换为窗口相对坐标
        window_pos = self.pet_window.pos()
        window_size = self.pet_window.size()
        
        # 检查点击是否在窗口范围内
        if (window_pos.x() <= x <= window_pos.x() + window_size.width() and
            window_pos.y() <= y <= window_pos.y() + window_size.height()):
            # 转换为窗口相对坐标
            relative_x = x - window_pos.x()
            relative_y = y - window_pos.y()
            
            # 更新拖动位置
            self.drag_position = QPoint(relative_x, relative_y)
            
            # 更新最后交互时间
            self.state_timestamps["last_interaction"] = time.time()
            
            # 检查当前所在平台
            is_on_platform, platform = self._is_on_platform(
                window_pos.x(), window_pos.y(),
                window_size.width(), window_size.height()
            )
            
            # 如果在平台上，检查是否是可交互平台（最顶层窗口或任务栏）
            if is_on_platform:
                platform_type = platform.get("type")
                is_top_window = platform.get("is_top_window", False)
                
                # 如果不是最顶层窗口且不是任务栏，不触发交互
                if platform_type == "window" and not is_top_window:
                    print(f"当前在非最顶层窗口上: {platform.get('title')}, 不触发交互")
                    return
            
            # 处理状态转换
            if self.current_state == PetState.FALL:
                self._set_state(PetState.CATCH)
            else:
                # 计算点击区域
                catch_zone_end = window_size.height() * 0.60
                drag_area_height = window_size.height() - 20
                
                if relative_y >= drag_area_height:
                    # 点击透明区域，不做任何响应
                    return
                elif relative_y < catch_zone_end:
                    # 上部分（0 ~ 60%）触发抓取状态
                    self._set_state(PetState.CATCH)
                else:
                    # 下部分（60% ~ 底部）触发站立相关状态
                    if self.current_state == PetState.SLEEP:
                        self._set_state(PetState.AWAKENING)
                    elif self.current_state == PetState.IDLE:
                        self._set_state(PetState.IDLE_TO_STAND)
                    elif self.current_state == PetState.STAND:
                        self._set_state(PetState.STAND_TO_IDLE)
                    elif self.current_state in [PetState.WALK, PetState.WALK_BEGIN]:
                        self._set_state(PetState.WALK_END)

    def check_state_transitions(self):
        """
        检查并执行基于时间的状态自动转换。
        包括检查下落、音乐状态、随机行走等。
        """
        # 如果正在下落，不执行任何状态转换
        if self.current_state == PetState.FALL:
            return
            
        # 获取当前状态的转换配置
        transition = self.state_transitions.get(self.current_state)
        
        # 检查音乐状态，如果音乐在播放但不在跳舞状态，尝试恢复跳舞
        # 排除不应该打断的状态
        excluded_states = [PetState.FALL, PetState.CATCH, 
                          PetState.TOMATO_WORKING, PetState.TOMATO_RESTING, PetState.TOMATO_BREAK,
                          PetState.BREAK, PetState.DRINK, PetState.DRINK_LOOP,
                          PetState.DANCE, PetState.STAND_TO_DANCE, PetState.IDLE_TO_STAND]
        
        if self.music_detection_enabled and self.is_music_playing and self.current_state not in excluded_states:
            print("DPet Debug: 检测到音乐仍在播放，尝试恢复跳舞状态")
            if self.current_state == PetState.STAND:
                self._set_state(PetState.STAND_TO_DANCE)
                return
            elif self.current_state == PetState.IDLE:
                self._set_state(PetState.IDLE_TO_STAND)
                return
            elif self.current_state in [PetState.WALK, PetState.WALK_BEGIN, PetState.WALK_END]:
                print("DPet Debug: 打断行走状态，开始跳舞")
                self._set_state(PetState.STAND_TO_DANCE)
                return
        
        # 检查下落状态
        self._check_falling()
        
        # 只在非手动行走状态下处理随机行走
        if not self.walk_config["is_manual_walking"]:
            # 处理随机行走状态
            if self.walk_config["enabled"] and (self.current_state in [PetState.IDLE, PetState.SLEEP]):
                current_time = time.time()
                # 检查是否已经过了冷却时间
                if current_time >= self.walk_config["next_walk_time"]:
                    # 如果达到行走概率，开始行走
                    if random.random() < self.walk_config["walk_chance"]:
                        # 如果当前是睡眠状态，需要先唤醒
                        if self.current_state == PetState.SLEEP:
                            print("从睡眠状态唤醒以开始随机行走")
                            self._set_state(PetState.AWAKENING)
                            return
                            
                        # 随机选择方向
                        direction = random.choice(["left", "right"])
                        # 设置随机行走持续时间
                        duration = random.uniform(
                            self.walk_config["min_walk_time"],
                            self.walk_config["max_walk_time"]
                        )
                        self.walk_config["current_walk_duration"] = duration
                        self.walk_config["last_walk_time"] = current_time
                        self.walk_config["walk_direction"] = direction
                        self.walk_config["is_manual_walking"] = False
                        print(f"开始随机行走，方向：{direction}，持续时间：{duration:.1f}秒")
                        self._set_state(PetState.WALK_BEGIN)
                        return
            
            # 如果正在随机行走，检查是否需要停止
            elif self.current_state == PetState.WALK and not self.walk_config["is_manual_walking"]:
                current_time = time.time()
                walk_time = current_time - self.walk_config["last_walk_time"]
                
                # 如果超过行走持续时间，停止行走
                if walk_time >= self.walk_config["current_walk_duration"]:
                    print(f"随机行走结束，已行走：{walk_time:.1f}秒")
                    self.stop_walking()
                    return
        
        # 处理其他状态转换
        if transition and transition["check"]():
            self._set_state(transition["next_state"])

        # 检查是否需要提醒喝水
        self._check_water_time()

    def check_sleep(self):
        """
        @deprecated: 请使用 check_state_transitions() 方法代替。
        此方法为保持与main.py的兼容性而保留。
        
        Note:
            此方法由main.py中的定时器调用，
            作为状态检测系统的入口点。
        """
        self.check_state_transitions() 

    def update_music_state(self, is_playing):
        """
        更新音乐播放状态，并根据状态改变触发相应的动画。

        状态转换序列：
        1. 当音乐开始播放时：
           - 如果当前是 IDLE: IDLE -> IDLE_TO_STAND -> STAND -> STAND_TO_DANCE -> DANCE
           - 如果当前是 SLEEP: SLEEP -> AWAKENING -> IDLE -> IDLE_TO_STAND -> STAND -> STAND_TO_DANCE -> DANCE
           - 如果当前是 STAND: STAND -> STAND_TO_DANCE -> DANCE
           - 如果当前是 WALK/WALK_BEGIN/WALK_END: 立即转换到 STAND_TO_DANCE
        2. 当音乐停止时：
           - DANCE -> DANCE_TO_STAND -> STAND

        Args:
            is_playing (bool): 音乐是否正在播放
        """
        # 如果音乐检测功能已关闭，不执行任何状态转换
        if not self.music_detection_enabled:
            return
            
        # 如果正在下落或拖拽状态，只更新状态标志，不执行状态转换
        if self.current_state in [PetState.FALL, PetState.CATCH]:
            self.is_music_playing = is_playing
            return
        
        # 定义不应该被音乐状态改变打断的状态列表
        excluded_states = [PetState.TOMATO_WORKING, PetState.TOMATO_BREAK, PetState.TOMATO_RESTING,
                          PetState.BREAK, PetState.DRINK, PetState.DRINK_LOOP]
            
        # 更新音乐播放状态标志
        self.is_music_playing = is_playing
        
        if is_playing:
            # 音乐开始播放，根据当前状态执行不同的转换序列
            if self.current_state not in excluded_states:
                if self.current_state == PetState.IDLE:
                    print("DPet Debug: 检测到音乐播放，从IDLE开始转换")
                    self._set_state(PetState.IDLE_TO_STAND)
                elif self.current_state == PetState.SLEEP:
                    print("DPet Debug: 检测到音乐播放，从SLEEP开始转换")
                    self._set_state(PetState.AWAKENING)
                elif self.current_state == PetState.STAND:
                    print("DPet Debug: 检测到音乐播放，从STAND开始转换")
                    self._set_state(PetState.STAND_TO_DANCE)
                elif self.current_state in [PetState.WALK, PetState.WALK_BEGIN, PetState.WALK_END]:
                    print("DPet Debug: 检测到音乐播放，打断行走状态")
                    self._set_state(PetState.STAND_TO_DANCE)
        else:
            # 音乐停止，返回站立状态
            if self.current_state == PetState.DANCE:
                print("DPet Debug: 音乐停止，结束跳舞")
                # 如果随机行走功能开启，重置下次行走时间，使其可以很快再次触发随机行走
                if self.walk_config["enabled"] and not self.tomato_lock_mode:
                    print("DPet Debug: 随机行走功能已开启，重置下次行走时间")
                    # 设置一个短暂的延迟（3秒）后可以再次触发随机行走
                    self.walk_config["next_walk_time"] = time.time() + 3
                self._set_state(PetState.DANCE_TO_STAND)

    def set_walk_enabled(self, enabled: bool):
        """启用或禁用自动行走功能"""
        self.walk_config["enabled"] = enabled
        print(f"自动行走功能已{'启用' if enabled else '禁用'}")

    def set_walk_chance(self, chance: float):
        """设置行走概率（0.0-1.0）"""
        self.walk_config["walk_chance"] = max(0.0, min(1.0, chance))
        print(f"行走概率已设置为: {chance:.2f}")

    def set_walk_duration_range(self, min_time: float, max_time: float):
        """设置行走持续时间范围（秒）"""
        self.walk_config["min_walk_time"] = max(1.0, min_time)
        self.walk_config["max_walk_time"] = max(min_time, max_time)
        print(f"行走持续时间范围已设置为: {min_time:.1f}s - {max_time:.1f}s")

    def set_music_detection_enabled(self, enabled: bool):
        """启用或禁用音乐检测功能"""
        self.music_detection_enabled = enabled  # 保存音乐检测状态
        # 如果在 main.py 创建了 music_detector 并传递给了 pet_window，则通过 pet_window 访问
        # 这样就不需要直接在 PetInteraction 中保存 music_detector 的引用
        # 在 main.py 中 music_detector 是 DPet 类的成员而不是 PetInteraction 的成员
        if hasattr(self.pet_window, 'music_detector'):
            if enabled:
                self.pet_window.music_detector.start()
            else:
                self.pet_window.music_detector.stop()
                # 如果正在跳舞，停止跳舞
                if self.current_state == PetState.DANCE:
                    self._set_state(PetState.DANCE_TO_STAND)
        print(f"音乐检测功能已{'启用' if enabled else '禁用'}")

    def set_walk_direction(self, direction: str):
        """手动控制行走方向
        
        Args:
            direction (str): 行走方向 ("left" 或 "right")
        """
        print(f"设置行走方向: {direction}")
        
        # 如果在番茄钟锁定模式下，不允许手动行走
        if self.tomato_lock_mode:
            print("番茄钟模式下不允许手动行走")
            return
            
        current_time = time.time()
        
        # 如果在冷却时间内，不开始新的行走
        if current_time < self.walk_config["next_walk_time"]:
            print(f"行走冷却中，还需等待 {self.walk_config['next_walk_time'] - current_time:.1f} 秒")
            return
            
        # 如果当前已经在行走，只改变方向
        if self.current_state == PetState.WALK:
            self.walk_config["walk_direction"] = direction
            self.walk_config["is_manual_walking"] = True
            print(f"改变行走方向为: {direction}")
            return
            
        # 如果当前是可以开始行走的状态
        if self.current_state in [PetState.IDLE, PetState.STAND]:
            print(f"开始向{direction}行走")
            self.walk_config["walk_direction"] = direction
            self.walk_config["is_manual_walking"] = True
            self.walk_config["last_walk_time"] = current_time
            self._set_state(PetState.WALK_BEGIN)
        else:
            print(f"当前状态 {self.current_state} 不能开始行走")

    def stop_walking(self):
        """停止行走"""
        print("尝试停止行走")
        if self.current_state in [PetState.WALK, PetState.WALK_BEGIN]:
            print("执行停止行走")
            self._set_state(PetState.WALK_END)
            # 设置下次行走的时间
            self.walk_config["next_walk_time"] = time.time() + self.walk_config["walk_cooldown"]
            self.walk_config["is_manual_walking"] = False
        else:
            print(f"当前状态 {self.current_state} 不是行走状态，无需停止")

    def start_walking(self, direction: str):
        """开始行走"""
        print(f"开始向{direction}行走")
        self.walk_config["walk_direction"] = direction
        self.walk_config["is_manual_walking"] = True
        self.walk_config["last_walk_time"] = time.time()
        self._set_state(PetState.WALK_BEGIN)

    def set_walk_speed(self, speed: int):
        """设置行走速度（像素/帧）"""
        self.walk_config["walk_speed"] = max(1, speed)
        print(f"行走速度已设置为: {speed} 像素/帧")

    def set_walk_cooldown(self, cooldown: int):
        """设置两次行走之间的最小间隔（秒）"""
        self.walk_config["walk_cooldown"] = max(1, cooldown)
        print(f"两次行走之间的最小间隔已设置为: {cooldown} 秒")

    def set_walk_chance(self, chance: float):
        """设置行走概率（0.0-1.0）"""
        self.walk_config["walk_chance"] = max(0.0, min(1.0, chance))
        print(f"行走概率已设置为: {chance:.2f}")

    def set_walk_duration_range(self, min_time: float, max_time: float):
        """设置行走持续时间范围（秒）"""
        self.walk_config["min_walk_time"] = max(1.0, min_time)
        self.walk_config["max_walk_time"] = max(min_time, max_time)
        print(f"行走持续时间范围已设置为: {min_time:.1f}s - {max_time:.1f}s")

    def set_music_detection_enabled(self, enabled: bool):
        """启用或禁用音乐检测功能"""
        self.music_detection_enabled = enabled  # 保存音乐检测状态
        # 如果在 main.py 创建了 music_detector 并传递给了 pet_window，则通过 pet_window 访问
        # 这样就不需要直接在 PetInteraction 中保存 music_detector 的引用
        # 在 main.py 中 music_detector 是 DPet 类的成员而不是 PetInteraction 的成员
        if hasattr(self.pet_window, 'music_detector'):
            if enabled:
                self.pet_window.music_detector.start()
            else:
                self.pet_window.music_detector.stop()
                # 如果正在跳舞，停止跳舞
                if self.current_state == PetState.DANCE:
                    self._set_state(PetState.DANCE_TO_STAND)
        print(f"音乐检测功能已{'启用' if enabled else '禁用'}")

    def _update_platforms(self):
        """更新平台列表，只包含最顶层的可交互窗口和任务栏"""
        # 清空当前平台列表
        self.fall_config["platforms"].clear()
        
        # 获取任务栏位置（作为默认平台）
        taskbar_rect = self._get_taskbar_geometry()
        if taskbar_rect:
            self.fall_config["platforms"].append({
                "rect": taskbar_rect,
                "type": "taskbar",
                "is_top_window": False  # 任务栏不是互动窗口
            })

        # 获取所有窗口的Z序（从顶层到底层）
        z_order_windows = []
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                windows.append(hwnd)
            return True
        win32gui.EnumWindows(enum_windows_callback, z_order_windows)

        # 只查找最顶层的可交互窗口
        top_interactive_window = None
        top_window_found = False
        
        for hwnd in z_order_windows:
            window_title = win32gui.GetWindowText(hwnd)
            
            # 检查这个窗口是否在我们的互动窗口列表中
            for interactive_window in self.fall_config["interactive_windows"]:
                if interactive_window["title"].lower() in window_title.lower():
                    # 尝试获取窗口位置
                    try:
                        rect = win32gui.GetWindowRect(hwnd)
                        if rect[2] - rect[0] > 50 and rect[3] - rect[1] > 50:  # 确保窗口足够大
                            top_interactive_window = {
                                "rect": QRect(rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]),
                                "type": "window",
                                "title": window_title,
                                "is_top_window": True  # 这是最顶层窗口
                            }
                            print(f"找到最顶层互动窗口: {window_title}")
                            top_window_found = True
                            break  # 找到最顶层交互窗口后立即退出
                    except Exception as e:
                        print(f"获取窗口位置时出错: {str(e)}")
            
            # 如果找到了最顶层的可交互窗口，就不需要继续查找了
            if top_window_found:
                break
        
        # 只添加最顶层的互动窗口到平台列表
        if top_interactive_window:
            self.fall_config["platforms"].append(top_interactive_window)
        
        # 打印平台信息
        platform_info = "\n".join([f"{i}: {p['title'] if 'title' in p else p['type']} (最顶层: {p.get('is_top_window', False)})" 
                                   for i, p in enumerate(self.fall_config["platforms"])])
        print(f"当前平台列表:\n{platform_info}")
        
        # 获取并打印最顶层窗口信息（无论是否可交互）
        if z_order_windows:
            top_window_title = win32gui.GetWindowText(z_order_windows[0])
            print(f"当前最顶层窗口: {top_window_title}")
            is_interactive = top_window_found
            print(f"最顶层窗口是否可交互: {is_interactive}")
        
        # 确保至少有一个平台
        if not self.fall_config["platforms"]:
            # 如果没有平台，使用屏幕底部作为默认平台
            screen = QApplication.primaryScreen().geometry()
            self.fall_config["platforms"].append({
                "rect": QRect(0, screen.height() - 10, screen.width(), 10),
                "type": "default_bottom",
                "is_top_window": False
            })

    def _is_on_platform(self, pos_x, pos_y, width, height):
        """
        检查给定位置是否在任何平台上
        
        Args:
            pos_x (int): 位置X坐标
            pos_y (int): 位置Y坐标
            width (int): 宽度
            height (int): 高度
            
        Returns:
            bool: 如果在平台上返回True，否则返回False
            dict: 如果在平台上，返回该平台信息，否则返回None
        """
        tolerance = 5  # 增加5像素的容差值
        
        for platform in self.fall_config["platforms"]:
            platform_rect = platform["rect"]
            # 使用容差值进行检测
            if (abs(platform_rect.y() - (pos_y + height)) <= tolerance and
                pos_x + width > platform_rect.x() and 
                pos_x < platform_rect.x() + platform_rect.width()):
                return True, platform
        return False, None

    def _find_landing_platform(self, pos_x, pos_y, width, height):
        """
        寻找下方最近的平台
        
        Args:
            pos_x (int): 位置X坐标
            pos_y (int): 位置Y坐标
            width (int): 宽度
            height (int): 高度
            
        Returns:
            dict: 找到的平台信息，如果没找到则返回None
        """
        nearest_platform = None
        nearest_distance = float('inf')
        
        for platform in self.fall_config["platforms"]:
            platform_rect = platform["rect"]
            # 只检查在桌宠下方的平台
            if (platform_rect.y() > pos_y + height and
                pos_x + width > platform_rect.x() and
                pos_x < platform_rect.x() + platform_rect.width()):
                distance = platform_rect.y() - (pos_y + height)
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_platform = platform
        
        return nearest_platform

    def _check_falling(self):
        """
        检查是否需要开始下坠或更新下坠状态
            
        Returns:
            bool: 如果需要下落返回True，否则返回False
        """
        if not self.fall_config["enabled"]:
            return False
            
        current_pos = self.pet_window.pos()
        window_size = self.pet_window.size()
        
        # 检查是否在平台上
        is_on_platform, platform = self._is_on_platform(
            current_pos.x(), current_pos.y(),
            window_size.width(), window_size.height()
        )
        
        # 如果当前是下坠状态且检测到平台
        if self.current_state == PetState.FALL and is_on_platform:
            print(f"检测到平台: {platform.get('title', platform.get('type'))}, 播放落地动画")
            # 番茄钟模式下的下落结束处理
            if self.tomato_lock_mode:
                self._handle_tomato_fall_end()
            else:
                # 普通模式下的下落结束处理
                self._set_state(PetState.FALL_END)
            return False
            
        # 如果不在平台上且不是抓取状态，开始下坠
        # 注意：现在允许从任何状态（除了CATCH）转换到FALL
        if not is_on_platform and self.current_state != PetState.CATCH:
            # 排除过渡动画状态
            transition_states = [
                PetState.STAND_TO_IDLE,
                PetState.WALK_END,
                PetState.DANCE_TO_STAND,
                PetState.AWAKENING,
                PetState.FALL_END
            ]
            
            if self.current_state not in transition_states:
                print(f"从{self.current_state}状态检测到没有平台，开始下坠")
                self._set_state(PetState.FALL)
                return True
        return False

    def _handle_tomato_fall_end(self):
        """处理番茄钟模式下的落地结束状态"""
        if hasattr(self, 'tomato_timer'):
            if self.tomato_timer.state == TomatoState.WORKING:
                self._set_state(PetState.TOMATO_WORKING)
            elif self.tomato_timer.state == TomatoState.RESTING:
                self._set_state(PetState.TOMATO_RESTING)
            elif self.tomato_timer.state == TomatoState.COMPLETED:
                self._set_state(PetState.TOMATO_COMPLETED)
            else:
                self._set_state(PetState.IDLE)

    def add_interactive_window(self, title, class_name):
        """添加一个新的互动窗口"""
        self.fall_config["interactive_windows"].append({
            "title": title,
            "class_name": class_name
        })
        self._update_platforms()
        print(f"添加互动窗口: {title}")

    def remove_interactive_window(self, title):
        """移除一个互动窗口"""
        self.fall_config["interactive_windows"] = [
            w for w in self.fall_config["interactive_windows"]
            if w["title"] != title
        ]
        self._update_platforms()
        print(f"移除互动窗口: {title}")

    def _get_taskbar_geometry(self):
        """获取任务栏的位置和大小"""
        try:
            # 查找任务栏窗口
            taskbar_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
            if taskbar_hwnd:
                # 获取任务栏矩形
                rect = win32gui.GetWindowRect(taskbar_hwnd)
                print(f"找到任务栏原始位置: {rect}")
                
                # 获取任务栏实际可见区域
                visible_rect = win32gui.GetClientRect(taskbar_hwnd)
                print(f"任务栏可见区域: {visible_rect}")
                
                # 使用实际的任务栏高度
                taskbar_height = visible_rect[3]  # 使用可见区域的高度
                screen = QApplication.primaryScreen().geometry()
                
                # 创建正确的任务栏矩形（在屏幕底部）
                taskbar_rect = QRect(
                    0,  # x 坐标始终从0开始
                    screen.height() - taskbar_height,  # y 坐标是屏幕高度减去任务栏高度
                    screen.width(),  # 宽度是整个屏幕宽度
                    taskbar_height  # 高度是任务栏实际高度
                )
                
                print(f"调整后的任务栏位置: {taskbar_rect.x()}, {taskbar_rect.y()}, {taskbar_rect.width()}, {taskbar_rect.height()}")
                return taskbar_rect
        except Exception as e:
            print(f"获取任务栏位置时出错: {str(e)}")
        
        # 如果获取失败，使用屏幕底部的固定区域作为后备方案
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            taskbar_height = 40  # 假设任务栏高度为40像素
            return QRect(
                screen_geometry.x(),
                screen_geometry.y() + screen_geometry.height() - taskbar_height,
                screen_geometry.width(),
                taskbar_height
            )
        return None

    def _find_window_geometry(self, title, class_name):
        """查找指定窗口的位置和大小，只返回顶层窗口"""
        found_windows = []
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and not win32gui.GetParent(hwnd):  # 只选择顶层窗口
                window_title = win32gui.GetWindowText(hwnd)
                window_class = win32gui.GetClassName(hwnd)
                # 使用部分匹配而不是完全匹配
                if (title.lower() in window_title.lower() or 
                    (class_name != "*" and class_name.lower() in window_class.lower())):
                    try:
                        # 获取窗口矩形
                        rect = win32gui.GetWindowRect(hwnd)
                        # 转换为QRect并添加到列表
                        windows.append(QRect(rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]))
                        print(f"找到顶层窗口: {window_title} ({window_class}) at {rect}")
                    except Exception as e:
                        print(f"获取窗口位置时出错: {str(e)}")
            return True
        
        try:
            win32gui.EnumWindows(callback, found_windows)
        except Exception as e:
            print(f"枚举窗口时出错: {str(e)}")
        
        return found_windows

    def list_visible_windows(self):
        """列出所有可见的顶层窗口，返回窗口标题列表"""
        visible_windows = []
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and not win32gui.GetParent(hwnd):  # 只选择顶层窗口
                title = win32gui.GetWindowText(hwnd)
                if title and not title.isspace():  # 排除空标题窗口
                    try:
                        rect = win32gui.GetWindowRect(hwnd)
                        # 排除最小化的窗口和太小的窗口
                        if rect[2] - rect[0] > 50 and rect[3] - rect[1] > 50:
                            # 排除任务栏（因为任务栏已经默认添加）
                            if win32gui.GetClassName(hwnd) != "Shell_TrayWnd":
                                windows.append({
                                    "title": title,
                                    "class_name": win32gui.GetClassName(hwnd),
                                    "hwnd": hwnd
                                })
                    except Exception as e:
                        print(f"获取窗口信息时出错: {str(e)}")
            return True

        try:
            win32gui.EnumWindows(callback, visible_windows)
        except Exception as e:
            print(f"枚举窗口时出错: {str(e)}")

        # 按标题排序
        visible_windows.sort(key=lambda x: x["title"].lower())
        return visible_windows
        
    def get_common_windows(self):
        """获取当前可见的常用窗口列表
        
        返回:
            list: 包含常用窗口信息的列表，每个元素是一个字典，包含title和display
        """
        # 获取所有可见窗口
        all_windows = self.list_visible_windows()
        
        # 定义常用窗口的关键词匹配
        common_window_patterns = [
            {"keyword": "微信", "display": "微信"},
            {"keyword": "Chrome", "display": "Chrome浏览器"},
            {"keyword": "Edge", "display": "Edge浏览器"},
            {"keyword": "QQ", "display": "QQ"},
            {"keyword": "Word", "display": "Word"},
            {"keyword": "Excel", "display": "Excel"},
            {"keyword": "PowerPoint", "display": "PowerPoint"},
            {"keyword": "钉钉", "display": "钉钉"}
        ]
        
        # 查找匹配的窗口
        found_windows = []
        for window in all_windows:
            window_title = window["title"]
            for pattern in common_window_patterns:
                if pattern["keyword"].lower() in window_title.lower():
                    found_windows.append({
                        "title": window_title,
                        "display": f"{pattern['display']} - {window_title[:20]}{'...' if len(window_title) > 20 else ''}"
                    })
                    break
        
        return found_windows

    def get_interactive_windows(self):
        """获取当前所有互动窗口的列表"""
        return self.fall_config["interactive_windows"]

    def clear_interactive_windows(self):
        """清空所有互动窗口（保留任务栏）"""
        self.fall_config["interactive_windows"].clear()
        self._update_platforms()
        print("已清空所有互动窗口")

    def add_interactive_window(self, title, class_name="*"):
        """
        添加一个新的互动窗口。
        如果窗口已存在，则不会重复添加。
        
        Args:
            title (str): 窗口标题（支持部分匹配）
            class_name (str): 窗口类名，默认为"*"表示匹配任意类名
        """
        # 检查窗口是否已经在列表中
        for window in self.fall_config["interactive_windows"]:
            if window["title"].lower() == title.lower():
                print(f"窗口 '{title}' 已经在互动列表中")
                return False

        # 验证窗口是否存在
        window_rects = self._find_window_geometry(title, class_name)
        if not window_rects:
            print(f"未找到标题包含 '{title}' 的窗口")
            return False

        # 添加到互动窗口列表
        self.fall_config["interactive_windows"].append({
            "title": title,
            "class_name": class_name
        })
        self._update_platforms()
        print(f"已添加互动窗口: {title}")
        return True

    def remove_interactive_window(self, title):
        """
        移除指定的互动窗口。
        
        Args:
            title (str): 要移除的窗口标题
        """
        initial_count = len(self.fall_config["interactive_windows"])
        self.fall_config["interactive_windows"] = [
            w for w in self.fall_config["interactive_windows"]
            if w["title"].lower() != title.lower()
        ]
        if len(self.fall_config["interactive_windows"]) < initial_count:
            self._update_platforms()
            print(f"已移除互动窗口: {title}")
            return True
        else:
            print(f"未找到互动窗口: {title}")
            return False 

    def _check_break_time(self):
        """检查是否需要休息提醒"""
        if not self.break_config["enabled"]:
            return
            
        # 计算距离上次休息的时间（分钟）
        elapsed_time = (time.time() - self.break_config["last_break"]) / 60
        
        # 如果超过设定的间隔时间，且当前不在休息状态
        if (elapsed_time >= self.break_config["interval"] and 
            self.current_state not in [PetState.BREAK, PetState.TOMATO_RESTING]):
            # 更新上次休息时间
            self.break_config["last_break"] = time.time()
            # 添加到提醒队列
            self._add_reminder_to_queue("break", PetState.BREAK, self.break_config["duration"] * 60 * 1000)

    def _check_water_time(self):
        """检查是否需要提醒喝水"""
        if not self.water_config["enabled"]:
            return
        
        current_time = time.time()
        time_since_last_water = current_time - self.water_config["last_water"]
        interval_seconds = self.water_config["interval"] * 60
        
        if time_since_last_water >= interval_seconds:
            print("DPet Debug: 该喝水了！")
            # 重置上次喝水时间
            self.water_config["last_water"] = current_time
            # 添加到提醒队列
            self._add_reminder_to_queue("water", PetState.DRINK, self.water_config["duration"] * 1000)

    def _add_reminder_to_queue(self, reminder_type, state, duration):
        """添加提醒到队列
        
        Args:
            reminder_type: 提醒类型，'water'或'break'
            state: 要切换到的状态
            duration: 持续时间（毫秒）
        """
        # 创建提醒项
        reminder = {
            "type": reminder_type,
            "state": state,
            "duration": duration
        }
        
        # 添加到队列
        if reminder_type == "water":  # 喝水提醒优先级高，放在队列前面
            self.reminder_queue.insert(0, reminder)
        else:
            self.reminder_queue.append(reminder)
        
        # 如果当前没有提醒在显示，则开始显示
        if not self.is_reminder_active:
            self._process_next_reminder()
    
    def _process_next_reminder(self):
        """处理队列中的下一个提醒"""
        if not self.reminder_queue:
            self.is_reminder_active = False
            return
        
        # 取出队列中的第一个提醒
        self.is_reminder_active = True
        reminder = self.reminder_queue.pop(0)
        
        # 切换到对应状态
        self._set_state(reminder["state"])
        
        # 设置定时器，在提醒结束后处理下一个提醒
        QTimer.singleShot(
            reminder["duration"],
            self._reminder_finished
        )
    
    def _reminder_finished(self):
        """提醒结束后的回调"""
        # 切换回空闲状态
        self._set_state(PetState.IDLE)
        
        # 如果随机行走功能开启，重置下次行走时间，使其可以很快再次触发随机行走
        if self.walk_config["enabled"] and not self.tomato_lock_mode:
            print("DPet Debug: 健康提醒结束，随机行走功能已恢复，重置下次行走时间")
            # 设置一个短暂的延迟（3秒）后可以再次触发随机行走
            self.walk_config["next_walk_time"] = time.time() + 3
        
        # 处理队列中的下一个提醒
        QTimer.singleShot(1000, self._process_next_reminder)  # 等待1秒后处理下一个提醒

    def _check_tomato_finished(self):
        if self.tomato_timer.is_finished():
            self.tomato_timer = None
            self.pet_window.hide_tomato_timer()  # 更新方法名

    def set_water_reminder_enabled(self, enabled: bool):
        """设置喝水提醒的启用状态"""
        self.water_config["enabled"] = enabled
        if enabled:
            self.water_config["last_water"] = time.time()  # 重置上次喝水时间
            self.water_timer.start()  # 启动定时器
        else:
            self.water_timer.stop()  # 停止定时器

    def set_water_interval(self, interval: int):
        """设置喝水提醒间隔（分钟）"""
        self.water_config["interval"] = interval
        if self.water_config["enabled"]:
            self.water_config["last_water"] = time.time()  # 重置上次喝水时间

    def set_water_duration(self, duration: int):
        """设置喝水提醒持续时间（秒）"""
        self.water_config["duration"] = duration
        print(f"喝水提醒持续时间已设置为: {duration} 秒")

    def set_break_reminder_enabled(self, enabled: bool):
        """设置休息提醒的启用状态"""
        self.break_config["enabled"] = enabled
        if enabled:
            # 重置上次休息时间，立即开始新的计时
            self.break_config["last_break"] = time.time()
            if not self.break_timer.isActive():
                self.break_timer.start(1000)  # 每秒检查一次
        else:
            # 停止检查休息提醒
            self.break_timer.stop()

    def set_break_interval(self, interval: int):
        """设置休息提醒间隔（分钟）"""
        self.break_config["interval"] = interval
        # 重置上次休息时间，避免立刻触发旧间隔条件
        self.break_config["last_break"] = time.time()

    def set_break_duration(self, duration: int):
        """设置休息提醒持续时间（分钟）"""
        self.break_config["duration"] = duration
        print(f"休息提醒持续时间已设置为: {duration} 分钟")

    def _save_pre_tomato_state(self):
        """保存进入番茄钟前的状态设置"""
        self.pre_tomato_state = {
            "walk_enabled": self.walk_config["enabled"],
            "walk_manual": self.walk_config.get("is_manual_walking", False),
            "break_enabled": self.break_config["enabled"],
            "water_enabled": self.water_config["enabled"],
            "gesture_enabled": False,
            "music_enabled": False
        }
        
        # 保存手势检测状态
        if hasattr(self.pet_window, 'gesture_detector'):
            self.pre_tomato_state["gesture_enabled"] = self.pet_window.gesture_detector.config["enabled"]
            
        # 保存音乐检测状态
        if hasattr(self, 'music_detector'):
            self.pre_tomato_state["music_enabled"] = hasattr(self.music_detector, 'is_running') and self.music_detector.is_running
    
    def _enter_tomato_lock_mode(self):
        """进入番茄钟锁定模式，禁用其他功能"""
        # 禁用行走功能
        self.walk_config["enabled"] = False
        
        # 禁用健康提醒
        self.break_config["enabled"] = False
        self.water_config["enabled"] = False
        
        # 停止定时器
        if hasattr(self, 'break_timer') and self.break_timer.isActive():
            self.break_timer.stop()
            
        if hasattr(self, 'water_timer') and self.water_timer.isActive():
            self.water_timer.stop()
        
        # 禁用手势检测
        if hasattr(self.pet_window, 'gesture_detector'):
            self.pet_window.gesture_detector.set_enabled(False)
            
        # 禁用音乐检测
        if hasattr(self, 'music_detector'):
            if hasattr(self.music_detector, 'stop'):
                self.music_detector.stop()
                
        # 如果当前在跳舞，停止跳舞
        if self.current_state == PetState.DANCE:
            self._set_state(PetState.DANCE_TO_STAND)
            
        # 如果当前在行走，停止行走
        if self.current_state in [PetState.WALK, PetState.WALK_BEGIN]:
            self.stop_walking()
            
        # 设置锁定标志
        self.tomato_lock_mode = True
        
    def _exit_tomato_lock_mode(self):
        """退出番茄钟锁定模式，恢复之前的功能状态"""
        if not hasattr(self, 'pre_tomato_state'):
            return
            
        # 恢复行走功能
        self.walk_config["enabled"] = self.pre_tomato_state["walk_enabled"]
        self.walk_config["is_manual_walking"] = self.pre_tomato_state["walk_manual"]
        
        # 如果随机行走功能开启，重置下次行走时间，使其可以很快再次触发随机行走
        if self.walk_config["enabled"]:
            print("DPet Debug: 退出番茄钟模式，随机行走功能已恢复，重置下次行走时间")
            # 设置一个短暂的延迟（3秒）后可以再次触发随机行走
            self.walk_config["next_walk_time"] = time.time() + 3
        
        # 恢复健康提醒
        self.break_config["enabled"] = self.pre_tomato_state["break_enabled"]
        self.water_config["enabled"] = self.pre_tomato_state["water_enabled"]
        
        # 重新启动定时器
        if self.break_config["enabled"] and not self.break_timer.isActive():
            self.break_timer.start(1000)
        
        # 恢复手势检测
        if hasattr(self.pet_window, 'gesture_detector') and self.pre_tomato_state["gesture_enabled"]:
            self.pet_window.gesture_detector.set_enabled(True)
            
        # 恢复音乐检测
        if hasattr(self.pet_window, 'music_detector') and self.pre_tomato_state["music_enabled"]:
            self.pet_window.music_detector.start()
            
        # 清除锁定标志
        self.tomato_lock_mode = False
        
        # 清除保存的状态
        delattr(self, 'pre_tomato_state')