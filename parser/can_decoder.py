# parser/can_decoder.py
import cantools
import os

dbc_path = "dbc/openDBC_현대기아.dbc"
dbc = cantools.database.load_file(dbc_path)

def decode_line(line):
    """
    "CAN FD RX: ID=0x123, DLC=24, Data=11 22 33 44 55 66 77 88" 형식의 문자열 → 신호 dict 변환
    """
    try:
        # CAN FD RX: 접두사 제거
        if line.startswith("CAN FD RX: "):
            line = line[11:]  # "CAN FD RX: " 제거
        
        # ID 부분 추출
        id_part = line.split(',')[0]  # "ID=0xEA"
        msg_id = int(id_part.split('=')[1], 16)
        
        # Data 부분 추출
        data_part = line.split('Data=')[1]  # "7E 41 BB 00 01 41 00 00 01 08 00 10 00 00 00 00 AC FF 00 00 00 00 00 00"
        data_bytes = bytes(int(b, 16) for b in data_part.split())
        
        # DBC에서 메시지 찾기 및 디코딩
        msg = dbc.get_message_by_frame_id(msg_id)
        decoded = msg.decode(data_bytes)
        
        # DBC 신호명을 그대로 반환 (매핑 없음)
        return decoded
    except Exception as e:
        # 디버깅을 위한 에러 출력 (선택사항)
        # print(f"Decode error for line: {line.strip()}, Error: {e}")
        return {}
