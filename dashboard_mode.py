# dashboard_mode.py

from fastapi import FastAPI, WebSocket, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn, os, pandas as pd, asyncio, signal, sys
from parser.monitor_core import MonitorCore
from parser.can_decoder import decode_line
from parser.log_buffer import LogBuffer
from event_logic.event_detector import process_data
from config.signals import STANDARD_COLUMNS, VISUALIZATION_SIGNALS

from io import StringIO
import datetime
import threading
import time

try:
    from serial import Serial
except ImportError:
    Serial = None

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

clients = set()
monitor = MonitorCore()
log_buffer = monitor.log_buffer
serial = None
logging_start_time = None  # 로깅 시작 시간 추적
csv_save_timer = None  # CSV 저장 타이머
csv_filename = None  # CSV 파일명
csv_data_buffer = []  # CSV 데이터 버퍼
csv_save_lock = threading.Lock()  # CSV 저장용 락

def signal_handler(signum, frame):
    """시그널 핸들러 - 안전한 종료"""
    print(f"\n🛑 종료 신호 수신 (시그널: {signum})")
    print("📊 데이터 저장 중...")
    
    # CSV 최종 저장
    if monitor.csv_data_buffer:
        monitor.stop_csv_logging()
        print(f"💾 최종 CSV 저장 완료: {monitor.csv_filename}")
    
    # 시리얼 연결 종료
    global serial
    if serial:
        serial.close()
        print("🔌 UART 연결 종료")
    
    print("✅ 프로그램 안전 종료 완료")
    sys.exit(0)

# 시그널 핸들러 설정
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def process_csv_simple(df):
    """CSV 데이터를 단순히 처리하는 함수 (이미 0xEA 기준으로 처리된 데이터)"""
    processed = []
    
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        
        # 대시보드용: 모든 시각화 신호가 result에 없으면 None으로 채움
        for sig in VISUALIZATION_SIGNALS:
            if sig == "SPEED":
                # SPEED는 원본 데이터에서 계산
                if all(col in row_dict for col in ['WHEEL_SPEED_1','WHEEL_SPEED_2','WHEEL_SPEED_3','WHEEL_SPEED_4']):
                    row_dict['SPEED'] = sum(float(row_dict[col]) for col in ['WHEEL_SPEED_1','WHEEL_SPEED_2','WHEEL_SPEED_3','WHEEL_SPEED_4']) / 4
                else:
                    row_dict['SPEED'] = None
            elif sig not in row_dict:
                row_dict[sig] = None
        
        # Trigger와 Event 상태 로깅 추가 (실시간과 동일한 방식 사용)
        try:
            # process_data 함수를 사용하여 실시간과 동일한 방식으로 처리
            processed_row = process_data(row_dict)
            row_dict['trigger'] = processed_row.get('trigger', 'none')
            row_dict['event'] = processed_row.get('event', 'none')
            
        except Exception as e:
            row_dict['trigger'] = 'error'  # 오류 발생 시 'error'
            row_dict['event'] = 'error'
        
        processed.append(row_dict)
    
    return processed

def to_jsonable(data):
    # 모든 값을 JSON 직렬화 가능한 값으로 변환
    def convert(val):
        if isinstance(val, (int, float, str, type(None))):
            return val
        return str(val)
    return {k: convert(v) for k, v in data.items()}

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    print("INFO: connection open")
    try:
        last_sent_time = None
        check_count = 0
        while True:
            await asyncio.sleep(0.05)  # 0.05초 간격으로 더 빠르게 체크
            check_count += 1
            
            # 메모리에서 최신 데이터 가져오기 (매우 빠름)
            latest_data = monitor.get_latest_data_for_dashboard()
            
            if latest_data:
                # 로깅 시작 시간 정보 추가
                if logging_start_time:
                    latest_data['logging_start_time'] = logging_start_time.isoformat()
                    latest_data['logging_duration'] = (datetime.datetime.now() - logging_start_time).total_seconds()
                
                # SPEED 계산 추가
                if 'WHEEL_SPEED_1' in latest_data and 'WHEEL_SPEED_2' in latest_data and 'WHEEL_SPEED_3' in latest_data and 'WHEEL_SPEED_4' in latest_data:
                    try:
                        speed = (float(latest_data['WHEEL_SPEED_1']) + float(latest_data['WHEEL_SPEED_2']) + 
                                float(latest_data['WHEEL_SPEED_3']) + float(latest_data['WHEEL_SPEED_4'])) / 4
                        latest_data['SPEED'] = speed
                    except (ValueError, TypeError):
                        latest_data['SPEED'] = 0
                
                # 새로운 데이터인 경우에만 전송
                current_time = latest_data.get('Time', 0)
                if last_sent_time != current_time:
                    await websocket.send_json(to_jsonable(latest_data))
                    last_sent_time = current_time
            
            else:
                # 20번마다 한 번씩 상태 출력
                if check_count % 20 == 0:
                    pass
                    
    except Exception as e:
        print(f"INFO: connection closed - {e}")
    finally:
        clients.discard(websocket)

@app.post("/start_logging")
async def start_logging():
    global serial, logging_start_time
    if Serial is None:
        return "❌ pyserial 미설치"
    try:
        # 기존 연결이 있으면 종료
        if serial:
            serial.close()
            serial = None
        
        # 모니터링 재시작
        monitor.running = True
        
        serial = Serial("/dev/ttyS0", 115200, timeout=1)  # ttyUSB0 → ttyS0로 변경
        logging_start_time = datetime.datetime.now()  # 로깅 시작 시간 기록
        
        # CSV 로깅 시작
        monitor.start_csv_logging()
        
        asyncio.create_task(monitor.start(serial))
        start_time_str = logging_start_time.strftime("%Y-%m-%d %H:%M:%S")
        return f"✅ 로깅 시작됨 ({start_time_str})"
    except Exception as e:
        return f"❌ UART 연결 실패: {e}"

@app.post("/stop_logging")
async def stop_logging():
    global serial, logging_start_time
    try:
        # 모니터링 중지
        monitor.running = False
        
        # CSV 최종 저장
        if monitor.csv_data_buffer:
            monitor.stop_csv_logging()
            print(f"💾 최종 CSV 저장 완료: {monitor.csv_filename}")
        
        # 시리얼 연결 종료
        if serial:
            serial.close()
            serial = None
            print("🔌 UART 연결 종료")
        
        # 로깅 시간 계산
        if logging_start_time:
            duration = (datetime.datetime.now() - logging_start_time).total_seconds()
            logging_start_time = None
            return f"🛑 로깅 종료됨 (총 {duration:.1f}초, 데이터 자동 저장 완료)"
        else:
            return "🛑 로깅 종료됨 (데이터 자동 저장 완료)"
            
    except Exception as e:
        print(f"❌ 로깅 종료 중 오류: {e}")
        return f"❌ 로깅 종료 중 오류: {e}"

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    try:
        if not file.filename:
            return JSONResponse(content={"success": False, "message": "파일이 선택되지 않았습니다."})

        print(f"📁 업로드 요청 파일명: {file.filename}")
        contents = await file.read()
        csv_data = contents.decode("utf-8")
        df = pd.read_csv(StringIO(csv_data))
        # 컬럼명을 모두 대문자화(혹시 소문자 업로드 대비) - Time과 event는 제외
        df.columns = [col.upper() if col not in ['Time', 'event'] else col for col in df.columns]
        df = df.ffill().fillna(0)

        # 단순 처리 (이미 0xEA 기준으로 처리된 데이터)
        processed = process_csv_simple(df)



        # 파일 저장
        logs_dir = "logs"
        os.makedirs(logs_dir, exist_ok=True)
        filename = file.filename
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(filename)
        new_filename = f"{base}_{ts}{ext}"
        final_path = os.path.join(logs_dir, new_filename)
        temp_path = os.path.join(logs_dir, f"temp_{new_filename}")

        # config에서 정의된 컬럼 순서로 저장 (DBC 신호명 기준)
        result_df = pd.DataFrame(processed)
        for col in STANDARD_COLUMNS:
            if col not in result_df.columns:
                result_df[col] = 0
        
        # trigger 열이 없으면 추가
        if 'trigger' not in result_df.columns:
            result_df['trigger'] = 'none'
        
        # 컬럼 순서: STANDARD_COLUMNS + event + trigger
        result_df = result_df[STANDARD_COLUMNS + ['event', 'trigger']]
        result_df.to_csv(temp_path, index=False)
        os.rename(temp_path, final_path)
        print(f"✅ CSV 안전 저장 완료 → {final_path}")
        
        # JSON 응답으로 파일 데이터 반환
        return JSONResponse(content={
            "success": True,
            "message": f"업로드 및 이벤트 분석 완료: {new_filename}",
            "data": processed,
            "filename": new_filename,
            "total_points": len(processed)
        })
        
    except Exception as e:
        print(f"❌ 업로드 처리 중 오류: {e}")
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(content={"success": False, "message": f"처리 중 오류 발생: {str(e)}"})

@app.post("/shutdown")
async def shutdown(request: Request):
    print("🛑 브라우저 종료 감지 → 서버 종료 중")
    os._exit(0)
