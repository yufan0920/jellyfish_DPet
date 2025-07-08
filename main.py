import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# 从自定义模块导入核心类
from pet_display import PetDisplay
from pet_interaction import PetInteraction, PetState
from pet_music_detector import PetMusicDetector
from pet_tomato_timer import PetTomatoTimer

class DPet:
    """
    桌宠应用程序的主类。
    负责初始化和管理：
    1. PyQt应用程序实例
    2. 宠物显示窗口(PetDisplay)
    3. 交互逻辑处理器(PetInteraction)
    4. 音乐检测系统(PetMusicDetector)
    5. 番茄钟系统(PetTomatoTimer)
    """
    def __init__(self):
        """初始化DPet应用程序的所有组件"""
        print("DPet: Initializing QApplication...")
        self.app = QApplication(sys.argv)
        print("DPet: QApplication initialized.")
        
        # --- 初始配置参数 ---
        initial_state = PetState.IDLE     # 宠物的初始状态
        window_size = (180, 180)          # 宠物窗口的大小（基础大小）
        initial_position = (100, 100)     # 窗口的初始位置

        # --- 初始化显示窗口 ---
        print(f"DPet: Initializing PetDisplay with size {window_size}...")
        # 1. 创建宠物显示窗口 (PetDisplay实例)
        # PetDisplay负责所有与视觉相关的部分：窗口创建、图像显示等。
        self.display = PetDisplay(
            size=window_size, 
            position=initial_position
        )
        print("DPet: PetDisplay initialized.")
        
        # --- 初始化交互处理器 ---
        print("DPet: Initializing PetInteraction...")
        # 2. 创建宠物交互和状态管理器 (PetInteraction实例)
        # PetInteraction负责处理用户输入（点击、拖动）、状态转换逻辑以及动画播放。
        self.interaction = PetInteraction(
            pet_window=self.display,         # 将显示窗口实例传递给交互处理器
            initial_state=initial_state      # 设置宠物的初始状态
        )
        print("DPet: PetInteraction initialized.")
        
        # 3. 将交互处理器与显示窗口关联
        # PetDisplay窗口会将鼠标事件（如点击、移动）转发给PetInteraction实例进行处理。
        self.display.set_interaction_handler(self.interaction)
        print("DPet: Interaction handler set on display.")
        
        # 4. 设置状态转换检查定时器
        # 创建一个QTimer，定期检查宠物的状态是否需要自动转换，
        # 包括：空闲到睡眠、站立到空闲等状态的自动切换
        self.state_check_timer = QTimer()
        self.state_check_timer.timeout.connect(self.interaction.check_state_transitions)
        self.state_check_timer.start(500)  # 每500毫秒（0.5秒）检查一次状态
        print("DPet: State transition check timer started.")

        # 5. 初始化音乐检测器
        # 创建PetMusicDetector实例，负责检测音乐播放状态
        self.music_detector = PetMusicDetector(self.interaction)
        # 将 music_detector 也赋值给 display 对象，以便 PetInteraction 可以访问
        self.display.music_detector = self.music_detector
        print("DPet: Music detector initialized.")

        print("DPet: __init__ completed.")

    def run(self):
        """启动应用程序的事件循环，程序将持续运行直到退出"""
        print("DPet: Starting event loop (app.exec_())...")
        sys.exit(self.app.exec_())

if __name__ == '__main__':
    # 当脚本作为主程序执行时:
    print("main.py: Script execution started.")
    d_pet = DPet() # 创建DPet应用程序的实例
    print("main.py: DPet instance created.")
    d_pet.run()    # 运行应用程序
    print("main.py: d_pet.run() called (should not see this if event loop started).")
