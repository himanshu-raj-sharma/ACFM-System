const camera = document.querySelector("#camera");
const canvas = document.querySelector("#frame");
const start = document.querySelector("#start");
const stop = document.querySelector("#stop");
const analyze = document.querySelector("#analyze");
const consent = document.querySelector("#consent");
const result = document.querySelector("#result");
let stream;

start.addEventListener("click", async () => {
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: true });
    camera.srcObject = stream;
    analyze.disabled = !consent.checked;
    stop.disabled = false;
    result.textContent = "Camera is ready. Frames are analyzed in memory only.";
  } catch (error) {
    result.textContent = `Camera access failed: ${error.message}`;
  }
});

consent.addEventListener("change", () => {
  analyze.disabled = !stream || !consent.checked;
});

stop.addEventListener("click", () => {
  stream?.getTracks().forEach((track) => track.stop());
  stream = undefined;
  camera.srcObject = null;
  analyze.disabled = true;
  stop.disabled = true;
  result.textContent = "Camera is off.";
});

analyze.addEventListener("click", async () => {
  canvas.width = camera.videoWidth;
  canvas.height = camera.videoHeight;
  result.textContent = "Analyzing...";
  const frames = [];
  for (let index = 0; index < 12; index += 1) {
    canvas.getContext("2d").drawImage(camera, 0, 0);
    frames.push(canvas.toDataURL("image/jpeg", 0.75));
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  try {
    const response = await fetch("http://127.0.0.1:5000/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consent: true, images: frames })
    });
    const data = await response.json();
    result.textContent = response.ok
      ? `${data.prediction.label} (${Math.round(data.prediction.score * 100)}%). ${data.prediction.recommendation}`
      : data.error;
  } catch (error) {
    result.textContent = `Analysis request failed: ${error.message}`;
  }
});
