# event_logic/rules.py

from collections import deque

class EventDetector:
    """각 이벤트의 on/off 조건을 독립적으로 계산하고 trigger를 생성"""
    
    def __init__(self):
        self.timer = {}
        self.history = deque(maxlen=30)  # 최대 3초 (30 * 0.1초)
        self.delay = {}
        self.current_time = 0.0  # 현재 시간 추적

    def update(self, key, inc, cond):
        self.timer[key] = self.timer.get(key, 0)
        self.timer[key] = self.timer[key] + inc if cond else 0

    def safe_get(self, row, key, default=None):
        """안전하게 값을 가져오는 함수 - 누락된 키는 None 반환"""
        return row.get(key, default)

    def get_recent_data_by_time(self, time_window):
        """지정된 시간 동안의 최근 데이터 반환"""
        cutoff_time = self.current_time - time_window
        recent_data = []
        
        for data in reversed(list(self.history)):
            if data.get('timestamp', 0) >= cutoff_time:
                recent_data.append(data)
            else:
                break
        
        return list(reversed(recent_data))

    def get_speed_at_time(self, time_ago):
        """지정된 시간 전의 속도를 반환"""
        target_time = self.current_time - time_ago
        
        # 히스토리에서 가장 가까운 시간의 속도를 찾기
        closest_speed = 0  # 기본값
        min_time_diff = float('inf')
        
        for data in self.history:
            time_diff = abs(data.get('timestamp', 0) - target_time)
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_speed = data.get('speed', 0)
        
        return closest_speed

    def detect_triggers(self, row, dt=0.1):
        """모든 이벤트의 on/off 조건을 계산하고 trigger 리스트 반환"""
        triggers = []
        
        # 현재 시간 업데이트
        self.current_time += dt
        
        # 필요한 키들이 모두 있는지 확인
        required_keys = ['ACCELERATOR_PEDAL_PRESSED', 'BRAKE_PRESSED', 'SPEED']
        missing_keys = [key for key in required_keys if key not in row]
        
        if missing_keys:
            return triggers
        
        a = row['ACCELERATOR_PEDAL_PRESSED']
        b = row['BRAKE_PRESSED']
        v = row['SPEED']
        p = self.safe_get(row, 'BRAKE_PRESSURE', 0)
        ang = self.safe_get(row, 'STEERING_ANGLE_2', 0)
        rate = self.safe_get(row, 'STEERING_RATE', 0)
        tq = self.safe_get(row, 'STEERING_COL_TORQUE', 0)
        

        
        # 타임스탬프와 함께 히스토리에 저장
        self.history.append({
            'speed': v, 'angle': ang, 'torque': tq, 'rate': rate, 'pressure': p,
            'timestamp': self.current_time
        })

        # PM - 페달 오조작
        if a and b:
            self.update('PM', dt, True)
            if self.timer['PM'] >= 1.0:
                triggers.append('PM_on')
        elif a and not b:
            if 'PM_check' not in self.delay:
                # 가속 페달을 밟기 시작하는 시점의 속도를 start로 사용
                start_speed = v
                self.delay['PM_check'] = {'start': start_speed, 'time': 0}
            self.delay['PM_check']['time'] += dt
            if self.delay['PM_check']['time'] >= 1.0:
                dv = v - self.delay['PM_check']['start']
                condition = (self.delay['PM_check']['start'] < 6 and dv >= 4) or (self.delay['PM_check']['start'] >= 6 and dv >= 8)
                if condition:
                    triggers.append('PM_on')
                del self.delay['PM_check']
        else:
            self.delay.pop('PM_check', None)
            self.update('PM_off_wait', dt, a == 0)
            if self.timer['PM_off_wait'] >= 0.5:
                triggers.append('PM_off')

        # SA - 급가속
        if a and not b:
            if 'SA_pre' not in self.delay:
                # 가속 페달을 밟기 시작하는 시점의 속도를 start로 사용
                start_speed = v
                self.delay['SA_pre'] = {'start': start_speed, 'time': 0}
            self.delay['SA_pre']['time'] += dt
            if self.delay['SA_pre']['time'] >= 0.5:
                dv = v - self.delay['SA_pre']['start']
                condition = (self.delay['SA_pre']['start'] < 6 and dv >= 2) or (self.delay['SA_pre']['start'] >= 6 and dv >= 4)
                if condition:
                    triggers.append('SA_on')
                del self.delay['SA_pre']
        else:
            if 'SA_pre' in self.delay:
                del self.delay['SA_pre']
        
        # SA OFF
        self.update('SA_off_wait', dt, a == 0)
        if self.timer['SA_off_wait'] >= 0.5:
            triggers.append('SA_off')
            self.timer['SA_off_wait'] = 0

        # SB - 급감속 (시간 기준으로 수정)
        if v >= 6 and b:
            self.update('SB_pre', dt, True)
            if self.timer['SB_pre'] >= 0.3:
                # 최근 0.3초 동안의 데이터 확인
                recent_data = self.get_recent_data_by_time(0.3)
                recent_pressures = [h['pressure'] for h in recent_data]
                condition = any(p >= 300 for p in recent_pressures)
                if condition:
                    triggers.append('SB_on')
        else:
            self.timer['SB_pre'] = 0
        
        # SB OFF
        self.update('SB_off_wait', dt, b == 0)
        if self.timer['SB_off_wait'] >= 0.3:
            triggers.append('SB_off')

        # DD - 졸음운전 (간단한 카운트 방식)
        # 졸음운전 조건: 속도≥6, 가속/브레이크 안밟음, 조향 변화 적음, 조향 속도 적음
        dd_condition_met = (v >= 6 and not a and not b and 
                           abs(tq) < 1.0 and abs(ang) < 3.0 and abs(rate) < 30)
        
        if dd_condition_met:
            self.update('DD_count', dt, True)
            if self.timer['DD_count'] >= 3.0:  # 3초(30회) 이상 조건 만족
                triggers.append('DD_on')
        else:
            # 조건이 만족되지 않으면 카운트 리셋
            self.timer['DD_count'] = 0
            self.update('DD_off_wait', dt, a == 1 or b == 1)
            if self.timer['DD_off_wait'] >= 0.3:
                triggers.append('DD_off')

        # SH - 급조향 (시간 기준으로 수정)
        if v >= 6 and abs(rate) >= 100:
            # 최근 0.3초 동안의 데이터 확인
            recent_data = self.get_recent_data_by_time(0.3)
            if len(recent_data) >= 2:  # 최소 2개 샘플 이상
                recent_angles = [h['angle'] for h in recent_data]
                angle_change = max(recent_angles) - min(recent_angles)
                if angle_change > 30:
                    triggers.append('SH_on')
        
        # SH OFF
        self.update('SH_off_wait', dt, abs(rate) < 10)
        if self.timer['SH_off_wait'] >= 1.0:
            triggers.append('SH_off')

        return triggers


class EventManager:
    """trigger와 현재 상태를 받아서 우선순위를 적용하고 최종 이벤트 상태를 관리"""
    
    def __init__(self):
        self.state = {e: False for e in ['PM', 'SA', 'SB', 'DD', 'SH']}
        # 우선순위 순서: PM > DD > SA > SB > SH
        self.priority_order = ["PM", "DD", "SA", "SB", "SH"]

    def check_higher_priority_active(self, event):
        """해당 이벤트보다 높은 우선순위의 이벤트가 활성화되어 있는지 확인"""
        event_index = self.priority_order.index(event)
        for higher_event in self.priority_order[:event_index]:
            if self.state[higher_event]:
                return True
        return False

    def force_off_lower_priority_events(self, higher_event):
        """높은 우선순위 이벤트가 발생하면 낮은 우선순위 이벤트들을 강제 해제"""
        result = []
        higher_index = self.priority_order.index(higher_event)
        
        for lower_event in self.priority_order[higher_index + 1:]:
            if self.state[lower_event]:
                result.append(f"{lower_event}_off")
                self.state[lower_event] = False
        
        return result

    def get_current_event(self):
        """현재 활성화된 이벤트 상태를 반환"""
        for event in self.priority_order:
            if self.state[event]:
                return f"{event}_on"
        return "none"

    def update_state(self, triggers):
        """trigger에 따라 상태를 업데이트하고 현재 활성화된 이벤트 반환"""
        # ON trigger들을 우선순위 순서로 처리
        on_triggers = [t for t in triggers if t.endswith('_on')]
        off_triggers = [t for t in triggers if t.endswith('_off')]
        
        # ON trigger 처리 (우선순위 고려)
        for trigger in on_triggers:
            event_name = trigger.replace('_on', '')
            if not self.state[event_name] and not self.check_higher_priority_active(event_name):
                self.state[event_name] = True
                # 낮은 우선순위 이벤트들 강제 해제
                for lower_event in self.priority_order[self.priority_order.index(event_name) + 1:]:
                    if self.state[lower_event]:
                        self.state[lower_event] = False
        
        # OFF trigger 처리
        for trigger in off_triggers:
            event_name = trigger.replace('_off', '')
            if self.state[event_name]:
                self.state[event_name] = False
        
        # 현재 활성화된 이벤트 반환
        return self.get_current_event()

    def process_triggers(self, triggers):
        """trigger 리스트를 처리하여 우선순위를 적용하고 최종 이벤트 상태 반환"""
        result = []
        
        # ON trigger들을 우선순위 순서로 정렬하여 처리
        on_triggers = [t for t in triggers if t.endswith('_on')]
        off_triggers = [t for t in triggers if t.endswith('_off')]
        
        # ON trigger 처리 (우선순위 고려)
        for trigger in on_triggers:
            event_name = trigger.replace('_on', '')
            if not self.state[event_name] and not self.check_higher_priority_active(event_name):
                result.append(trigger)
                self.state[event_name] = True
                # 낮은 우선순위 이벤트들 강제 해제
                result.extend(self.force_off_lower_priority_events(event_name))
        
        # OFF trigger 처리
        for trigger in off_triggers:
            event_name = trigger.replace('_off', '')
            if self.state[event_name]:
                result.append(trigger)
                self.state[event_name] = False
        
        return result
    



class EventFSM:
    """이벤트 감지와 관리를 통합하는 메인 클래스"""
    
    def __init__(self):
        self.detector = EventDetector()
        self.manager = EventManager()

    def detect(self, row, dt=0.1):
        """이벤트 감지 및 우선순위 적용"""
        # 1. 각 이벤트의 on/off 조건을 독립적으로 계산하여 trigger 생성
        triggers = self.detector.detect_triggers(row, dt)
        
        # 2. trigger와 현재 상태를 받아서 우선순위를 적용하고 최종 이벤트 상태 반환
        result = self.manager.process_triggers(triggers)
        
        return result
    
    def get_current_event(self):
        """현재 활성화된 이벤트 상태를 반환"""
        return self.manager.get_current_event()
    
    def update_state(self, row, dt=0.1):
        """trigger에 따라 상태를 업데이트하고 현재 활성화된 이벤트 반환"""
        triggers = self.detector.detect_triggers(row, dt)
        return self.manager.update_state(triggers)
    
