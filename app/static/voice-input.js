"use strict";
(() => {
  let active = null, pending = null, epoch = 0;
  const zh = () => document.documentElement.lang.startsWith("zh");
  const label = (cn, en) => zh() ? cn : en;
  function status(tool, text) { tool.querySelector(".voice-status").textContent = text; }
  function busy(value) {
    document.querySelectorAll("#generate-button,#agent-submit,#export-word").forEach(button => button.disabled = value);
    document.querySelectorAll(".voice-start").forEach(button => button.disabled = value);
  }
  function wav(samples, sampleRate) {
    const length = Math.floor(samples.length * 16000 / sampleRate);
    const data = new ArrayBuffer(44 + length * 2), view = new DataView(data);
    const ascii = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
    ascii(0, "RIFF"); view.setUint32(4, 36 + length * 2, true); ascii(8, "WAVE");
    ascii(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
    view.setUint16(32, 2, true); view.setUint16(34, 16, true); ascii(36, "data");
    view.setUint32(40, length * 2, true);
    for (let i = 0; i < length; i++) {
      const start = Math.floor(i * sampleRate / 16000), end = Math.min(samples.length, Math.floor((i + 1) * sampleRate / 16000));
      let value = 0;
      for (let j = start; j < end; j++) value += samples[j];
      value = Math.max(-1, Math.min(1, value / Math.max(1, end - start)));
      view.setInt16(44 + i * 2, value * (value < 0 ? 32768 : 32767), true);
    }
    return new Blob([data], {type: "audio/wav"});
  }
  async function cleanup(recording) {
    clearInterval(recording.timer);
    recording.stream?.getTracks().forEach(track => track.stop());
    recording.capture?.disconnect(); recording.source?.disconnect();
    if (recording.capture?.port) recording.capture.port.onmessage = null;
    await recording.context.close().catch(() => {});
  }
  async function cancel(tool) {
    epoch++;
    if (active) { const recording = active; active = null; await cleanup(recording); }
    pending?.controller?.abort(); pending = null;
    busy(false);
    tool.querySelector(".voice-stop").hidden = true;
    tool.querySelector(".voice-cancel").hidden = true;
    tool.querySelector(".voice-retry").hidden = true;
    status(tool, label("录音已取消。", "Recording cancelled."));
  }
  async function recognize(job) {
    const controller = new AbortController();
    job.controller = controller; pending = job; busy(true);
    job.tool.querySelector(".voice-cancel").hidden = false;
    job.tool.querySelector(".voice-retry").hidden = true;
    status(job.tool, label("正在识别语音…", "Transcribing…"));
    const timer = setTimeout(() => controller.abort(), 60000);
    try {
      const response = await fetch(`/api/audio/transcribe?language=${job.language}`, {
        method: "POST", headers: {"Content-Type": "audio/wav"}, body: job.audio, signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "ASR failed");
      if (pending !== job) return;
      const input = document.getElementById(job.tool.dataset.voiceTarget);
      const text = data.text?.trim() || "";
      const combined = input.value + (input.value && text ? "\n" : "") + text;
      if (input.maxLength > 0 && combined.length > input.maxLength) {
        const preview = job.tool.querySelector(".voice-preview");
        preview.value = text; preview.hidden = false;
        status(job.tool, label("输入框长度不足，转写已保留在下方，请自行复制需要的内容。", "Input limit reached; transcript is below for you to copy."));
      } else {
        input.value = combined; input.dispatchEvent(new Event("input", {bubbles: true}));
        status(job.tool, text ? label("已追加文字，可编辑后提交。", "Text appended. Review and edit before sending.") : label("未识别到文字，请重新录音。", "No speech detected; try recording again."));
      }
      job.audio = null; pending = null;
      job.tool.querySelector(".voice-cancel").hidden = true;
    } catch (error) {
      if (pending !== job) return;
      status(job.tool, label("识别失败，可重试或取消。", "Transcription failed; retry or cancel.") + " " + error.message);
      job.tool.querySelector(".voice-retry").hidden = false;
    } finally {
      clearTimeout(timer);
      if (!active && (!pending || pending === job)) busy(false);
    }
  }
  async function stop() {
    if (!active) return;
    const recording = active; active = null;
    await cleanup(recording);
    recording.tool.querySelector(".voice-stop").hidden = true;
    const samples = new Float32Array(recording.count);
    let offset = 0;
    recording.frames.forEach(frame => { samples.set(frame, offset); offset += frame.length; });
    if (samples.length < recording.context.sampleRate * .15) {
      recording.tool.querySelector(".voice-cancel").hidden = true;
      busy(false); status(recording.tool, label("录音过短，请重试。", "Recording too short; try again.")); return;
    }
    await recognize({tool: recording.tool, audio: wav(samples, recording.context.sampleRate), language: recording.language});
  }
  async function start(tool) {
    if (active || pending) return;
    const currentEpoch = ++epoch;
    busy(true); tool.querySelector(".voice-cancel").hidden = false;
    const recording = {
      tool, context: new AudioContext(), frames: [], count: 0,
      language: tool.querySelector(".voice-language").value,
    };
    active = recording;
    status(tool, label("正在开启麦克风…", "Opening microphone…"));
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error(label("需要 HTTPS 和麦克风权限。", "HTTPS and microphone permission are required."));
      await recording.context.resume();
      const receive = data => {
        if (active !== recording) return;
        recording.frames.push(data); recording.count += data.length;
        if (recording.count >= recording.context.sampleRate * 25) stop();
      };
      let moduleTimer;
      try {
        await Promise.race([
          recording.context.audioWorklet.addModule("/static/live-audio-worklet.js"),
          new Promise((_, reject) => { moduleTimer = setTimeout(() => reject(new Error("timeout")), 3000); }),
        ]);
        recording.capture = new AudioWorkletNode(recording.context, "debate-capture");
        recording.capture.port.onmessage = ({data}) => receive(data);
      } catch {
        recording.capture = recording.context.createScriptProcessor(4096, 1, 1);
        recording.capture.onaudioprocess = event => receive(event.inputBuffer.getChannelData(0).slice());
      } finally { clearTimeout(moduleTimer); }
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true},
      });
      if (epoch !== currentEpoch) { stream.getTracks().forEach(track => track.stop()); return; }
      recording.stream = stream;
      recording.source = recording.context.createMediaStreamSource(stream);
      recording.source.connect(recording.capture); recording.capture.connect(recording.context.destination);
      const started = Date.now();
      tool.querySelector(".voice-stop").hidden = false;
      const tick = () => status(tool, label("录音中", "Recording") + ` ${Math.floor((Date.now() - started) / 1000)} / 25s`);
      tick(); recording.timer = setInterval(tick, 1000);
    } catch (error) {
      if (active === recording) { active = null; await cleanup(recording); busy(false); }
      tool.querySelector(".voice-cancel").hidden = true;
      status(tool, error.message);
    }
  }
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".voice-tools").forEach(tool => {
      tool.innerHTML = `<button type="button" class="voice-start">🎙 <span data-i18n="voiceInput">${label("语音输入", "Voice input")}</span></button>
        <select class="voice-language" aria-label="Speech language"><option value="zh">中文</option><option value="en">English</option></select>
        <button type="button" class="voice-stop" data-i18n="voiceStop" hidden>${label("结束并转文字", "Stop & transcribe")}</button>
        <button type="button" class="voice-cancel" data-i18n="voiceCancel" hidden>${label("取消", "Cancel")}</button>
        <button type="button" class="voice-retry" data-i18n="voiceRetry" hidden>${label("重试识别", "Retry")}</button>
        <span class="voice-status" role="status"></span><textarea class="voice-preview" readonly hidden aria-label="Transcript"></textarea>`;
      tool.querySelector(".voice-language").value = localStorage.getItem("debateBuddyLanguage") === "zh" ? "zh" : "en";
      tool.querySelector(".voice-start").addEventListener("click", () => start(tool));
      tool.querySelector(".voice-stop").addEventListener("click", stop);
      tool.querySelector(".voice-cancel").addEventListener("click", () => cancel(tool));
      tool.querySelector(".voice-retry").addEventListener("click", () => pending && recognize(pending));
    });
    window.addEventListener("pagehide", () => {
      epoch++; active?.stream?.getTracks().forEach(track => track.stop());
      active?.context.close(); pending?.controller?.abort();
    });
  });
})();
