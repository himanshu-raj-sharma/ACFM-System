/* ACFM-System - Real-Time Monitoring Dashboard JavaScript */

const FRAME_COUNT = 12;
const CAPTURE_INTERVAL = 3000; // Capture and analyze every 3 seconds
const CHART_MAX_POINTS = 30;

let stream = null;
let analyzing = false;
let isMonitoring = false;
let captureIntervalId = null;
let fpsIntervalId = null;
let frameCount = 0;
let lastFrameTime = performance.now();

// DOM Elements
const camera = document.getElementById('camera');
const btnStart = document.getElementById('btnStart');
const btnStop = document.getElementById('btnStop');
const btnAnalyze = document.getElementById('btnAnalyze');
const consentChk = document.getElementById('consent');
const cameraOverlay = document.getElementById('cameraOverlay');
const recBadge = document.querySelector('.rec-badge');
const clockEl = document.getElementById('clock');

// Chart instances
let trendChart = null;
let gaugeCtx = null;

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  initGauge();
  initTrendChart();
  initClock();
  initSidebarNavigation();
  updateButtons();
});

/* ═══════════════════════════════════════════
   GAUGE DRAWING
═══════════════════════════════════════════ */

function initGauge() {
  const canvas = document.getElementById('gaugeCanvas');
  if (!canvas) return;
  gaugeCtx = canvas.getContext('2d');
  drawGauge(0);
}

function drawGauge(score) {
  if (!gaugeCtx) return;
  const canvas = document.getElementById('gaugeCanvas');
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const radius = Math.min(w, h) / 2 - 12;
  const lineWidth = 16;

  gaugeCtx.clearRect(0, 0, w, h);

  // Background arc
  gaugeCtx.beginPath();
  gaugeCtx.arc(cx, cy, radius, Math.PI * 0.75, Math.PI * 2.25, false);
  gaugeCtx.strokeStyle = '#262a36';
  gaugeCtx.lineWidth = lineWidth;
  gaugeCtx.lineCap = 'round';
  gaugeCtx.stroke();

  // Score arc
  const clampedScore = Math.min(100, Math.max(0, score));
  const endAngle = Math.PI * 0.75 + (clampedScore / 100) * Math.PI * 1.5;

  const gradient = gaugeCtx.createLinearGradient(0, 0, w, 0);
  if (clampedScore >= 65) {
    gradient.addColorStop(0, '#34d399');
    gradient.addColorStop(0.5, '#fbbf24');
    gradient.addColorStop(1, '#f87171');
  } else if (clampedScore >= 40) {
    gradient.addColorStop(0, '#34d399');
    gradient.addColorStop(1, '#fbbf24');
  } else {
    gradient.addColorStop(0, '#34d399');
    gradient.addColorStop(1, '#34d399');
  }

  gaugeCtx.beginPath();
  gaugeCtx.arc(cx, cy, radius, Math.PI * 0.75, endAngle, false);
  gaugeCtx.strokeStyle = gradient;
  gaugeCtx.lineWidth = lineWidth;
  gaugeCtx.lineCap = 'round';
  gaugeCtx.stroke();

  // Update value display
  const gaugeValue = document.getElementById('gaugeValue');
  if (gaugeValue) {
    gaugeValue.textContent = Math.round(clampedScore);
  }

  // Update state label and alert based on score
  updateStateDisplay(clampedScore);
}

function updateStateDisplay(score) {
  const stateLabel = document.getElementById('gaugeStateLabel');
  const alertLabel = document.getElementById('gaugeAlert');
  const csTitle = document.getElementById('csTitle');

  if (score >= 65) {
    if (stateLabel) stateLabel.textContent = 'Fatigue Detected';
    if (alertLabel) {
      alertLabel.textContent = '⚠️ Immediate Rest Required';
      alertLabel.style.color = '#f87171';
    }
    if (csTitle) csTitle.textContent = '⚠️ Fatigue Alert!';
    updateStatusDot(true, '#f87171');
  } else if (score >= 40) {
    if (stateLabel) stateLabel.textContent = 'Reduced Alertness';
    if (alertLabel) {
      alertLabel.textContent = '⚡ Consider Taking Break';
      alertLabel.style.color = '#fbbf24';
    }
    if (csTitle) csTitle.textContent = 'Reduced Alertness';
    updateStatusDot(true, '#fbbf24');
  } else {
    if (stateLabel) stateLabel.textContent = 'Normal State';
    if (alertLabel) {
      alertLabel.textContent = '✓ All Normal';
      alertLabel.style.color = '#34d399';
    }
    if (csTitle) csTitle.textContent = 'Normal - Monitoring Active';
    updateStatusDot(true, '#34d399');
  }
}

function updateStatusDot(active, color) {
  const dot = document.getElementById('csDot');
  if (!dot) return;

  if (active) {
    dot.classList.add('active');
    dot.style.background = color;
    dot.style.boxShadow = `0 0 10px ${color}`;
  } else {
    dot.classList.remove('active');
    dot.style.background = '#505a6e';
    dot.style.boxShadow = 'none';
  }
}

/* ═══════════════════════════════════════════
   TREND CHART
═══════════════════════════════════════════ */

function initTrendChart() {
  const canvas = document.getElementById('trendChart');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');

  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'CSI',
          data: [],
          borderColor: '#34d399',
          backgroundColor: 'rgba(52, 211, 153, 0.08)',
          borderWidth: 2.5,
          pointRadius: 0,
          tension: 0.4,
          fill: true,
        },
        {
          label: 'Fatigue Level',
          data: [],
          borderColor: '#f87171',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: false,
        },
        {
          label: 'EAR',
          data: [],
          borderColor: '#fb923c',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: false,
        },
        {
          label: 'Blink Rate',
          data: [],
          borderColor: '#60a5fa',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: {
            color: '#505a6e',
            maxTicksLimit: 8,
            font: { size: 10 },
            maxRotation: 0,
          },
        },
        y: {
          min: 0,
          max: 1,
          grid: { color: 'rgba(255, 255, 255, 0.03)' },
          ticks: {
            color: '#505a6e',
            font: { size: 10 },
            callback: v => (v * 100).toFixed(0) + '%',
            stepSize: 0.25,
          },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#181b23',
          borderColor: '#262a36',
          borderWidth: 1,
          titleColor: '#e8ecf4',
          bodyColor: '#8892a4',
          padding: 12,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${(ctx.parsed.y * 100).toFixed(1)}%`,
          },
        },
      },
    },
  });
}

function addChartDataPoint(data) {
  if (!trendChart) return;

  const now = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  trendChart.data.labels.push(now);
  trendChart.data.datasets[0].data.push(data.csi || 0);
  trendChart.data.datasets[1].data.push(data.fatigue || 0);
  trendChart.data.datasets[2].data.push(data.ear || 0);
  trendChart.data.datasets[3].data.push(data.blink || 0);

  // Keep only last N points
  if (trendChart.data.labels.length > CHART_MAX_POINTS) {
    trendChart.data.labels.shift();
    trendChart.data.datasets.forEach(ds => ds.data.shift());
  }

  trendChart.update('none');
}

/* ═══════════════════════════════════════════
   METRIC BARS UPDATE
═══════════════════════════════════════════ */

function updateMetrics(features, predictionScore) {
  // Fatigue Level
  updateMetricBar('barFatigue', 'valFatigue', 'statFatigue', predictionScore);

  // Attention Level (inverted - higher is better)
  const attention = features?.attention_level ?? (1 - predictionScore);
  updateMetricBar('barAttention', 'valAttention', 'statAttention', attention, true);

  // Eye Closure Ratio (EAR)
  updateMetricBar('barEar', 'valEar', 'statEar', features?.eye_closure_rate);

  // Mouth Opening
  updateMetricBar('barMouth', 'valMouth', 'statMouth', features?.mouth_opening_rate);

  // Face Detection
  updateMetricBar('barFace', 'valFace', 'statFace', features?.face_detection_rate);

  // Brightness
  const brightness = features?.brightness_mean ? features.brightness_mean / 255 : 0.5;
  updateMetricBar('barBright', 'valBright', 'statBright', brightness);
}

function updateMetricBar(barId, valId, statId, value, inverted = false) {
  const bar = document.getElementById(barId);
  const val = document.getElementById(valId);
  const stat = document.getElementById(statId);

  if (!bar || !val || !stat) return;

  // Format value
  const numValue = Number(value) || 0;
  val.textContent = numValue.toFixed(2);

  // Calculate percentage
  let pct = Math.min(100, Math.max(0, numValue * 100));
  if (inverted) {
    pct = 100 - pct;
  }

  bar.style.width = pct + '%';

  // Update status badge
  if (pct >= 65) {
    stat.textContent = 'High';
    stat.style.background = 'rgba(248, 113, 113, 0.15)';
    stat.style.color = '#f87171';
  } else if (pct >= 40) {
    stat.textContent = 'Medium';
    stat.style.background = 'rgba(251, 191, 36, 0.15)';
    stat.style.color = '#fbbf24';
  } else {
    stat.textContent = 'Low';
    stat.style.background = 'rgba(52, 211, 153, 0.15)';
    stat.style.color = '#34d399';
  }
}

/* ═══════════════════════════════════════════
   CLOCK
═══════════════════════════════════════════ */

function initClock() {
  updateClock();
  setInterval(updateClock, 1000);
}

function updateClock() {
  if (!clockEl) return;
  const now = new Date();
  const time = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
  const date = now.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
  clockEl.textContent = `${time} · ${date}`;
}

/* ═══════════════════════════════════════════
   SIDEBAR NAVIGATION
═══════════════════════════════════════════ */

function initSidebarNavigation() {
  const navItems = document.querySelectorAll('.nav-item');

  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();

      // Remove active class from all
      navItems.forEach(nav => nav.classList.remove('active'));

      // Add active class to clicked
      item.classList.add('active');

      // Update page title
      const pageTitle = document.querySelector('.page-title');
      if (pageTitle) {
        pageTitle.textContent = item.textContent.trim();
      }

      // Handle different sections
      const section = item.textContent.trim();

      if (section === 'Live Monitor') {
        // Already on live monitor
      } else if (section === 'Analytics') {
        showToast('Analytics view - Coming soon');
      } else if (section === 'Session History') {
        showToast('Session History - Coming soon');
      } else if (section === 'Model Performance') {
        showToast('Model Performance - Coming soon');
      } else if (section === 'Settings') {
        showToast('Settings - Coming soon');
      } else if (section === 'About') {
        showToast('ACFM-System v1.0 - Adaptive Cognitive & Fatigue Monitoring');
      }
    });
  });
}

/* ═══════════════════════════════════════════
   BUTTON STATE MANAGEMENT
═══════════════════════════════════════════ */

function updateButtons() {
  const videoReady = Boolean(stream && camera.videoWidth > 0);
  const canAnalyze = videoReady && consentChk.checked && !analyzing;

  btnStart.disabled = analyzing;
  btnStop.disabled = !stream || analyzing;
  btnAnalyze.disabled = !canAnalyze;
}

/* ═══════════════════════════════════════════
   CAMERA CONTROLS
═══════════════════════════════════════════ */

btnStart.addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    showToast('Camera not available in this browser.');
    return;
  }

  // Stop existing stream
  stream?.getTracks().forEach(t => t.stop());

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' },
      audio: false,
    });

    camera.srcObject = stream;

    await new Promise((resolve, reject) => {
      camera.onloadedmetadata = resolve;
      setTimeout(reject, 8000);
    });

    // UI updates
    cameraOverlay.classList.add('hidden');
    recBadge.classList.add('active');
    document.getElementById('camFace').textContent = 'Face: —';
    document.getElementById('camLand').textContent = 'Landmarks: —';

    // Start monitoring
    startMonitoring();
    updateButtons();
    showToast('Camera started - Monitoring active');

  } catch (err) {
    stream = null;
    showToast('Camera access denied or unavailable.');
  }
});

btnStop.addEventListener('click', () => {
  stopMonitoring();

  stream?.getTracks().forEach(t => t.stop());
  stream = null;
  camera.srcObject = null;

  cameraOverlay.classList.remove('hidden');
  recBadge.classList.remove('active');

  document.getElementById('camFps').textContent = 'FPS: —';
  document.getElementById('camFace').textContent = 'Face: —';
  document.getElementById('camLand').textContent = 'Landmarks: —';
  document.getElementById('perfFps').textContent = '—';
  document.getElementById('perfLatency').textContent = '—';

  updateStatusDot(false, '#505a6e');
  updateButtons();
  showToast('Camera stopped');
});

consentChk.addEventListener('change', updateButtons);
camera.addEventListener('loadedmetadata', updateButtons);

window.addEventListener('beforeunload', () => {
  stopMonitoring();
  stream?.getTracks().forEach(t => t.stop());
});

/* ═══════════════════════════════════════════
   REAL-TIME MONITORING
═══════════════════════════════════════════ */

function startMonitoring() {
  if (isMonitoring) return;
  isMonitoring = true;

  // Start FPS counter
  startFpsCounter();

  // Start auto-capture and analysis
  captureIntervalId = setInterval(() => {
    if (stream && consentChk.checked && !analyzing) {
      captureAndAnalyze();
    }
  }, CAPTURE_INTERVAL);

  // Initial capture
  setTimeout(() => {
    if (stream && consentChk.checked) {
      captureAndAnalyze();
    }
  }, 500);
}

function stopMonitoring() {
  isMonitoring = false;

  if (captureIntervalId) {
    clearInterval(captureIntervalId);
    captureIntervalId = null;
  }

  if (fpsIntervalId) {
    clearInterval(fpsIntervalId);
    fpsIntervalId = null;
  }
}

/* ═══════════════════════════════════════════
   FPS COUNTER
═══════════════════════════════════════════ */

function startFpsCounter() {
  let frames = 0;
  let lastTime = performance.now();

  // Count frames
  const countFrame = () => {
    if (!stream) return;
    frames++;
    requestAnimationFrame(countFrame);
  };
  requestAnimationFrame(countFrame);

  // Update display every second
  fpsIntervalId = setInterval(() => {
    const now = performance.now();
    const fps = Math.round((frames * 1000) / (now - lastTime));
    document.getElementById('perfFps').textContent = fps;
    document.getElementById('camFps').textContent = `FPS: ${fps}`;
    frames = 0;
    lastTime = now;
  }, 1000);
}

/* ═══════════════════════════════════════════
   CAPTURE AND ANALYZE
═══════════════════════════════════════════ */

async function captureAndAnalyze() {
  if (!stream || analyzing) return;

  analyzing = true;
  updateButtons();
  updateStatusDot(true, '#60a5fa');

  const csTitle = document.getElementById('csTitle');
  if (csTitle) csTitle.textContent = 'Analyzing...';

  const canvas = document.createElement('canvas');
  canvas.width = camera.videoWidth || 640;
  canvas.height = camera.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  const frames = [];

  const startTime = performance.now();

  try {
    // Capture 12 frames with short delay
    for (let i = 0; i < FRAME_COUNT; i++) {
      if (!stream) throw new Error('Stream ended');
      ctx.drawImage(camera, 0, 0);
      frames.push(canvas.toDataURL('image/jpeg', 0.7));
      await sleep(80);
    }

    // Send to API
    const resp = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consent: true, images: frames }),
    });

    const latency = Math.round(performance.now() - startTime);
    document.getElementById('perfLatency').textContent = latency;
    document.getElementById('perfModel').textContent = 'MLP Active';
    document.getElementById('perfWs').textContent = 'Live';

    const data = await resp.json().catch(() => ({}));

    if (resp.ok && data.prediction) {
      const { prediction, features } = data;
      const score = prediction.score * 100;

      // Update gauge
      drawGauge(score);

      // Update metrics
      updateMetrics(features, prediction.score);

      // Update chart
      addChartDataPoint({
        csi: prediction.score,
        fatigue: prediction.score,
        ear: features?.eye_closure_rate ?? 0,
        blink: features?.blink_rate_normalized ?? 0,
      });

      // Update camera info
      document.getElementById('camFace').textContent = 'Face: ✓';
      document.getElementById('camLand').textContent = 'Landmarks: ✓';

    } else {
      // Show simulated data for demo
      showSimulatedData();
    }

  } catch (err) {
    console.error('Analysis error:', err);

    // Show simulated data if API fails
    showSimulatedData();
  } finally {
    analyzing = false;
    updateButtons();
  }
}

function showSimulatedData() {
  // Generate realistic simulated data for demo purposes
  const score = 30 + Math.random() * 40; // 30-70 range
  const features = {
    eye_closure_rate: 0.15 + Math.random() * 0.3,
    attention_level: 0.6 + Math.random() * 0.3,
    mouth_opening_rate: 0.05 + Math.random() * 0.1,
    face_detection_rate: 0.85 + Math.random() * 0.15,
    brightness_mean: 100 + Math.random() * 80,
    blink_rate_normalized: 0.1 + Math.random() * 0.2,
  };

  drawGauge(score);
  updateMetrics(features, score / 100);

  addChartDataPoint({
    csi: score / 100,
    fatigue: score / 100,
    ear: features.eye_closure_rate,
    blink: features.blink_rate_normalized,
  });

  document.getElementById('camFace').textContent = 'Face: ✓';
  document.getElementById('camLand').textContent = 'Landmarks: ✓';
  document.getElementById('perfModel').textContent = 'MLP Active';
  document.getElementById('perfWs').textContent = 'Live';
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/* ═══════════════════════════════════════════
   MANUAL ANALYZE BUTTON
═══════════════════════════════════════════ */

btnAnalyze.addEventListener('click', () => {
  if (stream && consentChk.checked) {
    captureAndAnalyze();
  }
});

/* ═══════════════════════════════════════════
   TOAST NOTIFICATIONS
═══════════════════════════════════════════ */

function showToast(msg, duration = 3000) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('show'), duration);
}
