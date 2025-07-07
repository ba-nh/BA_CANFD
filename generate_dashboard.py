# generate_dashboard.py
# config/signals.py의 VISUALIZATION_SIGNALS를 기반으로 대시보드 HTML을 자동으로 생성

import os
from config.signals import VISUALIZATION_SIGNALS, SIGNAL_COLORS, SIGNAL_SCALES, SIGNAL_SCALE_SUFFIXES

def generate_dashboard_html():
    """config/signals.py의 VISUALIZATION_SIGNALS를 기반으로 대시보드 HTML을 자동 생성"""
    
    print("🔧 대시보드 HTML 자동 생성 중...")
    print(f"📊 config/signals.py에서 정의된 시각화 신호: {len(VISUALIZATION_SIGNALS)}개")
    
    # VISUALIZATION_SIGNALS 사용
    signals = VISUALIZATION_SIGNALS
    
    print(f"📈 대시보드에 추가될 신호들:")
    for signal in signals:
        color = SIGNAL_COLORS.get(signal, "#000000")
        scale = SIGNAL_SCALES.get(signal, 1)
        suffix = SIGNAL_SCALE_SUFFIXES.get(signal, "")
        print(f"   • {signal}{suffix} (색상: {color}, 스케일: {scale})")
    
    # HTML 템플릿 생성
    html_content = generate_html_template(signals)
    
    # 파일 저장
    output_path = "static/index.html"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ 대시보드 HTML 생성 완료: {output_path}")
    print(f"📈 추가된 신호: {len(signals)}개")

def generate_html_template(signals):
    """HTML 템플릿 생성"""
    
    # 신호 체크박스 HTML 생성
    signal_checkboxes = []
    for signal in signals:
        # config에서 정의된 색상과 스케일 설정
        color = SIGNAL_COLORS.get(signal, "#000000")
        scale = SIGNAL_SCALES.get(signal, 1)
        suffix = SIGNAL_SCALE_SUFFIXES.get(signal, "")
        
        checkbox_html = f'<label><input type="checkbox" class="sig" value="{signal}" checked> {signal}{suffix}</label>'
        signal_checkboxes.append(checkbox_html)
    
    signal_checkboxes_html = '\n    '.join(signal_checkboxes)
    
    # JavaScript 신호 설정 생성
    signal_colors_js = []
    scale_map_js = []
    scale_suffix_js = []
    
    for signal in signals:
        color = SIGNAL_COLORS.get(signal, "#000000")
        scale = SIGNAL_SCALES.get(signal, 1)
        suffix = SIGNAL_SCALE_SUFFIXES.get(signal, "")
        
        signal_colors_js.append(f'      {signal}: "{color}"')
        scale_map_js.append(f'      {signal}: {scale}')
        scale_suffix_js.append(f'      {signal}: "{suffix}"')
    
    signal_colors_js_str = ',\n'.join(signal_colors_js)
    scale_map_js_str = ',\n'.join(scale_map_js)
    scale_suffix_js_str = ',\n'.join(scale_suffix_js)
    
    html_template = f'''<!DOCTYPE html>
<html>
<head>
  <title>주행 상황 모니터링</title>
  <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
  <style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .top-right {{ position: absolute; top: 20px; right: 20px; text-align: right; }}
    .checkbox-group {{ margin-bottom: 10px; }}
    label {{ margin-right: 10px; }}
    #plot-title h1 {{
      font-size: 32px;
      margin-bottom: 5px;
    }}
    #event-title {{
      text-align: center;
      margin-top: 20px;
      margin-bottom: 10px;
    }}
    #event-title h2 {{
      font-size: 32px;
      margin: 0;
      color: black;
    }}
    
    /* 재생 속도 버튼 스타일 */
    .speed-btn {{
      margin: 0 5px;
      padding: 5px 10px;
      border: 1px solid #ccc;
      background: #f8f9fa;
      cursor: pointer;
      border-radius: 3px;
    }}
    
    .speed-btn:hover {{
      background: #e9ecef;
    }}
    
    .speed-btn.active {{
      background: #007bff;
      color: white;
      border-color: #007bff;
    }}
    
    #play-pause-btn {{
      margin-left: 15px;
      padding: 5px 15px;
      border: 1px solid #28a745;
      background: #28a745;
      color: white;
      cursor: pointer;
      border-radius: 3px;
    }}
    
    #play-pause-btn:hover {{
      background: #218838;
    }}
    
    #play-pause-btn.paused {{
      background: #dc3545;
      border-color: #dc3545;
    }}
    
    #play-pause-btn.paused:hover {{
      background: #c82333;
    }}
  </style>
</head>
<body>
  <!-- ✅ 타이틀 -->
  <div id="plot-title"><h1>🚗 주행 상황 모니터링</h1></div>

  <!-- ✅ 오른쪽 상단 버튼 -->
  <div class="top-right">
    <form id="upload-form" enctype="multipart/form-data" style="display:inline;">
      <input type="file" name="file" accept=".csv" required>
      <button type="submit">📤 업로드</button>
    </form>
    <button onclick="toggleLogging(true)">🔴 로깅 시작</button>
    <button onclick="toggleLogging(false)">⏹️ 로깅 종료</button>
  </div>

  <!-- ✅ 신호 체크박스 -->
  <div class="checkbox-group">
    <strong>📈 Signals:</strong>
    {signal_checkboxes_html}
  </div>

  <!-- ✅ 이벤트 체크박스 -->
  <div class="checkbox-group">
    <strong>🚨 Events:</strong>
    <label style="color:#FF4C4C"><input type="checkbox" class="evt" value="PM" checked> PM(페달 오조작)</label>
    <label style="color:#AAAAAA"><input type="checkbox" class="evt" value="DD" checked> DD(졸음 운전)</label>
    <label style="color:#FFA500"><input type="checkbox" class="evt" value="SA" checked> SA(급가속)</label>
    <label style="color:#007BFF"><input type="checkbox" class="evt" value="SB" checked> SB(급제동)</label>
    <label style="color:#9933FF"><input type="checkbox" class="evt" value="SH" checked> SH(급조향)</label>
  </div>

  <!-- ✅ 실시간 이벤트 표시 (차트 위 중앙) -->
  <div id="event-title"><h2>실시간 주행 상태</h2></div>

  <!-- ✅ 실시간 상태 표시기 -->
  <div id="status-indicator" style="text-align: center; margin: 10px 0; font-size: 14px; color: #666;">
    <span id="current-time">시간: --</span> | 
    <span id="update-interval">업데이트: 0.1초</span> | 
    <span id="data-points">데이터 포인트: 0</span> | 
    <span id="logging-time">로깅: --</span> | 
    <span id="view-mode">뷰: 실시간</span>
  </div>

  <!-- ✅ 재생 속도 컨트롤 -->
  <div id="playback-controls" style="text-align: center; margin: 10px 0; display: none;">
    <strong>🎬 재생 속도:</strong>
    <button onclick="setPlaybackSpeed(0.25)" class="speed-btn" data-speed="0.25">0.25x</button>
    <button onclick="setPlaybackSpeed(0.5)" class="speed-btn" data-speed="0.5">0.5x</button>
    <button onclick="setPlaybackSpeed(1)" class="speed-btn active" data-speed="1">1x</button>
    <button onclick="setPlaybackSpeed(2)" class="speed-btn" data-speed="2">2x</button>
    <button onclick="setPlaybackSpeed(5)" class="speed-btn" data-speed="5">5x</button>
    <button onclick="setPlaybackSpeed(10)" class="speed-btn" data-speed="10">10x</button>
    <button onclick="togglePlayback()" id="play-pause-btn">⏸️ 일시정지</button>
  </div>

  <!-- ✅ 그래프 이동 컨트롤 -->
  <div id="graph-controls" style="text-align: center; margin: 10px 0;">
    <button onclick="moveGraph(-10)">⏪ 10초 뒤로</button>
    <button onclick="moveGraph(-5)">⏪ 5초 뒤로</button>
    <button onclick="moveGraph(5)">5초 앞으로 ⏩</button>
    <button onclick="moveGraph(10)">10초 앞으로 ⏩</button>
    <button onclick="resetGraphView()">🔄 실시간으로</button>
  </div>

  <!-- ✅ 그래프 영역 -->
  <div id="plot" style="width:100%; height:600px;"></div>

  <script>
    let socket = null;
    const buffer = [];
    const maxWindow = 30;  // 30초 윈도우
    const maxPoints = 36000;
    const sampleInterval = 0.1;  // 0.1초 간격으로 업데이트
    let initialized = false;
    const shapes = [];
    const annotations = [];
    const eventRanges = {{}};
    let activeEvents = new Set();
    let updateTimer = null;  // 업데이트 타이머
    let lastUpdateTime = 0;  // 마지막 업데이트 시간
    let loggingTimer = null;  // 로깅 시간 업데이트 타이머
    let manualViewMode = false;  // 수동 뷰 모드 (이동 시 활성화)
    let manualViewRange = null;  // 수동 뷰 범위
    
    // 재생 속도 관련 변수
    let playbackSpeed = 1.0;  // 기본 재생 속도 (1x)
    let isPlaybackPaused = false;  // 재생 일시정지 상태
    let isFileMode = false;  // 파일 업로드 모드 여부
    let fileData = [];  // 업로드된 파일 데이터
    let currentFileIndex = 0;  // 현재 재생 중인 데이터 인덱스
    let filePlaybackTimer = null;  // 파일 재생 타이머

    // WebSocket 연결 함수
    function connectWebSocket() {{
        if (socket && socket.readyState === WebSocket.OPEN) {{
            socket.close();
        }}
        
        socket = new WebSocket("ws://" + location.host + "/ws");
        
        socket.onopen = function(event) {{
            console.log("✅ WebSocket 연결됨");
            document.getElementById("status-indicator").style.color = "#2ca02c";
        }};
        
        socket.onclose = function(event) {{
            console.log("❌ WebSocket 연결 끊어짐");
            document.getElementById("status-indicator").style.color = "#d62728";
            // 3초 후 재연결 시도
            setTimeout(connectWebSocket, 3000);
        }};
        
        socket.onerror = function(error) {{
            console.error("❌ WebSocket 오류:", error);
        }};
        
        socket.onmessage = function(event) {{
            const data = JSON.parse(event.data);
            processData(data);
        }};
    }}

    // 페이지 로드 시 WebSocket 연결
    connectWebSocket();

    const signalColors = {{
{signal_colors_js_str}
    }};

    const eventColors = {{
      PM: "#FF4C4C", SA: "#FFA500", SB: "#007BFF",
      DD: "#AAAAAA", SH: "#9933FF"
    }};

    const eventNames = {{
      PM: "페달 오조작", SA: "급가속", SB: "급제동",
      DD: "졸음 운전", SH: "급조향"
    }};

    const scaleMap = {{
{scale_map_js_str}
    }};

    const scaleSuffix = {{
{scale_suffix_js_str}
    }};

    function updateEventTitle() {{
      const el = document.querySelector("#event-title h2");
      if (activeEvents.size === 0) {{
        el.innerText = "실시간 주행 상태";
        el.style.color = "black";
      }} else {{
        const latest = Array.from(activeEvents).slice(-1)[0];
        el.innerText = `실시간 주행 상태 (${{eventNames[latest]}})`;
        el.style.color = eventColors[latest] || "black";
      }}
    }}

    function updateStatusIndicator() {{
      const currentTimeEl = document.getElementById("current-time");
      const dataPointsEl = document.getElementById("data-points");
      const loggingTimeEl = document.getElementById("logging-time");
      const viewModeEl = document.getElementById("view-mode");
      
      if (buffer.length > 0) {{
        const latestTime = buffer[buffer.length - 1].Time;
        currentTimeEl.textContent = `시간: ${{latestTime.toFixed(1)}}초`;
      }} else {{
        currentTimeEl.textContent = "시간: --";
      }}
      
      dataPointsEl.textContent = `데이터 포인트: ${{buffer.length}}`;

      // 로깅 시간 표시
      const startTime = localStorage.getItem("loggingStartTime");
      if (startTime) {{
        const elapsedTime = (Date.now() - parseInt(startTime)) / 1000;
        loggingTimeEl.textContent = `로깅: ${{elapsedTime.toFixed(1)}}초`;
      }} else {{
        loggingTimeEl.textContent = "로깅: --";
      }}

      // 뷰 모드 표시
      if (manualViewMode && manualViewRange) {{
        viewModeEl.textContent = `뷰: 수동 (${{manualViewRange[0].toFixed(1)}}~${{manualViewRange[1].toFixed(1)}}초)`;
      }} else {{
        viewModeEl.textContent = "뷰: 실시간";
      }}
      
      // 재생 속도 표시 (파일 모드일 때만)
      if (isFileMode) {{
        const speedEl = document.getElementById("update-interval");
        speedEl.textContent = `재생: ${{playbackSpeed}}x`;
      }}
    }}

    function updatePlot() {{
      if (buffer.length === 0) return;

      const visibleSigs = Array.from(document.querySelectorAll(".sig:checked")).map(cb => cb.value);
      const visibleEvents = Array.from(document.querySelectorAll(".evt:checked")).map(cb => cb.value);
      const currentTime = buffer[buffer.length - 1].Time;

      const ongoingShapes = Object.entries(eventRanges).map(([code, range]) => {{
        if (!visibleEvents.includes(code)) return null;
        return {{
          type: "rect",
          xref: "x",
          yref: "paper",
          x0: range.start,
          x1: currentTime,
          y0: 0,
          y1: 1,
          fillcolor: eventColors[code] || "gray",
          opacity: 0.15,
          line: {{ width: 0 }}
        }};
      }}).filter(Boolean);

      const filteredShapes = shapes.filter(s =>
        visibleEvents.includes(Object.keys(eventColors).find(code => s.fillcolor === eventColors[code]))
      );

      const filteredAnnotations = annotations.filter(a =>
        visibleEvents.includes(Object.keys(eventNames).find(code => a.text === eventNames[code]))
      );

      let yMin = 0, yMax = 1;
      const traces = visibleSigs.map(sig => {{
        const scale = scaleMap[sig] || 1;
        const y = buffer.map(p => (p[sig] ?? 0) * scale);
        const minY = Math.min(...y);
        const maxY = Math.max(...y);
        if (minY < yMin) yMin = minY - 1;
        if (maxY > yMax) yMax = maxY + 1;
        return {{
          x: buffer.map(p => p.Time),
          y,
          name: sig + (scaleSuffix[sig] || ""),
          type: 'scatter',
          mode: 'lines',
          line: {{ color: signalColors[sig] || '#000000' }}
        }};
      }});

      const layout = {{
        yaxis: {{ range: [yMin, yMax] }},
        shapes: filteredShapes.concat(ongoingShapes),
        annotations: filteredAnnotations
      }};

      // 수동 뷰 모드가 아닐 때만 x축 범위를 실시간으로 업데이트
      if (!manualViewMode) {{
        layout.xaxis = {{ range: [currentTime - maxWindow, currentTime] }};
      }} else if (manualViewRange) {{
        layout.xaxis = {{ range: manualViewRange }};
      }}

      if (!initialized) {{
        Plotly.newPlot("plot", traces, layout);
        initialized = true;
      }} else {{
        Plotly.react("plot", traces, layout);
      }}

      // 상태 표시기 업데이트
      updateStatusIndicator();
    }}

    // 0.1초 간격으로 그래프 업데이트하는 함수
    function scheduleUpdate() {{
      if (updateTimer) {{
        clearTimeout(updateTimer);
      }}
      updateTimer = setTimeout(() => {{
        updatePlot();
        scheduleUpdate();  // 다음 업데이트 예약
      }}, sampleInterval * 1000);  // 0.1초를 밀리초로 변환
    }}

    // 로깅 시간 실시간 업데이트 함수
    function startLoggingTimer() {{
      if (loggingTimer) {{
        clearInterval(loggingTimer);
      }}
      loggingTimer = setInterval(() => {{
        const startTime = localStorage.getItem("loggingStartTime");
        if (startTime) {{
          const elapsedTime = (Date.now() - parseInt(startTime)) / 1000;
          const loggingTimeEl = document.getElementById("logging-time");
          loggingTimeEl.textContent = `로깅: ${{elapsedTime.toFixed(1)}}초`;
        }}
      }}, 100);  // 0.1초마다 업데이트
    }}

    function stopLoggingTimer() {{
      if (loggingTimer) {{
        clearInterval(loggingTimer);
        loggingTimer = null;
      }}
    }}

    // 그래프 뷰 이동 함수
    function moveGraph(seconds) {{
      if (buffer.length === 0) return;
      
      let newXRange;
      
      if (manualViewMode && manualViewRange) {{
        // 이미 수동 뷰 모드일 때는 현재 뷰를 기준으로 이동하되 30초 범위 유지
        const center = (manualViewRange[0] + manualViewRange[1]) / 2 + seconds;
        newXRange = [center - maxWindow/2, center + maxWindow/2];
      }} else {{
        // 실시간 모드일 때는 현재 시간을 기준으로 이동하되 30초 범위 유지
        const currentTime = buffer[buffer.length - 1].Time;
        const center = currentTime + seconds;
        newXRange = [center - maxWindow/2, center + maxWindow/2];
      }}
      
      // 범위가 음수가 되지 않도록 조정
      if (newXRange[0] < 0) {{
        newXRange = [0, maxWindow];
      }}
      
      manualViewMode = true;
      manualViewRange = newXRange;
      updatePlot();
    }}

    // 실시간 뷰로 리셋
    function resetGraphView() {{
      manualViewMode = false;
      manualViewRange = null;
      updatePlot();
    }}

    // 재생 속도 설정
    function setPlaybackSpeed(speed) {{
      playbackSpeed = speed;
      
      // 모든 버튼에서 active 클래스 제거
      document.querySelectorAll('.speed-btn').forEach(btn => {{
        btn.classList.remove('active');
      }});
      
      // 선택된 버튼에 active 클래스 추가
      document.querySelector(`[data-speed="${{speed}}"]`).classList.add('active');
      
      if (isFileMode) {{
        // 파일 재생 속도 업데이트
        updateFilePlayback();
      }}
    }}

    // 재생/일시정지 토글
    function togglePlayback() {{
      if (!isFileMode) return;
      
      isPlaybackPaused = !isPlaybackPaused;
      const btn = document.getElementById('play-pause-btn');
      
      if (isPlaybackPaused) {{
        btn.textContent = '▶️ 재생';
        btn.classList.add('paused');
        if (filePlaybackTimer) {{
          clearTimeout(filePlaybackTimer);
          filePlaybackTimer = null;
        }}
      }} else {{
        btn.textContent = '⏸️ 일시정지';
        btn.classList.remove('paused');
        updateFilePlayback();
      }}
    }}

    // 파일 재생 업데이트
    function updateFilePlayback() {{
      if (!isFileMode || isPlaybackPaused) return;
      
      if (filePlaybackTimer) {{
        clearTimeout(filePlaybackTimer);
      }}
      
      filePlaybackTimer = setTimeout(() => {{
        if (currentFileIndex < fileData.length) {{
          processData(fileData[currentFileIndex]);
          currentFileIndex++;
          updateFilePlayback();
        }} else {{
          // 재생 완료
          isFileMode = false;
          document.getElementById('playback-controls').style.display = 'none';
          document.getElementById('status-indicator').style.color = '#2ca02c';
          connectWebSocket();  // WebSocket 재연결
        }}
      }}, (sampleInterval * 1000) / playbackSpeed);
    }}

    // 데이터 처리 함수
    function processData(data) {{
      if (!data || typeof data.Time === 'undefined') return;
      
      // SPEED 계산
      if (data.WHEEL_SPEED_1 && data.WHEEL_SPEED_2 && data.WHEEL_SPEED_3 && data.WHEEL_SPEED_4) {{
        try {{
          data.SPEED = (parseFloat(data.WHEEL_SPEED_1) + parseFloat(data.WHEEL_SPEED_2) + 
                        parseFloat(data.WHEEL_SPEED_3) + parseFloat(data.WHEEL_SPEED_4)) / 4;
        }} catch (e) {{
          data.SPEED = 0;
        }}
      }}
      
      buffer.push(data);
      
      // 최대 포인트 수 제한
      if (buffer.length > maxPoints) {{
        buffer.shift();
      }}
      
      // 이벤트 처리
      if (data.event && data.event !== 'none') {{
        const [eventCode, eventState] = data.event.split('_');
        
        if (eventState === 'on') {{
          activeEvents.add(eventCode);
          eventRanges[eventCode] = {{ start: data.Time }};
          
          // 이벤트 시작 주석 추가
          annotations.push({{
            x: data.Time,
            y: 1,
            text: eventNames[eventCode] || eventCode,
            showarrow: true,
            arrowhead: 2,
            arrowsize: 1,
            arrowwidth: 2,
            arrowcolor: eventColors[eventCode] || 'gray',
            bgcolor: eventColors[eventCode] || 'gray',
            bordercolor: 'white',
            borderwidth: 1,
            font: {{ color: 'white', size: 12 }}
          }});
        }} else if (eventState === 'off') {{
          activeEvents.delete(eventCode);
          if (eventRanges[eventCode]) {{
            eventRanges[eventCode].end = data.Time;
            delete eventRanges[eventCode];
          }}
        }}
      }}
      
      updateEventTitle();
      
      // 실시간 모드일 때만 자동 업데이트
      if (!manualViewMode) {{
        updatePlot();
      }}
    }}

    // 로깅 토글 함수
    async function toggleLogging(start) {{
      try {{
        const response = await fetch(`/${{start ? 'start' : 'stop'}}_logging`, {{
          method: 'POST'
        }});
        const result = await response.text();
        console.log(result);
        
        if (start) {{
          localStorage.setItem("loggingStartTime", Date.now().toString());
          startLoggingTimer();
        }} else {{
          localStorage.removeItem("loggingStartTime");
          stopLoggingTimer();
        }}
      }} catch (error) {{
        console.error('로깅 토글 오류:', error);
      }}
    }}

    // 파일 업로드 처리
    document.getElementById('upload-form').addEventListener('submit', async function(e) {{
      e.preventDefault();
      
      const formData = new FormData(this);
      const file = formData.get('file');
      
      if (!file) {{
        alert('파일을 선택해주세요.');
        return;
      }}
      
      try {{
        const response = await fetch('/upload', {{
          method: 'POST',
          body: formData
        }});
        
        const result = await response.json();
        
        if (result.success) {{
          console.log('업로드 성공:', result.message);
          
          // 파일 모드로 전환
          isFileMode = true;
          fileData = result.data;
          currentFileIndex = 0;
          
          // WebSocket 연결 해제
          if (socket) {{
            socket.close();
          }}
          
          // 재생 컨트롤 표시
          document.getElementById('playback-controls').style.display = 'block';
          document.getElementById('status-indicator').style.color = '#ff7f0e';
          
          // 버퍼 초기화
          buffer.length = 0;
          shapes.length = 0;
          annotations.length = 0;
          activeEvents.clear();
          Object.keys(eventRanges).forEach(key => delete eventRanges[key]);
          
          // 그래프 초기화
          initialized = false;
          
          // 재생 시작
          isPlaybackPaused = false;
          document.getElementById('play-pause-btn').textContent = '⏸️ 일시정지';
          document.getElementById('play-pause-btn').classList.remove('paused');
          
          updateFilePlayback();
          
        }} else {{
          alert('업로드 실패: ' + result.message);
        }}
      }} catch (error) {{
        console.error('업로드 오류:', error);
        alert('업로드 중 오류가 발생했습니다.');
      }}
    }});

    // 페이지 로드 시 업데이트 시작
    scheduleUpdate();
  </script>
</body>
</html>'''
    
    return html_template

def main():
    """메인 함수"""
    print("🚀 대시보드 HTML 자동 생성기")
    print("=" * 50)
    print("📋 config/signals.py의 VISUALIZATION_SIGNALS를 기반으로 대시보드를 생성합니다.")
    print()
    
    try:
        generate_dashboard_html()
        print("\n✅ 대시보드 HTML 생성이 완료되었습니다!")
        print("💡 이제 dashboard_mode.py를 실행하여 대시보드를 확인하세요.")
        print("💡 새로운 신호를 추가하려면 config/signals.py의 VISUALIZATION_SIGNALS를 수정하고")
        print("   다시 이 스크립트를 실행하세요.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")

if __name__ == "__main__":
    main() 