import cv2
import mediapipe as mp
import numpy as np
from PyQt5.QtCore import QObject, QTimer
import time
from pet_interaction import PetState

class PetGestureDetector(QObject):
    """
    使用MediaPipe实现手势检测，用于控制桌面宠物。
    
    手势定义：
    1. 抓取手势：手掌闭合
    2. 释放手势：手掌张开
    3. 挥手手势：手掌左右移动
    4. 移动手势：手掌持续左右移动控制行走
    """
    
    def __init__(self, interaction_handler):
        """
        初始化手势检测器
        
        Args:
            interaction_handler: PetInteraction实例，用于控制宠物行为
        """
        super().__init__()
        self.interaction_handler = interaction_handler
        
        # 初始化MediaPipe
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # 使用GestureRecognizer替代Hands
        BaseOptions = mp.tasks.BaseOptions
        GestureRecognizer = mp.tasks.vision.GestureRecognizer
        GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        # 创建GestureRecognizer
        options = GestureRecognizerOptions(
            base_options=BaseOptions(model_asset_path='gesture_recognizer.task'),
            running_mode=VisionRunningMode.IMAGE,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.5,
            num_hands=2
        )
        self.gesture_recognizer = GestureRecognizer.create_from_options(options)
        
        # 创建视频捕获对象
        self.cap = None
        
        # 创建定时器用于定期检测
        self.detection_timer = QTimer()
        self.detection_timer.timeout.connect(self._process_frame)
        
        # 状态追踪
        self.is_walking = False
        self.current_direction = None
        self.last_state_change = 0
        self.is_in_yeah_state = False
        self.yeah_animation_started = False
        self.yeah_frames_count = 0
        
        # 配置参数
        self.config = {
            "enabled": False,
            "detection_interval": 50,     # 检测间隔（毫秒）
            "palm_threshold": 0.6,        # 手掌张开阈值
            "state_cooldown": 0.2,        # 状态改变冷却时间（秒）
            "yeah_frames_threshold": 3,    # 连续检测到Yeah手势的帧数阈值
            "show_debug_window": False    # 默认不显示调试窗口
        }
        
        # 调试窗口名称
        self.debug_window_name = "Hand Gesture Debug"

    def start(self):
        """启动手势检测"""
        if not self.config["enabled"]:
            return
            
        if self.cap is None:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("无法打开摄像头")
                return
                
        self.detection_timer.start(self.config["detection_interval"])
        print("手势检测已启动")
        
        if self.config["show_debug_window"]:
            cv2.namedWindow(self.debug_window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.debug_window_name, 640, 480)

    def stop(self):
        """停止手势检测"""
        self.detection_timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        if self.config["show_debug_window"]:
            cv2.destroyWindow(self.debug_window_name)
        
        print("手势检测已停止")

    def set_enabled(self, enabled: bool):
        """设置是否启用手势检测"""
        self.config["enabled"] = enabled
        if enabled:
            self.start()
        else:
            self.stop()

    def _calculate_palm_openness(self, hand_landmarks):
        """计算手掌张开程度"""
        # 直接使用 NormalizedLandmark 对象的坐标
        palm_center = np.array([hand_landmarks[0].x, hand_landmarks[0].y])
        finger_tips = [8, 12, 16, 20]  # 食指、中指、无名指、小指的指尖
        total_distance = 0
        
        for tip_id in finger_tips:
            tip_pos = np.array([hand_landmarks[tip_id].x, hand_landmarks[tip_id].y])
            distance = np.linalg.norm(tip_pos - palm_center)
            total_distance += distance
            
        palm_value = (total_distance - 0.2) / 0.2
        return np.clip(palm_value, 0, 1)

    def _process_frame(self):
        """处理视频帧并检测手势"""
        if hasattr(self, 'interaction_handler') and getattr(self.interaction_handler, 'tomato_lock_mode', False):
            return
        if self.cap is None or not self.cap.isOpened():
            return
            
        success, frame = self.cap.read()
        if not success:
            return
            
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 创建MediaPipe Image对象
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # 使用GestureRecognizer处理图像
        recognition_result = self.gesture_recognizer.recognize(mp_image)
        
        # 准备调试画面
        debug_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        status_text = []
        
        if not recognition_result.gestures:
            status_text = ["No hands detected"]
            if self.is_in_yeah_state:
                print("未检测到手，结束Yeah状态")
                self.is_in_yeah_state = False
                self.interaction_handler._set_state("STAND")
            if self.is_walking:
                print("停止行走")
                self.interaction_handler.stop_walking()
                self.is_walking = False
                self.current_direction = None
            self.yeah_frames_count = 0
            self._show_debug_info(debug_frame, status_text)
            return
        
        current_time = time.time()
        detected_yeah = False
        detected_hands = {"Left": False, "Right": False}
        
        # 处理每只手的手势
        for hand_idx, (gestures, handedness, hand_landmarks) in enumerate(
            zip(recognition_result.gestures, recognition_result.handedness, recognition_result.hand_landmarks)):
            
            # 创建一个兼容的 landmark 列表对象
            class CompatibleLandmark:
                def __init__(self, x, y, z, visibility=None):
                    self.x = x
                    self.y = y
                    self.z = z
                    self._visibility = visibility
                
                def HasField(self, field):
                    if field == 'visibility':
                        return self._visibility is not None
                    return False
                
                @property
                def visibility(self):
                    return self._visibility if self._visibility is not None else 0.0

            class CompatibleLandmarkList:
                def __init__(self, landmarks):
                    self.landmark = [
                        CompatibleLandmark(
                            lm.x, lm.y, lm.z,
                            lm.visibility if hasattr(lm, 'visibility') else None
                        ) for lm in landmarks
                    ]
            
            landmark_list = CompatibleLandmarkList(hand_landmarks)
            
            # 绘制手部标记
            self.mp_draw.draw_landmarks(
                debug_frame,
                landmark_list,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style()
            )
            
            # 获取手的类型（左手或右手）
            hand_type = "Left" if handedness[0].category_name == "Left" else "Right"
            
            # 检查手势
            gesture_name = gestures[0].category_name
            gesture_score = gestures[0].score
            status_text.append(f"{hand_type} Gesture: {gesture_name} ({gesture_score:.2f})")
            
            # 检测Victory/Yeah手势
            if gesture_name == "Victory" and gesture_score > 0.7:
                detected_yeah = True
            else:
                # 如果不是Victory手势，检查手掌开合状态
                palm_value = self._calculate_palm_openness(hand_landmarks)
                status_text.append(f"{hand_type} Palm: {palm_value:.2f}")
                
                if palm_value > self.config["palm_threshold"]:
                    detected_hands[hand_type] = True
                    status_text.append(f"{hand_type} hand detected (open)")
        
        # 处理Yeah手势状态
        if detected_yeah:
            self.yeah_frames_count += 1
            status_text.append(f"Yeah frames: {self.yeah_frames_count}/{self.config['yeah_frames_threshold']}")
            
            if (self.yeah_frames_count >= self.config['yeah_frames_threshold'] and 
                not self.is_in_yeah_state):
                print("检测到Yeah手势！")
                status_text.append("Yeah gesture detected!")
                self.is_in_yeah_state = True
                
                if self.is_walking:
                    print("尝试停止行走")
                    self.interaction_handler.stop_walking()
                    self.is_walking = False
                    self.current_direction = None
                
                # 使用 _set_state 来播放 happy 动画
                self.interaction_handler._set_state(PetState.HAPPY_BEGIN)
                self.yeah_animation_started = True
            
            self._show_debug_info(debug_frame, status_text)
            return
        
        # 如果没有检测到Yeah手势
        self.yeah_frames_count = 0
        if self.is_in_yeah_state:
            print("Yeah手势结束")
            status_text.append("Yeah gesture ended")
            self.is_in_yeah_state = False
            self.interaction_handler._set_state(PetState.STAND)
            self._show_debug_info(debug_frame, status_text)
            return
        
        # 处理行走控制
        new_direction = None
        if detected_hands["Left"] and not detected_hands["Right"]:
            new_direction = "right"
        elif detected_hands["Right"] and not detected_hands["Left"]:
            new_direction = "left"
        
        if new_direction:
            if (not self.is_walking or 
                (new_direction != self.current_direction and 
                 current_time - self.last_state_change > self.config["state_cooldown"])):
                
                self.current_direction = new_direction
                self.last_state_change = current_time
                
                if not self.is_walking:
                    print(f"开始行走，方向：{new_direction}")
                    status_text.append(f"Action: Start walking {new_direction}")
                else:
                    print(f"改变方向：{new_direction}")
                    status_text.append(f"Action: Change direction to {new_direction}")
                
                self.is_walking = True
                self.interaction_handler.start_walking(new_direction)
        else:
            if self.is_walking:
                print("停止行走")
                status_text.append("Action: Stop walking")
                self.interaction_handler.stop_walking()
                self.is_walking = False
                self.current_direction = None
        
        self._show_debug_info(debug_frame, status_text)

    def _show_debug_info(self, debug_frame, status_text):
        """显示调试信息"""
        for i, text in enumerate(status_text):
            cv2.putText(
                debug_frame,
                text,
                (10, 30 + i * 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
        
        if self.config["show_debug_window"]:
            cv2.imshow(self.debug_window_name, debug_frame)
            cv2.waitKey(1)

    def show_debug_window(self):
        """显示调试窗口"""
        if not self.config["show_debug_window"]:
            self.config["show_debug_window"] = True
            if self.config["enabled"]:
                cv2.namedWindow(self.debug_window_name, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(self.debug_window_name, 640, 480)
                print("已显示手势识别调试窗口")

    def hide_debug_window(self):
        """隐藏调试窗口"""
        if self.config["show_debug_window"]:
            self.config["show_debug_window"] = False
            cv2.destroyWindow(self.debug_window_name)
            print("已隐藏手势识别调试窗口")

    def toggle_debug_window(self):
        """切换调试窗口显示状态"""
        if self.config["show_debug_window"]:
            self.hide_debug_window()
        else:
            self.show_debug_window()

    def __del__(self):
        """清理资源"""
        self.stop()
        self.gesture_recognizer.close()
        cv2.destroyAllWindows() 