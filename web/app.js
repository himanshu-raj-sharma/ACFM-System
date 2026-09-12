const camera = document.querySelector("#camera");
const canvas = document.querySelector("#frame");
const start = document.querySelector("#start");
const analyze = document.querySelector("#analyze");
const result = document.querySelector("#result");
let stream;

start.addEventListener("click", async () => {
  stream = await navigator.mediaDevices.getUserMedia({ video: true });
  camera.srcObject = stream;
  analyze.disabled = false;
  result.textContent = "Camera is ready.";
});

analyze.addEventListener("click", async () => {
  canvas.width = camera.videoWidth;
  canvas.height = camera.videoHeight;
  canvas.getContext("2d").drawImage(camera, 0, 0);
  result.textContent = "Analyzing...";
  const response = await fetch("http://127.0.0.1:5000/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: canvas.toDataURL("image/jpeg", 0.85) })
  });
  const data = await response.json();
  result.textContent = response.ok
    ? `${data.prediction.label} (${Math.round(data.prediction.score * 100)}%). ${data.prediction.recommendation}`
    : data.error;
});
