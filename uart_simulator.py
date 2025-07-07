#!/usr/bin/env python3
"""
UART 시뮬레이터 - 실제 UART 연결 없이 로그 파일을 시뮬레이션
"""

import time
import serial
import threading
from parser.can_decoder import decode_line
from parser.monitor_core import MonitorCore
from event_logic.event_detector import process_data
import pandas as pd
import os
from datetime import datetime

class UARTSimulator:
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.monitor = MonitorCore()
        self.running = False
        self.cycle_count = 0
        self.event_count = 0
        
    def map_decoded_to_standard_format(self, decoded_data, event_result):
        """디코딩된 데이터를 표준 형식으로 매핑"""
        result = {}
        
        # 디코딩된 모든 신호를 그대로 추가
        for key, value in decoded_data.items():
            try:
                result[key] = float(value)
            except (ValueError, TypeError):
                result[key] = value
        
        # 이벤트 정보는 마지막에 추가
        if event_result and 'event' in event_result:
            result['event'] = event_result['event']
        else:
            result['event'] = 'none'
        
        return result
        
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
        
    def simulate_from_file(self, filename, output_filename=None):
        """로그 파일을 읽어서 시뮬레이션하고 결과를 CSV로 저장"""
        print(f"🚀 UART 시뮬레이션 시작: {filename}")
        
        if not os.path.exists(filename):
            print(f"❌ 파일을 찾을 수 없습니다: {filename}")
            return
            
        # 출력 파일명 생성
        if output_filename is None:
            base_name = os.path.splitext(os.path.basename(filename))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"logs/simulated_{base_name}_{timestamp}.csv"
            
        # 출력 디렉토리 생성
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
        results = []
        cycle_count = 0
        event_count = 0
        time_counter = 0  # 정수 카운터 (0xEA마다 1씩 증가)
        last_seen_ids = {}  # 각 ID별로 마지막에 본 데이터를 저장
        current_time_data = {}  # 현재 시간대의 모든 데이터를 저장
        last_values = {}  # 각 신호별로 마지막 값을 저장
        last_ea_data = None  # 마지막 0xEA 데이터 저장 (연속 체크용)
        
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or 'CAN FD RX:' not in line:
                    continue
                    
                try:
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
                        # 연속된 0xEA 신호 체크
                        current_ea_data = str(decoded)
                        if last_ea_data == current_ea_data:
                            print(f"⚠️ 연속된 0xEA 신호 무시: 라인 {line_num}")
                            continue  # 연속된 신호는 무시
                        
                        last_ea_data = current_ea_data
                        
                        # 이전 시간대 데이터가 있으면 이벤트 처리 및 저장
                        if current_time_data:
                            # 이벤트 감지
                            result = process_data(current_time_data)
                            
                            # 이벤트 정보 업데이트
                            if result and 'event' in result and result['event'] != 'none':
                                current_time_data['event'] = result['event']
                                event_count += 1
                                print(f"   🔥 이벤트 감지: {result['event']}")
                            
                            # none값들을 이전값으로 처리
                            for key, value in current_time_data.items():
                                if key == 'Time' or key == 'event':
                                    continue
                                if value == '' or value is None:
                                    if key in last_values:
                                        current_time_data[key] = last_values[key]
                                else:
                                    last_values[key] = value
                            
                            results.append(current_time_data)
                            print(f"✅ 시간대 처리 완료: {current_time_data.get('Time', 0)}s, 이벤트: {current_time_data.get('event', 'none')}")
                        
                        time_counter += 1
                        cycle_count += 1
                        # 새로운 시간대 시작 (이전 데이터 복사)
                        if results:
                            current_time_data = results[-1].copy()
                        else:
                            current_time_data = {}
                        current_time_data['Time'] = round(time_counter * 0.1, 1)
                        current_time_data['event'] = 'none'
                    
                    # 연속된 신호 체크 (같은 ID의 데이터가 이전과 동일하면 무시)
                    data_key = str(decoded)
                    if can_id in last_seen_ids and last_seen_ids[can_id] == data_key:
                        continue  # 연속된 신호는 무시
                    
                    last_seen_ids[can_id] = data_key
                    
                    # 현재 시간대 데이터에 추가 (이미 있는 값은 덮어쓰기)
                    for key, value in decoded.items():
                        try:
                            current_time_data[key] = float(value)
                        except (ValueError, TypeError):
                            current_time_data[key] = value
                    
                    # 진행상황 출력 (1000주기마다)
                    if cycle_count % 1000 == 0:
                        print(f"   📊 처리된 주기: {cycle_count}, 이벤트: {event_count}")
                        
                except Exception as e:
                    print(f"   ❌ 라인 {line_num} 처리 오류: {e}")
                    continue
        
        # 마지막 시간대 데이터 처리
        if current_time_data:
            # 이벤트 감지
            result = process_data(current_time_data)
            
            # 이벤트 정보 업데이트
            if result and 'event' in result and result['event'] != 'none':
                current_time_data['event'] = result['event']
                event_count += 1
                print(f"   🔥 이벤트 감지: {result['event']}")
            
            # none값들을 이전값으로 처리
            for key, value in current_time_data.items():
                if key == 'Time' or key == 'event':
                    continue
                if value == '' or value is None:
                    if key in last_values:
                        current_time_data[key] = last_values[key]
                else:
                    last_values[key] = value
            
            results.append(current_time_data)
            print(f"✅ 마지막 시간대 처리 완료: {current_time_data.get('Time', 0)}s, 이벤트: {current_time_data.get('event', 'none')}")
        
        # 결과를 DataFrame으로 변환하고 CSV 저장
        if results:
            df = pd.DataFrame(results)
            
            # Time과 event 컬럼을 첫 번째와 마지막으로 이동
            cols = [col for col in df.columns if col not in ['Time', 'event']]
            cols = ['Time'] + cols + ['event']
            df = df[cols]
            
            df.to_csv(output_filename, index=False)
            print(f"✅ 시뮬레이션 완료!")
            print(f"   📁 저장된 파일: {output_filename}")
            print(f"   📊 총 처리 주기: {cycle_count}")
            print(f"   🎯 감지된 이벤트: {event_count}")
        else:
            print("❌ 처리된 데이터가 없습니다.")
            
        return output_filename

def main():
    simulator = UARTSimulator()
    
    # logs/original/ 폴더의 모든 .txt 파일 처리
    original_dir = "logs/original"
    if not os.path.exists(original_dir):
        print(f"❌ {original_dir} 폴더가 없습니다.")
        return
        
    txt_files = [f for f in os.listdir(original_dir) if f.endswith('.txt')]
    if not txt_files:
        print(f"❌ {original_dir} 폴더에 .txt 파일이 없습니다.")
        return
        
    print(f"📁 발견된 파일들: {txt_files}")
    
    for filename in txt_files:
        filepath = os.path.join(original_dir, filename)
        print(f"\n🔄 처리 중: {filename}")
        
        try:
            output_file = simulator.simulate_from_file(filepath)
            if output_file:
                print(f"   ✅ 완료: {output_file}")
        except Exception as e:
            print(f"   ❌ 오류: {e}")

if __name__ == "__main__":
    main() 