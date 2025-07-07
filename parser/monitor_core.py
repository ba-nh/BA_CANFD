# parser/monitor_core.py

import asyncio
import signal
import sys
import os
import datetime
import threading
import time
from collections import defaultdict
from parser.can_decoder import decode_line
from parser.log_buffer import LogBuffer
from event_logic.event_detector import process_data

class MonitorCore:
    def __init__(self):
        self.log_buffer = LogBuffer()
        self.running = False
        self.time_counter = 0  # 시간 카운터 추가
        self.current_time_data = {}
        self.last_seen_ids = {}  # 각 ID별로 마지막에 본 데이터를 저장
        self.last_ea_data = None  # 마지막 0xEA 데이터 저장 (연속 체크용)
        
        # CSV 저장 관련 변수들
        self.csv_save_timer = None  # CSV 저장 타이머
        self.csv_filename = None  # CSV 파일명
        self.csv_data_buffer = []  # CSV 데이터 버퍼
        self.csv_save_lock = threading.Lock()  # CSV 저장용 락
        self.logging_start_time = None  # 로깅 시작 시간
        
        # 실시간 그래프용 메모리 저장
        self.latest_data_for_dashboard = None  # 대시보드용 최신 데이터
        self.dashboard_data_lock = threading.Lock()  # 대시보드 데이터용 락
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """시그널 핸들러 - 안전한 종료"""
        print(f"\n🛑 종료 신호 수신 (시그널: {signum})")
        print("📊 데이터 저장 중...")
        self.running = False
        
        # CSV 최종 저장
        if self.csv_data_buffer:
            self.stop_csv_logging() # 기존 함수 사용
            print(f"💾 최종 CSV 저장 완료: {self.csv_filename}")
        
        print("✅ 프로그램 안전 종료 완료")
        sys.exit(0)

    def extract_can_id(self, line):
        """CAN 라인에서 ID를 추출"""
        try:
            if line.startswith("CAN FD RX: "):
                line = line[11:]  # "CAN FD RX: " 제거
            
            # ID 부분 추출
            id_part = line.split(',')[0]  # "ID=0xEA"
            msg_id = int(id_part.split('=')[1], 16)
            return msg_id
        except:
            return None

    def process_ea_signal(self, decoded_data):
        """0xEA 신호 처리 - 시간 증가 및 이벤트 감지"""
        # 연속된 0xEA 신호 체크
        current_ea_data = str(decoded_data)
        if self.last_ea_data == current_ea_data:
            print(f"⚠️ 연속된 0xEA 신호 무시: {current_ea_data[:50]}...")
            return False  # 연속된 신호는 무시
        
        self.last_ea_data = current_ea_data
        
        # 이전 시간대 데이터가 있으면 처리
        if self.current_time_data:
            # 이벤트 감지
            processed = process_data(self.current_time_data)
            self.log_buffer.add(processed)
            
            # 대시보드용 메모리에 최신 데이터 저장 (빠른 접근용)
            with self.dashboard_data_lock:
                self.latest_data_for_dashboard = processed.copy()
                print(f"💾 대시보드 메모리 저장: Time={processed.get('Time', 0)}, 이벤트={processed.get('event', 'none')}")
            
            # CSV 버퍼에 추가
            self.add_to_csv_buffer(processed)
            
            # Time 기준으로 0.1초마다 CSV 저장
            self.save_csv_by_time()
            
            # 이벤트 정보 추출
            event = processed.get('event', 'none')
            trigger = processed.get('trigger', 'none')
            
            # 이벤트가 감지되었을 때 터미널에 알림 출력
            if event != 'none':
                # _on 접미사 제거
                event_name = event.replace('_on', '')
                print(f"🚨 이벤트 감지! 시간: {self.time_counter * 0.1:.1f}s, 이벤트: {event_name}")
            else:
                print(f"✅ 시간대 처리 완료: {self.time_counter * 0.1:.1f}s, 이벤트: {event}")
        
        self.time_counter += 1
        # 새로운 시간대 시작 (이전 데이터 복사)
        if self.log_buffer.buffer:
            self.current_time_data = self.log_buffer.buffer[-1].copy()
        else:
            self.current_time_data = {}
        self.current_time_data['Time'] = round(self.time_counter * 0.1, 1)
        self.current_time_data['event'] = 'none'
        
        return True  # 새로운 0xEA 신호 처리됨

    def update_csv_header(self, sample_row):
        """실제 데이터에 따라 CSV 헤더 동적 업데이트"""
        if not self.csv_filename:
            return
            
        # 현재 파일의 모든 데이터를 읽기
        with open(self.csv_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not lines:
            return
            
        # 실제 데이터에 있는 모든 키를 순서대로 헤더 생성
        header_parts = ['Time']  # Time은 항상 첫 번째
        
        # Time, event, trigger를 제외한 모든 신호를 순서대로 추가
        for key in sample_row.keys():
            if key not in ['Time', 'event', 'trigger']:
                header_parts.append(key)
        
        # event와 trigger는 항상 마지막
        header_parts.extend(['event', 'trigger'])
        
        # 새로운 헤더 생성
        new_header = ','.join(header_parts) + '\n'
        
        # 기존 데이터를 새로운 컬럼 구조에 맞게 조정
        adjusted_lines = [new_header]  # 새로운 헤더로 시작
        
        for i, line in enumerate(lines[1:], 1):  # 헤더 제외하고 처리
            if line.strip():
                # 기존 데이터를 파싱
                old_parts = line.strip().split(',')
                old_data = {}
                
                # 기존 헤더와 매칭
                if len(lines) > 0:
                    old_header = lines[0].strip().split(',')
                    for j, key in enumerate(old_header):
                        if j < len(old_parts):
                            old_data[key] = old_parts[j]
                
                # 새로운 컬럼 순서에 맞게 데이터 재구성
                new_parts = []
                for key in header_parts:
                    if key in old_data:
                        new_parts.append(old_data[key])
                    else:
                        # 없는 컬럼은 빈 값으로 채움
                        new_parts.append('')
                
                adjusted_lines.append(','.join(new_parts) + '\n')
        
        # 파일 다시 쓰기
        with open(self.csv_filename, 'w', encoding='utf-8') as f:
            f.writelines(adjusted_lines)
        
        print(f"📊 CSV 헤더 업데이트: {len(header_parts)}개 컬럼")
        print(f"📊 컬럼 순서: {', '.join(header_parts)}")

    def add_can_data(self, can_id, decoded_data):
        """CAN 데이터를 현재 시간대에 추가 - 모든 해석된 데이터 저장"""
        # 연속된 신호 체크 (같은 ID의 데이터가 이전과 동일하면 무시)
        data_key = str(decoded_data)
        if can_id in self.last_seen_ids and self.last_seen_ids[can_id] == data_key:
            return False  # 연속된 신호는 무시
        
        self.last_seen_ids[can_id] = data_key
        
        # 현재 시간대 데이터에 모든 해석된 데이터 추가
        new_columns_added = False
        for key, value in decoded_data.items():
            # 새로운 신호가 들어오면 알림 (값 설정 전에 체크)
            if key not in self.current_time_data:
                new_columns_added = True
                print(f"📊 새로운 신호 발견: {key}")
            
            try:
                # 숫자로 변환 가능하면 숫자로, 아니면 문자열로 저장
                if isinstance(value, (int, float)):
                    self.current_time_data[key] = value
                else:
                    # 문자열을 숫자로 변환 시도
                    try:
                        self.current_time_data[key] = float(value)
                    except (ValueError, TypeError):
                        self.current_time_data[key] = value
            except (ValueError, TypeError):
                self.current_time_data[key] = value
        
        # 새로운 컬럼이 추가되면 CSV 헤더 업데이트
        if new_columns_added:
            self.update_csv_header(self.current_time_data)
        
        return True  # 새로운 데이터 추가됨

    def compute_speed(self, row):
        keys = ['WHEEL_SPEED_1', 'WHEEL_SPEED_2', 'WHEEL_SPEED_3', 'WHEEL_SPEED_4']
        if all(k in row for k in keys):
            row['SPEED'] = sum(row[k] for k in keys) / 4
        else:
            row['SPEED'] = 0
        return row

    def clean_row(self, row):
        # 필요한 신호들만 추출하고 정리
        cleaned = {}
        for key in ['ACCELERATOR_PEDAL_PRESSED', 'BRAKE_PRESSED', 'BRAKE_PRESSURE', 
                   'STEERING_ANGLE_2', 'STEERING_RATE', 'STEERING_COL_TORQUE',
                   'WHEEL_SPEED_1', 'WHEEL_SPEED_2', 'WHEEL_SPEED_3', 'WHEEL_SPEED_4', 'SPEED']:
            if key in row:
                cleaned[key] = row[key]
        return cleaned

    def start_csv_logging(self):
        """CSV 로깅 시작 - 동적 컬럼 처리"""
        self.logging_start_time = datetime.datetime.now()
        timestamp = self.logging_start_time.strftime("%Y%m%d_%H%M%S")
        self.csv_filename = f"logs/realtime_log_{timestamp}.csv"
        
        # logs 디렉토리 생성
        os.makedirs("logs", exist_ok=True)
        
        # 초기 CSV 헤더 작성 (Time, event, trigger만)
        header = "Time,event,trigger\n"
        
        with open(self.csv_filename, 'w', encoding='utf-8') as f:
            f.write(header)
        
        print(f"📁 CSV 로깅 시작: {self.csv_filename}")
        print(f"📊 초기 컬럼: Time, event, trigger")
        print(f"📊 추가 신호는 실제 데이터에 따라 동적으로 추가됩니다.")
        print(f"📊 Time 기준으로 0.1초마다 저장")

    def add_to_csv_buffer(self, row):
        """CSV 버퍼에 데이터 추가 - 실제 들어오는 모든 신호를 동적으로 저장"""
        if not self.csv_filename:
            return
            
        # 실제 데이터에 있는 모든 키를 동적으로 처리
        csv_parts = []
        
        # Time 컬럼 (항상 첫 번째)
        csv_parts.append(f"{row.get('Time', 0):.1f}")
        
        # Time, event, trigger를 제외한 모든 신호 데이터를 순서대로 추가
        for key, value in row.items():
            if key in ['Time', 'event', 'trigger']:
                continue
            if isinstance(value, (int, float)):
                csv_parts.append(str(value))
            else:
                csv_parts.append(str(value))
        
        # event와 trigger 컬럼 (항상 마지막)
        csv_parts.append(row.get('event', 'none'))
        csv_parts.append(row.get('trigger', 'none'))
        
        # CSV 라인 생성
        csv_line = ','.join(csv_parts)
        
        with self.csv_save_lock:
            self.csv_data_buffer.append(csv_line)

    def save_csv_by_time(self):
        """Time 기준으로 0.1초마다 CSV 저장"""
        if not self.csv_filename or not self.csv_data_buffer:
            return
            
        with self.csv_save_lock:
            # 버퍼의 데이터를 CSV에 추가
            with open(self.csv_filename, 'a', encoding='utf-8') as f:
                for row_data in self.csv_data_buffer:
                    f.write(row_data + '\n')
            
            print(f"💾 Time 기준 CSV 저장 완료: {len(self.csv_data_buffer)}개 데이터")
            self.csv_data_buffer.clear()

    def stop_csv_logging(self):
        """CSV 로깅 종료 및 최종 저장"""
        if not self.csv_filename:
            return
            
        # 남은 버퍼 데이터 저장
        with self.csv_save_lock:
            if self.csv_data_buffer:
                with open(self.csv_filename, 'a', encoding='utf-8') as f:
                    for row_data in self.csv_data_buffer:
                        f.write(row_data + '\n')
                
                print(f"💾 최종 CSV 저장 완료: {len(self.csv_data_buffer)}개 데이터")
                self.csv_data_buffer.clear()
        
        # 로깅 시간 계산
        if self.logging_start_time:
            duration = (datetime.datetime.now() - self.logging_start_time).total_seconds()
            print(f"📊 총 로깅 시간: {duration:.1f}초")
            print(f"📁 저장된 파일: {self.csv_filename}")

    def get_latest_data_for_dashboard(self):
        """대시보드용 최신 데이터 반환 (메모리에서 빠르게 접근)"""
        with self.dashboard_data_lock:
            if self.latest_data_for_dashboard:
                return self.latest_data_for_dashboard.copy()
        
        # 메모리에 없으면 log_buffer에서 확인
        if self.log_buffer.buffer:
            return self.log_buffer.buffer[-1].copy()
        
        # 또는 현재 시간대 데이터 확인
        elif self.current_time_data and self.current_time_data.get('Time'):
            return self.current_time_data.copy()
        
        return None

    async def start(self, serial):
        self.running = True
        
        # CSV 로깅 시작
        self.start_csv_logging()
        
        while self.running:
            try:
                # 비동기로 시리얼 읽기
                line = await asyncio.get_event_loop().run_in_executor(
                    None, serial.readline
                )
                
                # UTF-8 디코딩 오류 처리
                try:
                    line = line.decode('utf-8', errors='ignore').strip()
                except (UnicodeDecodeError, AttributeError):
                    # 바이너리 데이터나 None인 경우 건너뛰기
                    continue
                
                if line and 'CAN FD RX:' in line:
                    # CAN ID 추출
                    can_id = self.extract_can_id(line)
                    if can_id is None:
                        continue
                    
                    # CAN 디코딩
                    decoded = decode_line(line)
                    if not decoded:
                        continue
                    
                    # 0xEA 신호 처리
                    if can_id == 0xEA:
                        self.process_ea_signal(decoded)
                    else:
                        # 다른 CAN ID 데이터 추가
                        self.add_can_data(can_id, decoded)
                        
                # CPU 사용량을 줄이기 위해 짧은 대기
                await asyncio.sleep(0.001)
                        
            except Exception as e:
                print(f"Monitor error: {e}")
                # 오류가 발생해도 계속 실행
                await asyncio.sleep(0.1)
                continue
        
        # CSV 로깅 종료
        self.stop_csv_logging()
        serial.close()

    def stop(self):
        self.running = False
        # CSV 로깅 종료
        self.stop_csv_logging()
