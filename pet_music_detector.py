import sounddevice as sd  # 用于获取系统音频输出
import numpy as np       # 用于音频数据处理
import psutil           # 用于检测正在运行的进程
from PyQt5.QtCore import QTimer, QObject

class PetMusicDetector(QObject):
    """
    宠物音乐检测器类
    负责检测系统中的音乐播放状态，包括：
    1. 检测音乐播放器进程
    2. 检测系统音频输出
    3. 管理音乐检测的定时器
    """
    def __init__(self, interaction_handler):
        """
        初始化音乐检测器
        
        Args:
            interaction_handler: PetInteraction实例，用于更新宠物状态
        """
        super().__init__()
        
        # 保存交互处理器的引用
        self.interaction = interaction_handler
        
        # --- 音频检测相关参数 ---
        self.audio_threshold = 0.005      # 降低音频响度阈值，使其更容易触发
        self.music_detection_count = 0    # 连续检测到音乐的次数计数器
        self.required_detections = 2      # 减少所需的连续检测次数，加快响应速度
        self.is_playing = False          # 当前音乐播放状态
        
        # --- 音频流设置 ---
        self.stream = None
        self.block_size = 1024  # 减小缓冲区大小，提高采样频率
        
        # 初始化音频流
        self._initialize_audio_stream()
        
        # --- 支持的音乐播放器列表 ---
        self.music_players = {
            "spotify.exe": "Spotify",
            "qqmusic.exe": "QQ音乐",
            "cloudmusic.exe": "网易云音乐",
            "kugou.exe": "酷狗音乐",
            "kwmusic.exe": "酷我音乐",
            "foobar2000.exe": "Foobar2000",
            "music.ui.exe": "Windows Media Player"
        }
        self.active_music_player = None   # 当前正在运行的音乐播放器名称

        # 初始化音乐检测定时器
        self.music_check_timer = QTimer()
        self.music_check_timer.timeout.connect(self._check_music_playing)
        self.music_check_timer.start(200)  # 减少检测间隔到200ms，提高响应速度
        print("PetMusicDetector: Music detection timer started.")

    def _initialize_audio_stream(self):
        """初始化音频流并处理可能的错误"""
        try:
            # 列出所有可用的音频设备
            devices = sd.query_devices()
            print("\nAvailable audio devices:")
            for i, dev in enumerate(devices):
                print(f"[{i}] {dev['name']} (in={dev['max_input_channels']}, out={dev['max_output_channels']})")

            # 查找立体声混音设备
            stereo_mix_device = None
            for i, dev in enumerate(devices):
                if "立体声混音" in dev['name'] and dev['max_input_channels'] > 0:
                    stereo_mix_device = i
                    break

            if stereo_mix_device is None:
                print("Error: Could not find Stereo Mix device. Please enable it in Windows sound settings.")
                return

            # 获取立体声混音设备信息
            device_info = sd.query_devices(stereo_mix_device)
            print(f"\nUsing Stereo Mix device: {device_info['name']}")
            print(f"Channels: in={device_info['max_input_channels']}, out={device_info['max_output_channels']}")
            print(f"Sample rate: {device_info['default_samplerate']}")

            # 创建音频流
            self.stream = sd.InputStream(
                device=stereo_mix_device,
                channels=device_info['max_input_channels'],  # 使用设备支持的通道数
                blocksize=self.block_size,
                samplerate=int(device_info['default_samplerate']),
                dtype=np.float32
            )
            self.stream.start()
            print("PetMusicDetector: Audio stream initialized successfully.")
            
        except Exception as e:
            print(f"PetMusicDetector: Failed to initialize audio stream: {str(e)}")
            if "立体声混音" not in str(e):
                print("\nTroubleshooting steps:")
                print("1. Right-click on the speaker icon in the system tray")
                print("2. Click 'Open Sound settings'")
                print("3. Click 'Sound Control Panel' on the right")
                print("4. In the Recording tab, right-click anywhere and enable 'Show Disabled Devices'")
                print("5. Find 'Stereo Mix', right-click it and enable it")
                print("6. Set it as the default device")
            self.stream = None

    def _is_music_player_running(self):
        """
        检查是否有音乐播放器在运行
        
        检查方式：
        1. 遍历系统所有进程
        2. 对比进程名是否在预定义的音乐播放器列表中
        3. 如果找到正在运行的音乐播放器，记录其名称
        
        Returns:
            bool: 如果有音乐播放器在运行返回True，否则返回False
        """
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                if proc_name in [name.lower() for name in self.music_players.keys()]:
                    self.active_music_player = self.music_players[proc_name]
                    print(f"PetMusicDetector: 检测到音乐播放器: {self.active_music_player}")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        self.active_music_player = None
        return False

    def _check_music_playing(self):
        """检测系统音频输出并结合音乐播放器状态来判断是否在播放音乐"""
        try:
            # 1. 检查音乐播放器
            music_player_running = self._is_music_player_running()
            if not music_player_running:
                self.music_detection_count = 0
                self.is_playing = False
                self.interaction.update_music_state(False)
                return

            # 2. 检查音频输出
            if self.stream is None or not self.stream.active:
                self._reinitialize_stream()
                if self.stream is None:
                    return

            try:
                # 读取音频数据
                data = self.stream.read(self.block_size)[0]
                
                # 计算音频响度 (使用RMS值)
                volume_norm = np.sqrt(np.mean(data**2))
                
                # 调试输出
                print(f"PetMusicDetector: Current volume level: {volume_norm:.6f}")
                
                # 3. 判断是否满足触发条件
                if volume_norm > self.audio_threshold:
                    self.music_detection_count += 1
                    print(f"PetMusicDetector: Detection count: {self.music_detection_count}/{self.required_detections}")
                    if self.music_detection_count >= self.required_detections:
                        print(f"PetMusicDetector: 检测到音乐播放 (来自 {self.active_music_player})")
                        self.is_playing = True
                        self.interaction.update_music_state(True)
                else:
                    if self.music_detection_count > 0:
                        print("PetMusicDetector: Reset detection count due to low volume")
                    self.music_detection_count = 0
                    self.is_playing = False
                    self.interaction.update_music_state(False)
            except sd.PortAudioError as e:
                print(f"PetMusicDetector: 音频读取错误: {str(e)}")
                self._reinitialize_stream()
                
        except Exception as e:
            print(f"PetMusicDetector: 音频检测错误: {str(e)}")
            self.music_detection_count = 0
            self.is_playing = False
            self.interaction.update_music_state(False)

    def _reinitialize_stream(self):
        """重新初始化音频流"""
        try:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
            self._initialize_audio_stream()
        except Exception as e:
            print(f"PetMusicDetector: Failed to reinitialize audio stream: {str(e)}")
            self.stream = None

    def start(self):
        """启动音乐检测"""
        if not self.music_check_timer.isActive():
            self._reinitialize_stream()  # 确保音频流是活跃的
            self.music_check_timer.start(200)
            print("PetMusicDetector: Music detection started.")

    def stop(self):
        """停止音乐检测"""
        if self.music_check_timer.isActive():
            self.music_check_timer.stop()
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            print("PetMusicDetector: Music detection stopped.")

    def set_audio_threshold(self, threshold):
        """
        设置音频检测阈值
        
        Args:
            threshold (float): 新的音频响度阈值
        """
        self.audio_threshold = threshold
        print(f"PetMusicDetector: Audio threshold set to {threshold}")

    def add_music_player(self, process_name, display_name):
        """
        添加新的音乐播放器到检测列表
        
        Args:
            process_name (str): 进程名称（例如：'player.exe'）
            display_name (str): 显示名称（例如：'新音乐播放器'）
        """
        self.music_players[process_name] = display_name
        print(f"PetMusicDetector: Added music player {display_name} ({process_name})")

    def is_music_playing(self):
        """
        获取当前音乐播放状态
        
        Returns:
            bool: 如果音乐正在播放返回True，否则返回False
        """
        return self.is_playing

    def __del__(self):
        """析构函数，确保在对象销毁时正确关闭音频流"""
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass 