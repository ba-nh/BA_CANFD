# event_logic/event_detector.py

from event_logic.rules import EventFSM

fsm = EventFSM()

def ensure_signals(row):
    # DBC 기준 컬럼명 사용 (CSV 파일에 speed 컬럼이 없으므로)
    signal_mapping = {
        'SPEED': ['WHEEL_SPEED_1', 'WHEEL_SPEED_2', 'WHEEL_SPEED_3', 'WHEEL_SPEED_4'],
        'ACCELERATOR_PEDAL_PRESSED': ['ACCELERATOR_PEDAL_PRESSED'],
        'BRAKE_PRESSED': ['BRAKE_PRESSED'],
        'BRAKE_PRESSURE': ['BRAKE_PRESSURE'],
        'STEERING_ANGLE_2': ['STEERING_ANGLE_2'],
        'STEERING_RATE': ['STEERING_RATE'],
        'STEERING_COL_TORQUE': ['STEERING_COL_TORQUE']
    }
    
    for target_key, source_keys in signal_mapping.items():
        if target_key not in row:
            if target_key == 'SPEED':
                # SPEED는 WHEEL_SPEED_1~4의 평균으로 계산
                if all(k in row for k in source_keys):
                    try:
                        row[target_key] = sum(float(row[k]) for k in source_keys) / 4
                    except Exception:
                        row[target_key] = 0
                else:
                    row[target_key] = 0
            else:
                # 다른 신호들은 해당 컬럼이 있으면 사용, 없으면 0
                found = False
                for source_key in source_keys:
                    if source_key in row:
                        row[target_key] = row[source_key]
                        found = True
                        break
                if not found:
                    row[target_key] = 0
    
    return row

def process_data(row):
    row = ensure_signals(row)
    
    # FSM에 SPEED가 포함된 데이터 전달하여 trigger 생성
    triggers = fsm.detect(row)
    
    result = row.copy()
    # SPEED 컬럼은 저장하지 않음 (계산된 값이므로)
    if 'SPEED' in result:
        result.pop('SPEED')
    
    # trigger 컬럼 추가
    if triggers:
        result['trigger'] = ', '.join(triggers)
    else:
        result['trigger'] = 'none'
    
    # 현재 활성화된 이벤트 상태를 event 컬럼에 설정
    current_event = fsm.get_current_event()
    result['event'] = current_event
    
    # 컬럼 순서: 기존 컬럼(단, event, trigger 제외) + trigger + event
    cols = [c for c in result.keys() if c not in ['event', 'trigger']] + ['trigger', 'event']
    return {k: result[k] for k in cols}
