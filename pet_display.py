from PyQt5.QtWidgets import (QMainWindow, QLabel, QApplication, QMenu, QAction, 
                            QSlider, QWidgetAction, QWidget, QVBoxLayout, QHBoxLayout, 
                            QSizePolicy, QInputDialog, QMessageBox, QSystemTrayIcon, 
                            QDialog, QSpinBox, QFormLayout, QPushButton, QCheckBox,
                            QFrame, QTabWidget, QListWidget, QListWidgetItem, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QSize
from PyQt5.QtGui import QPixmap, QTransform, QPainter, QColor, QFont, QImage, QIcon
import sys
import os

class TomatoSettingsDialog(QDialog):
    """番茄钟设置对话框，风格与健康提醒设置一致"""
    def __init__(self, parent=None, tomato_config=None):
        super().__init__(parent)
        self.setWindowTitle("番茄钟设置")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        layout = QFormLayout()
        # 工作时间
        self.work_time = QSpinBox()
        self.work_time.setRange(1, 120)
        self.work_time.setValue(int(tomato_config.get("work_minutes", 25)) if tomato_config else 25)
        layout.addRow("工作时间（分钟）:", self.work_time)
        # 休息时间
        self.rest_time = QSpinBox()
        self.rest_time.setRange(1, 30)
        self.rest_time.setValue(int(tomato_config.get("rest_minutes", 5)) if tomato_config else 5)
        layout.addRow("休息时间（分钟）:", self.rest_time)
        # 番茄钟个数
        self.tomato_count = QSpinBox()
        self.tomato_count.setRange(1, 10)
        self.tomato_count.setValue(int(tomato_config.get("total_tomatoes", 4)) if tomato_config else 4)
        layout.addRow("番茄钟个数:", self.tomato_count)
        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addRow("", button_layout)
        self.setLayout(layout)
    def get_settings(self):
        return {
            "work_minutes": self.work_time.value(),
            "rest_minutes": self.rest_time.value(),
            "total_tomatoes": self.tomato_count.value()
        }

class TomatoTimerWindow(QWidget):
    """独立的番茄钟倒计时窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |      # 无边框
            Qt.WindowStaysOnTopHint |     # 置顶
            Qt.Tool                       # 工具窗口
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # 透明背景

        # 创建倒计时标签
        self.timer_label = QLabel(self)
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                border-radius: 10px;
                padding: 8px;
                font-size: 32px;
                font-weight: bold;
            }
        """)

        # 创建布局
        layout = QVBoxLayout(self)
        layout.addWidget(self.timer_label)
        layout.setContentsMargins(0, 0, 0, 0)

        # 设置默认大小
        self.resize(150, 60)

    def update_time(self, time_str: str):
        """更新显示的时间"""
        self.timer_label.setText(time_str)
        self.timer_label.adjustSize()
        self.adjustSize()

class HealthReminderDialog(QDialog):
    """健康提醒设置对话框，支持休息提醒和喝水提醒的统一设置"""
    def __init__(self, parent=None, break_config=None, water_config=None):
        super().__init__(parent)
        self.setWindowTitle("健康提醒设置")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        layout = QFormLayout()

        # 休息提醒
        self.break_enable = QCheckBox("启用休息提醒")
        self.break_enable.setChecked(break_config.get("enabled", False) if break_config else False)
        layout.addRow(self.break_enable)

        self.break_interval = QSpinBox()
        self.break_interval.setRange(1, 180)
        self.break_interval.setValue(int(break_config.get("interval", 60)) if break_config else 60)
        layout.addRow("休息间隔（分钟）:", self.break_interval)

        self.break_duration = QSpinBox()
        self.break_duration.setRange(1, 60)
        self.break_duration.setValue(int(break_config.get("duration", 5)) if break_config else 5)
        layout.addRow("休息时长（分钟）:", self.break_duration)

        # 喝水提醒
        self.water_enable = QCheckBox("启用喝水提醒")
        self.water_enable.setChecked(water_config.get("enabled", False) if water_config else False)
        layout.addRow(self.water_enable)

        self.water_interval = QSpinBox()
        self.water_interval.setRange(1, 180)
        self.water_interval.setValue(int(water_config.get("interval", 60)) if water_config else 60)
        layout.addRow("喝水间隔（分钟）:", self.water_interval)

        self.water_duration = QSpinBox()
        self.water_duration.setRange(1, 600)
        self.water_duration.setValue(int(water_config.get("duration", 60)) if water_config else 60)
        layout.addRow("喝水动画时长（秒）:", self.water_duration)

        # 按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addRow("", button_layout)

        self.setLayout(layout)

    def get_settings(self):
        return {
            "break": {
                "enabled": self.break_enable.isChecked(),
                "interval": self.break_interval.value(),
                "duration": self.break_duration.value(),
            },
            "water": {
                "enabled": self.water_enable.isChecked(),
                "interval": self.water_interval.value(),
                "duration": self.water_duration.value(),
            }
        }

class InteractiveWindowDialog(QDialog):
    """互动窗口选择对话框，让用户可以勾选多个预设窗口"""
    def __init__(self, parent=None, interaction_handler=None):
        super().__init__(parent)
        self.interaction_handler = interaction_handler
        self.selected_windows = []
        
        self.setWindowTitle("选择互动窗口")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        # 创建主布局
        layout = QVBoxLayout(self)
        
        # 添加标签
        label = QLabel("请选择要添加的互动窗口：")
        layout.addWidget(label)
        
        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        
        # 预设窗口选项卡
        self.general_tab = QWidget()
        self.general_layout = QVBoxLayout(self.general_tab)
        
        # 当前窗口选项卡
        self.current_tab = QWidget()
        self.current_layout = QVBoxLayout(self.current_tab)
        
        # 添加选项卡
        self.tab_widget.addTab(self.current_tab, "当前窗口")
        self.tab_widget.addTab(self.general_tab, "预设窗口")
        
        layout.addWidget(self.tab_widget)
        
        # 创建列表控件
        self.window_list = QListWidget()
        self.window_list.setSelectionMode(QListWidget.MultiSelection)
        self.current_layout.addWidget(self.window_list)
        
        # 创建预设窗口选项
        self.create_preset_options()
        
        # 创建当前窗口列表
        self.populate_current_windows()
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 添加按钮
        add_button = QPushButton("确定")
        add_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def create_preset_options(self):
        """创建预设窗口选项"""
        # 创建常用应用程序组
        apps_group = QGroupBox("常用应用程序")
        apps_layout = QVBoxLayout(apps_group)
        
        # 预设应用列表
        preset_apps = [
            {"name": "浏览器", "items": ["Chrome", "Edge"]},
            {"name": "社交软件", "items": ["微信", "QQ", "钉钉"]},
            {"name": "办公软件", "items": ["Word", "Excel", "PowerPoint"]},
        ]
        
        self.preset_checkboxes = []  # 存储所有预设复选框
        
        # 为每个分组创建复选框
        for group in preset_apps:
            group_box = QGroupBox(group["name"])
            group_layout = QVBoxLayout(group_box)
            
            for item in group["items"]:
                checkbox = QCheckBox(item)
                self.preset_checkboxes.append(checkbox)  # 添加到复选框列表
                group_layout.addWidget(checkbox)
            
            apps_layout.addWidget(group_box)
        
        self.general_layout.addWidget(apps_group)
    
    def populate_current_windows(self):
        """填充当前窗口列表"""
        if not self.interaction_handler:
            return
            
        # 获取当前可见的窗口
        visible_windows = self.interaction_handler.list_visible_windows()
        
        # 添加到列表控件
        for window in visible_windows:
            item = QListWidgetItem(window["title"])
            item.setData(Qt.UserRole, window["title"])  # 存储窗口标题作为数据
            self.window_list.addItem(item)
    
    def get_selected_windows(self):
        """获取选中的窗口列表"""
        selected_windows = []
        
        # 获取总体设置选项卡中选中的预设窗口
        for checkbox in self.preset_checkboxes:
            if checkbox.isChecked():
                window_title = checkbox.text()
                # 查找匹配的窗口
                if self.interaction_handler:
                    windows = self.interaction_handler._find_window_geometry(window_title, "*")
                    if windows:
                        selected_windows.append({"title": window_title, "class_name": "*"})
        
        # 获取当前窗口选项卡中选中的项
        for index in range(self.window_list.count()):
            item = self.window_list.item(index)
            if item.isSelected():
                window_title = item.data(Qt.UserRole)
                selected_windows.append({"title": window_title, "class_name": "*"})
        
        return selected_windows

class TomatoProgressWindow(QWidget):
    """番茄钟进度显示窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建标签
        self.progress_label = QLabel(self)
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 150);
                border-radius: 10px;
                padding: 5px 10px;
                font-size: 16px;
            }
        """)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.progress_label)
        
        self.hide()
    
    def update_progress(self, current: int, total: int):
        """更新进度显示"""
        self.progress_label.setText(f"🍅 {current}/{total}")
        self.progress_label.adjustSize()
        self.adjustSize()

class PetDisplay(QMainWindow):
    """
    负责宠物在桌面上的显示。
    包括窗口的创建、样式的设置（如无边框、置顶、透明背景）以及宠物图像的加载和更新。
    """
    def __init__(self, size=(100,100), position=(100,100)):
        """
        初始化宠物显示窗口。

        Args:
            size (tuple): 窗口的初始尺寸 (宽度, 高度)。
            position (tuple): 窗口在屏幕上的初始位置 (x, y)。
        """
        super().__init__()
        
        # 存储初始尺寸，作为100%缩放的基准
        self.base_width = size[0]
        self.base_height = size[1]
        print(f"初始化大小: {self.base_width}x{self.base_height}")
        
        # 创建和配置标签
        self.pet_label = QLabel(self)
        self.pet_label.setScaledContents(True)
        # 设置大小策略，允许缩小和放大
        self.pet_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setCentralWidget(self.pet_label)

        self.setWindowFlags(
            Qt.FramelessWindowHint |      
            Qt.WindowStaysOnTopHint |     
            Qt.Tool                       
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置窗口大小策略
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # 设置初始大小和位置
        self.resize(self.base_width, self.base_height)
        self.move(position[0], position[1])
        
        # 创建右键菜单
        self.context_menu = QMenu(self)
        self.setup_context_menu()
        self.setup_tomato_only_menu()
        
        # 创建番茄钟倒计时窗口
        self.tomato_timer_window = TomatoTimerWindow()
        
        # 创建番茄钟进度显示窗口
        self.tomato_progress_window = TomatoProgressWindow()
        
        self.show()

    def setup_context_menu(self):
        """设置右键菜单的内容"""
        # 音乐跳舞功能开关
        self.dance_action = QAction('音乐跳舞', self, checkable=True)
        self.dance_action.setChecked(True)  # 默认开启
        self.dance_action.triggered.connect(self.toggle_dance)
        
        # 创建行走控制子菜单
        walk_menu = QMenu('行走控制', self)
        
        # 手动行走控制
        manual_walk_menu = QMenu('手动行走', self)
        walk_left_action = QAction('向左行走', self)
        walk_left_action.triggered.connect(lambda: self.interaction_handler.set_walk_direction("left"))
        manual_walk_menu.addAction(walk_left_action)
        
        walk_right_action = QAction('向右行走', self)
        walk_right_action.triggered.connect(lambda: self.interaction_handler.set_walk_direction("right"))
        manual_walk_menu.addAction(walk_right_action)
        
        stop_walk_action = QAction('停止行走', self)
        stop_walk_action.triggered.connect(lambda: self.interaction_handler.stop_walking())
        manual_walk_menu.addAction(stop_walk_action)
        
        walk_menu.addMenu(manual_walk_menu)
        walk_menu.addSeparator()  # 添加分隔线
        
        # 随机行走设置
        random_walk_menu = QMenu('随机行走', self)
        
        # 随机行走功能开关
        self.walk_action = QAction('启用随机行走', self, checkable=True)
        self.walk_action.setChecked(False)  # 默认关闭
        self.walk_action.triggered.connect(self.toggle_walk)
        random_walk_menu.addAction(self.walk_action)
        
        random_walk_menu.addSeparator()
        
        # 行走概率滑块
        chance_widget = QWidget()
        chance_layout = QHBoxLayout(chance_widget)
        chance_layout.setContentsMargins(5, 0, 5, 0)
        
        self.chance_slider = QSlider(Qt.Horizontal)
        self.chance_slider.setMinimum(0)
        self.chance_slider.setMaximum(100)
        self.chance_slider.setValue(30)  # 默认30%
        self.chance_slider.valueChanged.connect(self.on_walk_chance_changed)
        
        chance_layout.addWidget(QLabel('行走概率:'))
        chance_layout.addWidget(self.chance_slider)
        
        chance_action = QWidgetAction(self)
        chance_action.setDefaultWidget(chance_widget)
        random_walk_menu.addAction(chance_action)
        
        # 行走速度滑块
        speed_widget = QWidget()
        speed_layout = QHBoxLayout(speed_widget)
        speed_layout.setContentsMargins(5, 0, 5, 0)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(20)
        self.speed_slider.setValue(5)  # 默认速度5
        self.speed_slider.valueChanged.connect(self.on_walk_speed_changed)
        
        speed_layout.addWidget(QLabel('行走速度:'))
        speed_layout.addWidget(self.speed_slider)
        
        speed_action = QWidgetAction(self)
        speed_action.setDefaultWidget(speed_widget)
        random_walk_menu.addAction(speed_action)
        
        walk_menu.addMenu(random_walk_menu)
        
        # 创建大小调节子菜单
        size_menu = QMenu('大小设置', self)
        
        # 添加固定大小选项
        size_70_action = QAction('较小 (70%)', self)
        size_70_action.triggered.connect(lambda: self.change_size(0.7))
        size_menu.addAction(size_70_action)
        
        size_100_action = QAction('标准 (100%)', self)
        size_100_action.triggered.connect(lambda: self.change_size(1.0))
        size_menu.addAction(size_100_action)
        
        size_150_action = QAction('较大 (150%)', self)
        size_150_action.triggered.connect(lambda: self.change_size(1.5))
        size_menu.addAction(size_150_action)
        
        size_200_action = QAction('最大 (200%)', self)
        size_200_action.triggered.connect(lambda: self.change_size(2.0))
        size_menu.addAction(size_200_action)
        
        # 创建互动窗口管理子菜单
        interactive_menu = QMenu('可互动窗口', self)
        
        # 添加新窗口动作
        add_window_action = QAction('增加窗口', self)
        add_window_action.triggered.connect(self.add_interactive_window)
        interactive_menu.addAction(add_window_action)
        
        # 添加预设窗口菜单项
        preset_window_action = QAction('预设窗口', self)
        preset_window_action.triggered.connect(self.show_preset_window_dialog)
        interactive_menu.addAction(preset_window_action)
        
        # 添加分隔线
        interactive_menu.addSeparator()
        
        # 移除窗口子菜单（将在显示菜单时动态填充）
        self.remove_window_menu = QMenu('移除窗口', self)
        interactive_menu.addMenu(self.remove_window_menu)
        
        # 创建番茄钟菜单
        tomato_menu = QMenu('番茄钟', self)
        
        # 开始番茄钟
        self.start_tomato_action = QAction('开始番茄钟', self)
        self.start_tomato_action.triggered.connect(self.start_tomato_timer)
        tomato_menu.addAction(self.start_tomato_action)
        
        # 暂停番茄钟
        self.pause_tomato_action = QAction('暂停番茄钟', self)
        self.pause_tomato_action.triggered.connect(self.pause_tomato_timer)
        self.pause_tomato_action.setEnabled(False)
        tomato_menu.addAction(self.pause_tomato_action)
        
        # 继续番茄钟（新增）
        self.resume_tomato_action = QAction('继续番茄钟', self)
        self.resume_tomato_action.triggered.connect(self.resume_tomato_timer)
        self.resume_tomato_action.setEnabled(False)
        tomato_menu.addAction(self.resume_tomato_action)
        
        # 重置番茄钟
        self.reset_tomato_action = QAction('重置番茄钟', self)
        self.reset_tomato_action.triggered.connect(self.reset_tomato_timer)
        self.reset_tomato_action.setEnabled(False)
        tomato_menu.addAction(self.reset_tomato_action)
        
        tomato_menu.addSeparator()
        
        # 番茄钟设置
        self.settings_tomato_action = QAction('番茄钟设置', self)
        self.settings_tomato_action.triggered.connect(self.show_tomato_settings_dialog)
        tomato_menu.addAction(self.settings_tomato_action)
        
        # 按照指定顺序添加所有菜单项
        # 第一部分：基本交互功能
        self.context_menu.addAction(self.dance_action)
        self.context_menu.addMenu(walk_menu)
        self.context_menu.addMenu(size_menu) # 添加大小设置菜单
        self.context_menu.addSeparator()  # 添加分隔线
        
        # 第二部分：健康和工作管理
        self.context_menu.addMenu(tomato_menu)  # 番茄钟菜单
        
        # 健康提醒设置
        reminder_action = QAction('健康提醒设置', self)
        reminder_action.triggered.connect(self.show_health_reminder_dialog)
        self.context_menu.addAction(reminder_action)
        
        self.context_menu.addSeparator()  # 添加分隔线
        
        # 第三部分：窗口管理和退出
        self.context_menu.addMenu(interactive_menu)
        
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(QApplication.quit)
        self.context_menu.addAction(exit_action)

    def setup_tomato_only_menu(self):
        """设置番茄钟专用右键菜单，仅包含番茄钟相关操作和退出"""
        self.tomato_only_menu = QMenu(self)
        tomato_menu = QMenu('番茄钟', self)

        # 开始番茄钟
        tomato_menu.addAction(self.start_tomato_action)
        
        # 暂停番茄钟
        self.pause_tomato_action.setText('暂停番茄钟')  # 确保文本是"暂停番茄钟"
        tomato_menu.addAction(self.pause_tomato_action)
        
        # 继续番茄钟（新增）
        self.resume_tomato_action = QAction('继续番茄钟', self)
        self.resume_tomato_action.triggered.connect(self.resume_tomato_timer)
        self.resume_tomato_action.setEnabled(False)  # 初始禁用
        tomato_menu.addAction(self.resume_tomato_action)
        
        # 重置番茄钟
        tomato_menu.addAction(self.reset_tomato_action)
        
        tomato_menu.addSeparator()
        # 番茄钟设置
        tomato_menu.addAction(self.settings_tomato_action)
        
        self.tomato_only_menu.addMenu(tomato_menu)
        
        # 退出动作
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(QApplication.quit)
        self.tomato_only_menu.addAction(exit_action)

    def toggle_dance(self, checked):
        """切换音乐跳舞功能的开启状态"""
        print(f"切换音乐跳舞功能: {'开启' if checked else '关闭'}")
        # 更新菜单项状态
        self.dance_action.setChecked(checked)
        
        # 如果有交互处理器，设置音乐检测状态
        if hasattr(self, 'interaction_handler'):
            self.interaction_handler.set_music_detection_enabled(checked)
            
        # 如果有直接的音乐检测器引用，也直接控制它
        if hasattr(self, 'music_detector'):
            if checked:
                self.music_detector.start()
            else:
                self.music_detector.stop()

    def toggle_walk(self, checked):
        """切换随机行走功能的开启状态"""
        if hasattr(self, 'interaction_handler'):
            self.interaction_handler.set_walk_enabled(checked)
            
    def on_walk_chance_changed(self, value):
        """处理行走概率滑块值改变"""
        if hasattr(self, 'interaction_handler'):
            self.interaction_handler.set_walk_chance(value / 100.0)
            
    def on_walk_speed_changed(self, value):
        """处理行走速度滑块值改变"""
        if hasattr(self, 'interaction_handler'):
            self.interaction_handler.walk_config["walk_speed"] = value

    def change_size(self, scale_factor):
        """改变桌宠大小
        
        Args:
            scale_factor (float): 相对于基础大小的缩放比例
        """
        try:
            # 计算新的尺寸
            new_width = int(self.base_width * scale_factor)
            new_height = int(self.base_height * scale_factor)
            print(f"调整大小: {int(scale_factor * 100)}% -> {new_width}x{new_height} (基准大小: {self.base_width}x{self.base_height})")
            
            # 调整窗口大小
            self.setFixedSize(new_width, new_height)
            
            # 如果当前有显示的图像，重新设置图像
            if hasattr(self, 'current_pixmap') and self.current_pixmap and not self.current_pixmap.isNull():
                self.update_image_pixmap(self.current_pixmap, self.current_flip_horizontal)
        except Exception as e:
            print(f"调整大小时出错: {str(e)}")

    def update_image_pixmap(self, pixmap: QPixmap, flip_horizontal=False):
        """
        使用预加载的QPixmap对象更新宠物显示的图像。

        Args:
            pixmap (QPixmap): 要显示的QPixmap对象。
            flip_horizontal (bool): 是否水平翻转图像。
        """
        if pixmap and not pixmap.isNull():
            # 保存当前的pixmap和翻转状态，以便大小调整时使用
            self.current_pixmap = pixmap
            self.current_flip_horizontal = flip_horizontal
            
            # 根据当前窗口大小缩放图像
            current_size = self.size()
            scaled_pixmap = pixmap.scaled(
                current_size.width(),
                current_size.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            if flip_horizontal:
                transform = QTransform()
                transform.scale(-1, 1)  # 水平翻转
                scaled_pixmap = scaled_pixmap.transformed(transform)
            
            # 设置缩放后的图像
            self.pet_label.setPixmap(scaled_pixmap)
            # 确保标签大小与窗口大小一致
            self.pet_label.setFixedSize(current_size)
        else:
            print(f"警告: 尝试显示一个空的或无效的Pixmap对象。")

    def add_interactive_window(self):
        """添加新的互动窗口"""
        # 弹出输入对话框
        window_name, ok = QInputDialog.getText(
            self, 
            '添加互动窗口',
            '请输入窗口名称（例如：wps office）：'
        )
        
        if ok and window_name:
            # 这里我们使用一个通用的类名模式，实际使用时可能需要更精确的匹配
            class_name = "*"  # 通配符，匹配任何类名
            
            # 调用interaction_handler的方法添加窗口
            if hasattr(self, 'interaction_handler'):
                self.interaction_handler.add_interactive_window(window_name, class_name)
                QMessageBox.information(
                    self,
                    "添加成功",
                    f"已添加窗口：{window_name}\n"
                    "如果窗口存在且可见，桌宠现在可以站在这个窗口上了。"
                )

    def show_preset_window_dialog(self):
        """显示预设窗口选择对话框"""
        # 创建互动窗口选择对话框
        dialog = InteractiveWindowDialog(self, self.interaction_handler)
        
        # 如果用户点击了确定按钮
        if dialog.exec_() == QDialog.Accepted:
            # 获取选中的窗口列表
            selected_windows = dialog.get_selected_windows()
            
            # 添加选中的窗口
            added_count = 0
            for window in selected_windows:
                if self.interaction_handler.add_interactive_window(window["title"], window["class_name"]):
                    added_count += 1
            
            # 显示添加结果
            if added_count > 0:
                QMessageBox.information(
                    self,
                    "添加成功",
                    f"已成功添加 {added_count} 个互动窗口。"
                )
            else:
                QMessageBox.warning(
                    self,
                    "添加失败",
                    "未能添加任何窗口，请确保选择的窗口存在且可见。"
                )

    def update_remove_window_menu(self):
        """更新移除窗口子菜单的内容"""
        self.remove_window_menu.clear()
        
        if hasattr(self, 'interaction_handler'):
            # 获取当前的互动窗口列表
            windows = self.interaction_handler.fall_config["interactive_windows"]
            
            if not windows:
                # 如果没有互动窗口，添加一个禁用的提示项
                no_windows_action = QAction('没有互动窗口', self)
                no_windows_action.setEnabled(False)
                self.remove_window_menu.addAction(no_windows_action)
            else:
                # 为每个窗口创建一个移除动作
                for window in windows:
                    action = QAction(window["title"], self)
                    action.triggered.connect(
                        lambda checked, title=window["title"]: 
                        self.remove_interactive_window(title)
                    )
                    self.remove_window_menu.addAction(action)

    def remove_interactive_window(self, window_title):
        """移除指定的互动窗口"""
        if hasattr(self, 'interaction_handler'):
            self.interaction_handler.remove_interactive_window(window_title)
            QMessageBox.information(
                self,
                "移除成功",
                f"已移除窗口：{window_title}"
            )

    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.RightButton:
            self.update_remove_window_menu()
            if hasattr(self, 'interaction_handler') and getattr(self.interaction_handler, 'tomato_lock_mode', False):
                self.tomato_only_menu.exec_(event.globalPos())
            else:
                self.context_menu.exec_(event.globalPos())
        elif event.button() == Qt.LeftButton and hasattr(self, 'interaction_handler'):
            self.interaction_handler.handle_mouse_press(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        if hasattr(self, 'interaction_handler') and self.interaction_handler:
            self.interaction_handler.handle_mouse_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        if hasattr(self, 'interaction_handler') and self.interaction_handler:
            self.interaction_handler.handle_mouse_release(event)
        super().mouseReleaseEvent(event)

    def set_interaction_handler(self, handler):
        """
        设置交互事件处理器。
        PetDisplay窗口本身不直接处理复杂的交互逻辑，而是将交互事件
        委托给一个外部的交互处理器对象。

        Args:
            handler (object): 实现了处理鼠标事件方法的对象，通常是PetInteraction的实例。
        """
        self.interaction_handler = handler
        
        # 更新菜单选项的初始状态
        if hasattr(handler, 'walk_config'):
            self.walk_action.setChecked(handler.walk_config["enabled"])
            self.chance_slider.setValue(int(handler.walk_config["walk_chance"] * 100))
            self.speed_slider.setValue(handler.walk_config["walk_speed"])

    def show_health_reminder_dialog(self):
        """弹出健康提醒设置对话框"""
        if hasattr(self, 'interaction_handler'):
            break_cfg = self.interaction_handler.break_config.copy()
            water_cfg = self.interaction_handler.water_config.copy()
            dlg = HealthReminderDialog(self, break_cfg, water_cfg)
            if dlg.exec_() == QDialog.Accepted:
                settings = dlg.get_settings()
                # 休息提醒
                self.interaction_handler.set_break_reminder_enabled(settings['break']['enabled'])
                self.interaction_handler.set_break_interval(settings['break']['interval'])
                self.interaction_handler.set_break_duration(settings['break']['duration'])
                # 喝水提醒
                self.interaction_handler.set_water_reminder_enabled(settings['water']['enabled'])
                self.interaction_handler.set_water_interval(settings['water']['interval'])
                self.interaction_handler.set_water_duration(settings['water']['duration'])

    def start_tomato_timer(self):
        """开始番茄钟"""
        if self.interaction_handler:
            self.interaction_handler.start_tomato_timer()
            self.start_tomato_action.setEnabled(False)
            self.pause_tomato_action.setEnabled(True)
            self.resume_tomato_action.setEnabled(False)  # 禁用继续按钮
            self.reset_tomato_action.setEnabled(True)
            self.settings_tomato_action.setEnabled(False)
            self.tomato_timer_window.show()  # 显示倒计时窗口
            self._update_timer_window_position()  # 立即更新位置

    def pause_tomato_timer(self):
        """暂停番茄钟"""
        if self.interaction_handler:
            self.interaction_handler.pause_tomato_timer()
            self.pause_tomato_action.setEnabled(False)
            self.resume_tomato_action.setEnabled(True)  # 启用继续按钮
            self.reset_tomato_action.setEnabled(True)

    def resume_tomato_timer(self):
        """继续番茄钟"""
        if self.interaction_handler:
            self.interaction_handler.resume_tomato_timer()
            self.pause_tomato_action.setEnabled(True)  # 启用暂停按钮
            self.resume_tomato_action.setEnabled(False)  # 禁用继续按钮
            self.reset_tomato_action.setEnabled(True)

    def reset_tomato_timer(self):
        """重置番茄钟"""
        if self.interaction_handler:
            self.interaction_handler.reset_tomato_timer()
            self.start_tomato_action.setEnabled(True)
            self.pause_tomato_action.setEnabled(False)
            self.resume_tomato_action.setEnabled(False)  # 禁用继续按钮
            self.reset_tomato_action.setEnabled(False)
            self.settings_tomato_action.setEnabled(True)
            self.hide_tomato_timer()  # 使用新的隐藏方法

    def configure_tomato_timer(self):
        """配置番茄钟参数"""
        if hasattr(self, 'interaction_handler'):
            # 工作时长
            work_minutes, ok = QInputDialog.getInt(
                self,
                '设置工作时长',
                '请输入工作时长（分钟）：',
                value=25,  # 默认25分钟
                min=1,
                max=60
            )
            if not ok:
                return
            
            # 休息时长
            rest_minutes, ok = QInputDialog.getInt(
                self,
                '设置休息时长',
                '请输入休息时长（分钟）：',
                value=5,  # 默认5分钟
                min=1,
                max=30
            )
            if not ok:
                return
            
            # 番茄钟数量
            total_tomatoes, ok = QInputDialog.getInt(
                self,
                '设置番茄钟数量',
                '请输入要完成的番茄钟数量：',
                value=1,  # 默认1个
                min=1,
                max=10
            )
            if not ok:
                return
            
            self.interaction_handler.configure_tomato_timer(
                work_minutes, rest_minutes, total_tomatoes
            )
    
    def update_timer_display(self, time_str: str):
        """更新番茄钟倒计时显示"""
        self.tomato_timer_window.update_time(time_str)
        if not self.tomato_timer_window.isVisible():
            self.tomato_timer_window.show()
    
    def update_progress_display(self, current: int, total: int):
        """更新番茄钟进度显示"""
        self.tomato_progress_window.update_progress(current, total)
        if not self.tomato_progress_window.isVisible():
            self.tomato_progress_window.show()
        self._update_timer_window_position()
    
    def moveEvent(self, event):
        """处理窗口移动事件"""
        super().moveEvent(event)
        # 更新倒计时窗口位置
        self._update_timer_window_position()

    def resizeEvent(self, event):
        """处理窗口大小改变事件"""
        super().resizeEvent(event)
        if self.tomato_progress_window.isVisible():
            x = (self.width() - self.tomato_progress_window.width()) // 2
            y = self.tomato_timer_window.y() + self.tomato_timer_window.height() + 5 # 使用tomato_timer_window的y坐标
            self.tomato_progress_window.move(x, y)
        self._update_timer_window_position()

    def _update_timer_window_position(self):
        """更新番茄钟相关窗口的位置"""
        if self.tomato_timer_window.isVisible():
            # 获取桌宠位置
            pet_pos = self.pos()
            # 计算番茄钟计时器窗口位置
            x = pet_pos.x() + self.width()  # 在桌宠右侧
            # 垂直居中后整体下移 50 像素
            y = pet_pos.y() + (self.height() - self.tomato_timer_window.height()) // 2 + 50
            self.tomato_timer_window.move(x, y)
            
            # 更新进度显示窗口位置
            if self.tomato_progress_window.isVisible():
                progress_x = x  # 与计时器窗口x轴对齐
                progress_y = y - 30  # 比计时器窗口高30像素
                self.tomato_progress_window.move(progress_x, progress_y)
    
    def hide_tomato_timer(self):
        """隐藏番茄钟相关窗口"""
        self.tomato_timer_window.hide()
        self.tomato_progress_window.hide()
    
    def _create_tray_menu(self):
        """创建系统托盘菜单"""
        self.tray_menu = QMenu()
        
        # 番茄钟菜单
        tomato_menu = QMenu("番茄钟", self)
        
        # 番茄钟控制动作
        self.start_tomato_action = QAction("开始", self)
        self.start_tomato_action.triggered.connect(self._start_tomato)
        
        self.pause_tomato_action = QAction("暂停", self)
        self.pause_tomato_action.triggered.connect(self._pause_tomato)
        self.pause_tomato_action.setEnabled(False)
        
        self.resume_tomato_action = QAction("继续", self)
        self.resume_tomato_action.triggered.connect(self._resume_tomato)
        self.resume_tomato_action.setEnabled(False)
        
        self.reset_tomato_action = QAction("重置", self)
        self.reset_tomato_action.triggered.connect(self._reset_tomato)
        self.reset_tomato_action.setEnabled(False)
        
        self.settings_tomato_action = QAction("设置", self)
        self.settings_tomato_action.triggered.connect(self._show_tomato_settings)
        
        # 添加番茄钟相关动作到番茄钟菜单
        tomato_menu.addAction(self.start_tomato_action)
        tomato_menu.addAction(self.pause_tomato_action)
        tomato_menu.addAction(self.resume_tomato_action)
        tomato_menu.addAction(self.reset_tomato_action)
        tomato_menu.addSeparator()
        tomato_menu.addAction(self.settings_tomato_action)
        
        # 将番茄钟菜单添加到托盘菜单
        self.tray_menu.addMenu(tomato_menu)
        self.tray_menu.addSeparator()
        # 添加健康提醒设置唯一入口
        reminder_action = QAction('健康提醒设置', self)
        reminder_action.triggered.connect(self.show_health_reminder_dialog)
        self.tray_menu.addAction(reminder_action)
        # 添加番茄钟设置入口
        tomato_settings_action = QAction('番茄钟设置', self)
        tomato_settings_action.triggered.connect(self.show_tomato_settings_dialog)
        self.tray_menu.addAction(tomato_settings_action)
        # 退出动作
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.quit)
        self.tray_menu.addAction(quit_action)
        
        # 设置托盘图标的菜单
        self.tray_icon.setContextMenu(self.tray_menu)

    def _show_tomato_settings(self):
        """显示番茄钟设置对话框"""
        dialog = TomatoSettingsDialog(self)
        # 读取当前设置
        if hasattr(self, 'interaction') and hasattr(self.interaction, 'tomato_timer'):
            current_settings = self.interaction.tomato_timer.get_settings()
            dialog.set_settings(
                current_settings['work_minutes'],
                current_settings['rest_minutes'],
                current_settings['total_tomatoes']
            )
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            if hasattr(self, 'interaction'):
                self.interaction.configure_tomato_timer(
                    settings['work_minutes'],
                    settings['rest_minutes'],
                    settings['total_tomatoes']
                )

    def _start_tomato(self):
        """开始番茄钟"""
        if hasattr(self, 'interaction'):
            self.interaction.start_tomato_timer()
            self.start_tomato_action.setEnabled(False)
            self.pause_tomato_action.setEnabled(True)
            self.resume_tomato_action.setEnabled(False) # 禁用继续按钮
            self.reset_tomato_action.setEnabled(True)
            self.settings_tomato_action.setEnabled(False)
            self.tomato_timer_window.show()  # 显示倒计时窗口
            self._update_timer_window_position()  # 立即更新位置

    def _pause_tomato(self):
        """暂停番茄钟"""
        if hasattr(self, 'interaction'):
            self.interaction.pause_tomato_timer()
            self.pause_tomato_action.setEnabled(False)
            self.resume_tomato_action.setEnabled(True)

    def _resume_tomato(self):
        """继续番茄钟"""
        if hasattr(self, 'interaction'):
            self.interaction.resume_tomato_timer()
            self.resume_tomato_action.setEnabled(False)
            self.pause_tomato_action.setEnabled(True)

    def _reset_tomato(self):
        """重置番茄钟"""
        if hasattr(self, 'interaction'):
            self.interaction.reset_tomato_timer()
            self.start_tomato_action.setEnabled(True)
            self.pause_tomato_action.setEnabled(False)
            self.resume_tomato_action.setEnabled(False) # 禁用继续按钮
            self.reset_tomato_action.setEnabled(False)
            self.settings_tomato_action.setEnabled(True)
            self.hide_tomato_timer()  # 使用新的隐藏方法

    def show_tomato_settings_dialog(self):
        """弹出番茄钟设置对话框"""
        if hasattr(self, 'interaction_handler'):
            tomato_cfg = self.interaction_handler.tomato_timer.get_settings() if hasattr(self.interaction_handler, 'tomato_timer') else {}
            dlg = TomatoSettingsDialog(self, tomato_cfg)
            if dlg.exec_() == QDialog.Accepted:
                settings = dlg.get_settings()
                self.interaction_handler.configure_tomato_timer(
                    settings['work_minutes'],
                    settings['rest_minutes'],
                    settings['total_tomatoes']
                ) 