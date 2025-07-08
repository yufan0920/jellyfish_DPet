from enum import Enum
from PyQt5.QtCore import QTimer

class TomatoState(Enum):
    """番茄钟状态"""
    IDLE = 0        # 空闲状态
    WORKING = 1     # 工作状态
    RESTING = 2     # 休息状态
    COMPLETED = 3   # 完成状态

class PetTomatoTimer:
    """番茄钟计时器"""
    def __init__(self, interaction):
        self.interaction = interaction
        self.state = TomatoState.IDLE
        # 默认配置
        self.work_minutes = 25
        self.rest_minutes = 5
        self.total_tomatoes = 4
        self.current_tomato = 0
        self.completed_tomatoes = 0  # 新增：已完成的番茄钟数（包括休息时间）
        self.remaining_seconds = 0
        self.is_paused = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

    def get_settings(self):
        """获取当前番茄钟设置"""
        return {
            'work_minutes': self.work_minutes,
            'rest_minutes': self.rest_minutes,
            'total_tomatoes': self.total_tomatoes
        }

    def configure(self, work_minutes: int, rest_minutes: int, total_tomatoes: int):
        """配置番茄钟参数"""
        self.work_minutes = work_minutes
        self.rest_minutes = rest_minutes
        self.total_tomatoes = total_tomatoes
        self.reset()  # 重置当前状态

    def start(self):
        """开始番茄钟"""
        if self.state == TomatoState.IDLE:
            self.current_tomato = 0
            self.completed_tomatoes = 0  # 重置已完成数
            self._start_work_period()
            # 更新进度显示
            self.interaction._handle_tomato_completed()  # 调用此方法来更新进度显示

    def pause(self):
        """暂停番茄钟"""
        if not self.is_paused and self.timer.isActive():
            self.timer.stop()
            self.is_paused = True

    def resume(self):
        """继续番茄钟"""
        if self.is_paused:
            self.timer.start(1000)  # 1秒间隔
            self.is_paused = False

    def reset(self):
        """重置番茄钟"""
        self.timer.stop()
        self.state = TomatoState.IDLE
        self.current_tomato = 0
        self.completed_tomatoes = 0  # 重置已完成数
        self.remaining_seconds = 0
        self.is_paused = False
        self.interaction._handle_tomato_state_change(self.state)

    def _start_work_period(self):
        """开始工作时间段"""
        self.state = TomatoState.WORKING
        self.remaining_seconds = self.work_minutes * 60
        self.timer.start(1000)  # 1秒间隔
        self.interaction._handle_tomato_state_change(self.state)

    def _start_rest_period(self):
        """开始休息时间段"""
        self.state = TomatoState.RESTING
        self.remaining_seconds = self.rest_minutes * 60
        self.timer.start(1000)  # 1秒间隔
        self.interaction._handle_tomato_state_change(self.state)

    def _tick(self):
        """计时器tick事件处理"""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self.interaction._handle_tomato_time_update(self.remaining_seconds)
            if self.remaining_seconds == 0:
                if self.state == TomatoState.WORKING:
                    self.current_tomato += 1
                    if self.current_tomato >= self.total_tomatoes:
                        # 所有番茄钟完成
                        self.timer.stop()
                        self.state = TomatoState.COMPLETED
                        self.completed_tomatoes = self.total_tomatoes  # 更新完成数
                        self.interaction._handle_tomato_state_change(self.state)
                        self.interaction._handle_all_tomatoes_completed()
                    else:
                        # 开始休息
                        self._start_rest_period()
                        # 在状态更新为休息后再更新进度显示
                        self.interaction._handle_tomato_completed()
                elif self.state == TomatoState.RESTING:
                    # 休息结束，完成一个完整的番茄钟周期
                    self.completed_tomatoes = self.current_tomato  # 更新已完成的番茄钟数
                    # 开始下一个工作时间段
                    self._start_work_period()
                    # 在状态更新为工作后再更新进度显示
                    self.interaction._handle_tomato_completed()

    def get_formatted_time(self) -> str:
        """获取格式化的剩余时间"""
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def get_progress(self) -> tuple:
        """获取当前进度"""
        if self.state == TomatoState.IDLE:
            return 0, self.total_tomatoes
        elif self.state == TomatoState.RESTING:
            # 在休息时间显示当前完成的番茄钟编号，而不是下一个
            return self.current_tomato, self.total_tomatoes
        else:
            # 在工作时间显示当前进行中的番茄钟编号
            return self.current_tomato + 1, self.total_tomatoes 