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

  <!-- ✅ 그래프 영역 -->
  <div id="plot" style="width:100%; height:600px;"></div>

  <script>
    const socket = new WebSocket("ws://" + location.host + "/ws");
    const buffer = [];
    const maxWindow = 10;
    const maxPoints = 36000;
    const sampleInterval = 0.1;
    let initialized = false;
    const shapes = [];
    const annotations = [];
    let currentEvent = null;
    let eventStartTime = null;
    let lastEventCode = null; // 마지막으로 표시된 이벤트 코드 추적

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
      if (!currentEvent) {{
        el.innerText = "실시간 주행 상태";
        el.style.color = "black";
      }} else {{
        const [code, state] = currentEvent.split("_");
        if (state === "on") {{
          el.innerText = `실시간 주행 상태 (${{eventNames[code]}})`;
          el.style.color = eventColors[code] || "black";
        }} else {{
          el.innerText = "실시간 주행 상태";
          el.style.color = "black";
        }}
      }}
    }}

    function updatePlot() {{
      if (buffer.length === 0) return;

      const visibleSigs = Array.from(document.querySelectorAll(".sig:checked")).map(cb => cb.value);
      const visibleEvents = Array.from(document.querySelectorAll(".evt:checked")).map(cb => cb.value);
      const currentTime = buffer[buffer.length - 1].Time;

      // 현재 활성화된 이벤트의 영역만 표시
      const activeShapes = [];
      if (currentEvent && eventStartTime) {{
        const [code, state] = currentEvent.split("_");
        if (state === "on" && visibleEvents.includes(code)) {{
          activeShapes.push({{
            type: "rect",
            xref: "x",
            yref: "paper",
            x0: eventStartTime,
            x1: currentTime,
            y0: 0,
            y1: 1,
            fillcolor: eventColors[code] || "gray",
            opacity: 0.15,
            line: {{ width: 0 }}
          }});
        }}
      }}

      // shapes 배열은 더 이상 사용하지 않음 (실시간 영역만 표시)

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
        xaxis: {{ range: [currentTime - maxWindow, currentTime] }},
        shapes: activeShapes,
        annotations: filteredAnnotations
      }};

      if (!initialized) {{
        Plotly.newPlot("plot", traces, layout);
        initialized = true;
      }} else {{
        Plotly.react("plot", traces, layout);
      }}
    }}

    socket.onmessage = function(event) {{
      const data = JSON.parse(event.data);
      
      buffer.push(data);
      if (buffer.length > maxPoints) buffer.shift();

      const currentTime = data.Time;
      if (data.event) {{
        const [code, state] = data.event.split("_");
        if (state === "on") {{
          currentEvent = data.event;
          eventStartTime = currentTime;

          // 이벤트가 변경되었을 때만 annotation 추가
          if (code !== lastEventCode) {{
            const visibleEvents = Array.from(document.querySelectorAll(".evt:checked")).map(cb => cb.value);
            if (visibleEvents.includes(code)) {{
              annotations.push({{
                x: currentTime + 0.1,
                y: 1,
                xref: "x",
                yref: "paper",
                text: eventNames[code] || code,
                showarrow: false,
                font: {{
                  size: 14,
                  color: eventColors[code] || "black"
                }},
                align: "left",
                yanchor: "bottom"
              }});
            }}
            lastEventCode = code;
          }}

        }} else if (state === "off") {{
          currentEvent = null;
          eventStartTime = null;
          lastEventCode = null; // 이벤트가 종료되면 추적 초기화
        }}
        updateEventTitle();
      }}

      updatePlot();
    }};

    // 체크박스 변경 시 그래프 업데이트
    document.querySelectorAll(".sig, .evt").forEach(cb => {{
      cb.addEventListener("change", updatePlot);
    }});

    // 파일 업로드 처리
    document.getElementById("upload-form").addEventListener("submit", function(e) {{
      e.preventDefault();
      const formData = new FormData(this);
      fetch("/upload", {{
        method: "POST",
        body: formData
      }})
      .then(response => response.text())
      .then(result => {{
        alert(result);
        if (result.includes("✅")) {{
          this.reset();
        }}
      }})
      .catch(error => {{
        console.error("Error:", error);
        alert("업로드 실패");
      }});
    }});

    // 로깅 토글 함수
    function toggleLogging(start) {{
      const endpoint = start ? "/start_logging" : "/stop_logging";
      fetch(endpoint, {{ method: "POST" }})
        .then(response => response.text())
        .then(result => alert(result))
        .catch(error => {{
          console.error("Error:", error);
          alert("로깅 토글 실패");
        }});
    }}

    // 페이지 종료 시 서버 종료
    window.addEventListener("beforeunload", function() {{
      fetch("/shutdown", {{ method: "POST" }});
    }});
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
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    main() 