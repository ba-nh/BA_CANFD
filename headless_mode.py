# headless_mode.py
from parser.monitor_core import MonitorCore
from parser.event_engine import save_log
import time

if __name__ == "__main__":
    print("🟢 헤드리스 판단 모드 시작")
    monitor = MonitorCore()
    monitor.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 종료 중...")
        monitor.stop()
        save_log()
