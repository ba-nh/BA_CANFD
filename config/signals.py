# config/signals.py
# 신호 설정 파일 - 쉽게 신호를 추가/수정할 수 있도록 분리

# 로깅/저장할 때 사용할 표준 컬럼 순서 (DBC 신호명, Time 포함)
STANDARD_COLUMNS = [
    'Time',
    'ACCELERATOR_PEDAL_PRESSED',
    'BRAKE_PRESSED',
    'BRAKE_PRESSURE',
    'STEERING_ANGLE_2',
    'STEERING_RATE',
    'STEERING_COL_TORQUE',
    'WHEEL_SPEED_1',
    'WHEEL_SPEED_2',
    'WHEEL_SPEED_3',
    'WHEEL_SPEED_4',
    # 필요한 실제 DBC 신호명만 추가
]

# 이벤트 감지에 사용되는 필수 신호들
REQUIRED_SIGNALS = [
    'ACCELERATOR_PEDAL_PRESSED',
    'BRAKE_PRESSED',
    'SPEED',
]

# 대시보드에서 시각화할 신호들 (체크박스로 표시)
VISUALIZATION_SIGNALS = [
    'SPEED',
    'ACCELERATOR_PEDAL_PRESSED',
    'BRAKE_PRESSED',
    'BRAKE_PRESSURE',
    'STEERING_ANGLE_2',
    'STEERING_RATE',
    'STEERING_COL_TORQUE',
]

# 신호별 색상 설정 (대시보드용)
SIGNAL_COLORS = {
    'SPEED': "#1f77b4",
    'ACCELERATOR_PEDAL_PRESSED': "#ff7f0e",
    'BRAKE_PRESSED': "#2ca02c",
    'BRAKE_PRESSURE': "#d62728",
    'STEERING_ANGLE_2': "#9467bd",
    'STEERING_RATE': "#8c564b",
    'STEERING_COL_TORQUE': "#e377c2",
}

# 신호별 스케일 설정 (대시보드용)
SIGNAL_SCALES = {
    'SPEED': 1,
    'ACCELERATOR_PEDAL_PRESSED': 20,
    'BRAKE_PRESSED': 20,
    'BRAKE_PRESSURE': 1/10,
    'STEERING_ANGLE_2': 1/30,
    'STEERING_RATE': 1/20,
    'STEERING_COL_TORQUE': 1/30,
}

# 신호별 스케일 표시 텍스트 (대시보드용)
SIGNAL_SCALE_SUFFIXES = {
    'SPEED': "",
    'ACCELERATOR_PEDAL_PRESSED': " (×20)",
    'BRAKE_PRESSED': " (×20)",
    'BRAKE_PRESSURE': " (÷10)",
    'STEERING_ANGLE_2': " (÷30)",
    'STEERING_RATE': " (÷20)",
    'STEERING_COL_TORQUE': " (÷30)",
} 