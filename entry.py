import sys
import uvicorn
import webbrowser
import threading
import asyncio

def open_browser():
    import time
    time.sleep(1.5)  # 서버가 완전히 실행되기까지 약간의 지연
    webbrowser.open("http://localhost:8000")

async def run_monitor():
    from parser.monitor_core import MonitorCore
    from serial import Serial
    monitor = MonitorCore()
    serial = Serial("/dev/ttyS0", 115200, timeout=1)  # ttyUSB0 → ttyS0로 변경
    await monitor.start(serial)

if __name__ == "__main__":
    mode = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    if mode == 1:
        print("✅ 대시보드 모드 실행 중... (http://localhost:8000)")
        threading.Thread(target=open_browser).start()
        uvicorn.run("dashboard_mode:app", host="0.0.0.0", port=8000)
    else:
        print("✅ 헤드리스 모드 실행 중...")
        asyncio.run(run_monitor())
