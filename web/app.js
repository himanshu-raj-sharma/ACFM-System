function apiBaseUrl(locationObject = window.location, documentObject = document) {
  const configured = documentObject
    .querySelector('meta[name="acfm-api-base"]')
    ?.getAttribute("content")
    ?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  if (locationObject.port === "3000") {
    return `${locationObject.protocol}//${locationObject.hostname}:5000`;
  }
  return "";
}

function init() {
  const camera = document.querySelector("#camera");
  const canvas = document.querySelector("#frame");
  const start = document.querySelector("#start");
  const stop = document.querySelector("#stop");
  const analyze = document.querySelector("#analyze");
  const consent = document.querySelector("#consent");
  const result = document.querySelector("#result");
  const apiBase = apiBaseUrl();
  let stream;
  let analyzing = false;

  function updateButtons() {
    const ready = Boolean(stream && camera.videoWidth && camera.videoHeight);
    start.disabled = analyzing;
    stop.disabled = !stream || analyzing;
    analyze.disabled = !ready || !consent.checked || analyzing;
  }

  function waitForVideo() {
    if (camera.videoWidth && camera.videoHeight) {
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(
        () => reject(new Error("camera video did not become ready")),
        5000,
      );
      camera.addEventListener("loadedmetadata", () => {
        clearTimeout(timeout);
        resolve();
      }, { once: true });
    });
  }

  start.addEventListener("click", async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      result.textContent = "Camera access is unavailable in this browser context.";
      return;
    }
    stream?.getTracks().forEach((track) => track.stop());
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      camera.srcObject = stream;
      await waitForVideo();
      updateButtons();
      result.textContent = "Camera is ready. Frames are analyzed in memory only.";
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop());
      stream = undefined;
      updateButtons();
      result.textContent = `Camera access failed: ${error.message}`;
    }
  });

  camera.addEventListener("loadedmetadata", updateButtons);
  consent.addEventListener("change", updateButtons);

  stop.addEventListener("click", () => {
    stream?.getTracks().forEach((track) => track.stop());
    stream = undefined;
    camera.srcObject = null;
    updateButtons();
    result.textContent = "Camera is off.";
  });

  analyze.addEventListener("click", async () => {
    if (!stream || !consent.checked || analyzing) {
      return;
    }
    analyzing = true;
    updateButtons();
    const context = canvas.getContext("2d");
    canvas.width = camera.videoWidth;
    canvas.height = camera.videoHeight;
    result.textContent = "Analyzing...";
    const frames = [];
    try {
      for (let index = 0; index < 12; index += 1) {
        if (!stream || !consent.checked) {
          throw new Error("camera consent was withdrawn");
        }
        context.drawImage(camera, 0, 0);
        frames.push(canvas.toDataURL("image/jpeg", 0.75));
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
      const response = await fetch(`${apiBase}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent: true, images: frames }),
      });
      const data = await response.json().catch(() => ({}));
      result.textContent = response.ok
        ? `${data.prediction.label} (${Math.round(data.prediction.score * 100)}%). ${data.prediction.recommendation}`
        : data.error || "Analysis failed.";
    } catch (error) {
      result.textContent = `Analysis request failed: ${error.message}`;
    } finally {
      analyzing = false;
      updateButtons();
    }
  });

  window.addEventListener("beforeunload", () => {
    stream?.getTracks().forEach((track) => track.stop());
  });
  updateButtons();
}

if (typeof document !== "undefined") {
  init();
}

if (typeof module !== "undefined") {
  module.exports = { apiBaseUrl };
}
