"use strict";
const el = (id) => document.getElementById(id);
const live = {
  session: null, records: [], packs: [], pending: [], processing: false,
  failed: false, listening: false, stopping: false, starting: false,
  recognition: null, finalText: "", interimText: "", firstHeard: null,
  flushTimer: null, restartTimer: null, audio: null, frames: [], sampleCount: 0,
  speaker: null, advice: "", adviceVersion: 0, questionController: null,
  matchesOffset: 0, ready: false,
};
const sideName = (side) => side === "Proposition" ? "正方" : "反方";
const roundName = (round) => ({crossfire: "交叉质询", reply: "总结 / Reply"}[round] || `Round ${round}`);
const uid = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, "0")).join("");
const node = (tag, text, cls) => {
  const result = document.createElement(tag);
  if (text !== undefined) result.textContent = text;
  if (cls) result.className = cls;
  return result;
};
function error(message) {
  el("live-error").textContent = message || "";
  el("live-error").hidden = !message;
}
function controls() {
  const capturing = live.listening || live.stopping || live.starting;
  const busy = capturing || live.processing || live.pending.length > 0 || !!live.questionController;
  for (const id of ["live-speaker", "live-round", "live-speech-language", "live-asr"]) el(id).disabled = capturing;
  for (const id of ["new-match", "resume-match", "live-saved-matches"]) el(id).disabled = busy;
  el("listen-button").disabled = capturing || live.failed || !live.session || el("live-asr").value === "manual";
  el("pause-button").disabled = !live.listening || live.starting;
  el("manual-submit").disabled = live.pending.length >= 8 || live.failed;
  el("retry-turn").hidden = !live.failed;
  el("live-status").textContent = live.starting ? "正在开启麦克风…" : capturing ? "正在监听" : live.session ? "比赛已就绪" : "设置后开始";
  el("live-status").classList.toggle("listening", capturing);
  el("listen-status").textContent = capturing
    ? `${sideName(live.speaker.side)} · ${roundName(live.speaker.round)} · ${live.starting ? "正在开启麦克风…" : "监听中"}`
    : "麦克风已关闭";
}
function queueStatus(message) {
  el("queue-status").textContent = message || (live.pending.length ? `${live.pending.length} 段待处理` : `${live.records.length} 条摘要已保存`);
  controls();
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `请求失败 (${response.status})`);
  }
  return response.json();
}
async function readStream(url, payload, signal, onEvent) {
  const response = await fetch(url, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload), signal,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "请求失败。");
  }
  const reader = response.body.getReader(), decoder = new TextDecoder();
  let buffer = "", doneEvent = false;
  function line(text) {
    if (!text.trim()) return;
    const event = JSON.parse(text);
    if (event.type === "done") doneEvent = true;
    onEvent(event);
  }
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      const lines = buffer.split("\n"); buffer = lines.pop();
      lines.forEach(line);
    }
    buffer += decoder.decode();
    line(buffer);
    if (!doneEvent) throw new Error("连接中断，请重试。");
  } finally { reader.releaseLock(); }
}
async function loadMatches(append = false) {
  if (!append) { live.matchesOffset = 0; el("live-saved-matches").replaceChildren(new Option("选择比赛继续分析…", "")); }
  const data = await api(`/api/live/sessions?limit=30&offset=${live.matchesOffset}`);
  for (const session of data.items) {
    el("live-saved-matches").add(new Option(
      `${session.motion} · ${sideName(session.side)} · ${new Date(session.created_at).toLocaleDateString()}`, session.session_id));
  }
  live.matchesOffset += data.items.length;
  el("more-matches").hidden = data.items.length < 30;
}
function openSession(data) {
  live.session = data.session; live.records = data.records; live.advice = "";
  el("live-arena").hidden = false; el("new-match").hidden = false;
  el("live-motion").value = live.session.motion;
  el("live-side").value = live.session.side;
  el("live-my-round").value = live.session.speaking_round;
  el("live-output-language").value = live.session.language;
  el("live-setup").querySelectorAll("input,select,button").forEach(n => n.disabled = true);
  el("live-setup").hidden = true;
  el("live-match-summary").hidden = false;
  el("live-match-motion").textContent = live.session.motion;
  el("live-match-role").textContent = `我方：${sideName(live.session.side)} · 我的发言：${roundName(live.session.speaking_round)} · 建议语言：${live.session.language}`;
  document.querySelector(".live-resume").hidden = true;
  el("live-speaker").value = live.session.side;
  el("live-round").value = live.session.speaking_round;
  el("live-transcript").textContent = "开始监听，或在下方补录发言。";
  el("live-advice").replaceChildren(node("p", "等待新发言，或在下方提问。", "live-empty"));
  el("copy-advice").disabled = true;
  renderRecords(); queueStatus(); error("");
  el("live-answer").replaceChildren(); el("live-answer").hidden = true;
  el("question-status").textContent = "";
  asrHelp();
  history.replaceState(null, "", `/live?session=${live.session.session_id}`);
  el("live-arena").scrollIntoView({behavior: "smooth", block: "start"});
}
function renderRecords() {
  const list = el("live-records"); list.replaceChildren();
  el("record-count").textContent = `${live.records.length} 条摘要`;
  if (!live.records.length) list.append(node("p", "等待发言，观点和证据摘要会自动保存在这里。", "live-empty"));
  live.records.slice().reverse().forEach((record) => {
    const article = node("article", undefined, "live-record");
    article.id = `record-${record.event_id}`;
    const header = node("header");
    header.append(node("span", sideName(record.speaker_side), `live-side ${record.speaker_side === "Opposition" ? "opposition" : ""}`));
    header.append(node("span", roundName(record.round)), node("time", new Date(record.captured_at).toLocaleTimeString()));
    article.append(header, node("p", record.summary));
    if (record.key_points.length) article.append(bullets(record.key_points));
    if (record.evidence.length) article.append(node("strong", "证据 · 发言者声称，待核实"), bullets(record.evidence));
    if (record.uncertainties.length) article.append(node("p", `需确认：${record.uncertainties.join("；")}`, "uncertain"));
    list.append(article);
  });
}
function bullets(items) {
  const list = node("ul");
  items.forEach(text => list.append(node("li", text)));
  return list;
}
function addRecord(record) {
  if (!live.records.some(r => r.event_id === record.event_id)) {
    live.records.push(record);
    live.records.sort((a, b) => a.captured_at.localeCompare(b.captured_at));
    renderRecords();
  }
}
function showAdvice(advice, label, version, target = "live-advice") {
  if (target === "live-advice" && version !== live.adviceVersion) return;
  const panel = el(target); panel.replaceChildren(); panel.hidden = false;
  panel.append(node("h3", "可以这样说"), node("div", advice.ready_to_say, "live-ready-line"));
  if (advice.next_steps.length) panel.append(node("h3", "下一步"), bullets(advice.next_steps));
  if (advice.questions.length) panel.append(node("h3", "可以追问"), bullets(advice.questions));
  const cited = advice.cited_record_ids.map(id => live.records.find(r => r.event_id === id)).filter(Boolean);
  if (cited.length) {
    panel.append(node("h3", "依据的比赛记录"));
    const links = node("div");
    cited.forEach(record => {
      const link = node("a", `${sideName(record.speaker_side)} · ${roundName(record.round)}：${record.summary.slice(0, 45)}`);
      link.href = `#record-${record.event_id}`;
      links.append(link, node("br"));
    });
    panel.append(links);
  }
  if (target === "live-advice") {
    live.advice = [advice.ready_to_say, ...advice.next_steps, ...advice.questions].join("\n\n");
    el("copy-advice").disabled = false;
    el("advice-status").textContent = label;
  } else el("question-status").textContent = label;
}
function speakerNow() {
  return {side: el("live-speaker").value, round: el("live-round").value};
}
function turnFor(text, speaker, timestamp) {
  return {event_id: uid(), speaker_side: speaker.side, round: speaker.round, text, captured_at: timestamp || new Date().toISOString()};
}
function enqueue(job) {
  live.pending.push(job);
  queueStatus();
  if (live.pending.length >= 6 && live.listening) {
    error("处理速度暂时跟不上发言，已暂停监听。请等待摘要保存后继续。");
    pauseListening().catch(e => error(e.message));
  }
  processQueue();
}
async function processQueue() {
  if (live.processing || live.failed || !live.pending.length) return;
  live.processing = true; controls();
  try {
    while (live.pending.length && !live.failed) {
      const job = live.pending[0];
      // Each request keeps its original speaker/round/event ID across retries.
      let saved = false, reportedError = false;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 180000);
      const version = ++live.adviceVersion;
      try {
        if (job.audio) {
          queueStatus("正在识别语音…");
          const result = await api(`/api/live/sessions/${live.session.session_id}/transcribe?language=${job.language}`, {
            method: "POST", headers: {"Content-Type": "audio/wav"}, body: job.audio, signal: controller.signal,
          });
          job.turn.text = result.text;
          job.audio = null;
          if (!result.text) { live.pending.shift(); continue; }
          el("live-transcript").textContent = result.text;
        }
        await readStream(`/api/live/sessions/${live.session.session_id}/turns`, job.turn, controller.signal, event => {
          if (event.type === "progress") queueStatus(`${event.message} (${live.pending.length} 段)`);
          if (event.type === "summary") {
            saved = true; addRecord(event.record);
            // Full transcript is no longer needed once the summary is durable.
            if (!live.listening || el("live-transcript").textContent === job.turn.text) {
              el("live-transcript").textContent = "摘要已保存，原始转写已清除。";
            }
            job.turn.text = "";
          }
          if (event.type === "advice") showAdvice(event.advice, `${sideName(job.turn.speaker_side)} · ${roundName(job.turn.round)} 发言的回应建议`, version);
          if (event.type === "error") { error(event.error); saved = saved || event.saved; reportedError = true; }
          if (event.type === "done" && !event.saved) reportedError = true;
        });
        if (!saved) throw new Error("摘要尚未保存，请重试。");
        if (!reportedError) error("");
      } catch (exc) {
        if (!saved) {
          live.failed = true;
          error(`${exc.name === "AbortError" ? "处理超时" : exc.message} 待处理内容仅保留在本页，请点击重试。`);
          if (live.listening) await pauseListening();
        } else {
          error("摘要已保存，建议连接中断。可在下方重新提问。");
        }
      } finally { clearTimeout(timer); }
      if (saved) live.pending.shift();
    }
  } finally {
    live.processing = false;
    queueStatus(live.failed ? `${live.pending.length} 段尚未保存 · 等待重试` : undefined);
  }
}
function flushText() {
  const text = live.finalText.trim();
  if (!text) return;
  const timestamp = live.firstHeard;
  live.finalText = ""; live.firstHeard = null;
  el("live-transcript").textContent = live.interimText || "发言正在提炼为摘要…";
  for (let start = 0; start < text.length; start += 6000) {
    enqueue({turn: turnFor(text.slice(start, start + 6000), live.speaker, timestamp)});
  }
}
function startBrowser() {
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Speech) throw new Error("此浏览器不支持语音识别，请选择服务器 ASR 或文字补录。");
  const recognition = new Speech();
  live.recognition = recognition;
  recognition.lang = el("live-speech-language").value === "zh" ? "zh-CN" : "en-US";
  recognition.continuous = true; recognition.interimResults = true;
  recognition.onresult = (event) => {
    if (!live.listening && !live.stopping) return;
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const text = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        if (!live.firstHeard) live.firstHeard = new Date().toISOString();
        live.finalText += `${text} `;
      } else interim += text;
    }
    live.interimText = interim;
    el("live-transcript").textContent = `${live.finalText}${interim}`.slice(-6000);
    if (live.finalText.length >= 600) flushText();
  };
  recognition.onerror = (event) => {
    if (event.error === "no-speech" || (event.error === "aborted" && !live.listening)) return;
    error(({ "not-allowed": "麦克风权限被拒绝，请在浏览器设置中允许。",
      "audio-capture": "找不到可用麦克风。", "network": "浏览器识别服务连接失败，请换用服务器 ASR 或补录。"
    })[event.error] || `语音识别停止：${event.error}`);
    pauseListening().catch(e => error(e.message));
  };
  recognition.onend = () => {
    if (!live.listening) return;
    live.restartTimer = setTimeout(() => {
      if (!live.listening) return;
      try { recognition.start(); } catch { pauseListening().catch(e => error(e.message)); }
    }, 250);
  };
  recognition.start();
  live.flushTimer = setInterval(flushText, 8000);
}
function wav(samples, sourceRate) {
  const rate = 16000, length = Math.floor(samples.length * rate / sourceRate);
  const bytes = new ArrayBuffer(44 + length * 2), view = new DataView(bytes);
  const ascii = (offset, text) => { for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i)); };
  ascii(0, "RIFF"); view.setUint32(4, 36 + length * 2, true); ascii(8, "WAVE");
  ascii(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  ascii(36, "data"); view.setUint32(40, length * 2, true);
  for (let i = 0; i < length; i++) {
    const start = Math.floor(i * sourceRate / rate), end = Math.min(samples.length, Math.floor((i + 1) * sourceRate / rate));
    let value = 0;
    for (let j = start; j < end; j++) value += samples[j];
    value = Math.max(-1, Math.min(1, value / Math.max(1, end - start)));
    view.setInt16(44 + i * 2, value * (value < 0 ? 32768 : 32767), true);
  }
  return new Blob([bytes], {type: "audio/wav"});
}
function flushAudio() {
  if (!live.sampleCount || !live.audio) return;
  const samples = new Float32Array(live.sampleCount);
  let offset = 0, energy = 0;
  live.frames.forEach(frame => { samples.set(frame, offset); offset += frame.length; });
  live.frames = []; live.sampleCount = 0;
  for (const value of samples) energy += value * value;
  if (samples.length < live.audio.context.sampleRate * .15 || Math.sqrt(energy / samples.length) < .001) return;
  const timestamp = new Date(Date.now() - samples.length / live.audio.context.sampleRate * 1000).toISOString();
  enqueue({audio: wav(samples, live.audio.context.sampleRate), language: el("live-speech-language").value,
    turn: turnFor("", live.speaker, timestamp)});
  el("live-transcript").textContent = "语音分段已发送，等待 ASR 识别…";
}
async function startServer() {
  if (!navigator.mediaDevices?.getUserMedia) throw new Error("麦克风需要 HTTPS 或 localhost。");
  const context = new AudioContext();
  live.audio = {stream: null, context};
  try {
    await context.resume();
    const receive = (data) => {
      if (!live.listening) return;
      live.frames.push(data); live.sampleCount += data.length;
      if (live.sampleCount >= context.sampleRate * 5) flushAudio();
    };
    let moduleTimer, capture;
    try {
      if (!context.audioWorklet) throw new Error("AudioWorklet unavailable");
      await Promise.race([
        context.audioWorklet.addModule("/static/live-audio-worklet.js"),
        new Promise((_, reject) => { moduleTimer = setTimeout(() => reject(new Error("AudioWorklet timeout")), 3000); }),
      ]);
      capture = new AudioWorkletNode(context, "debate-capture");
      capture.port.onmessage = ({data}) => receive(data);
    } catch {
      // Compatibility path for browsers whose audio worklet cannot initialize.
      capture = context.createScriptProcessor(4096, 1, 1);
      capture.onaudioprocess = event => receive(event.inputBuffer.getChannelData(0).slice());
    } finally { clearTimeout(moduleTimer); }
    // Initialize capture first so microphone speech is not lost during module loading.
    const stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true}});
    live.audio.stream = stream;
    const source = context.createMediaStreamSource(stream);
    live.audio.source = source; live.audio.capture = capture;
    source.connect(capture); capture.connect(context.destination);
    await context.resume();
  } catch (exc) {
    live.audio?.stream?.getTracks().forEach(track => track.stop());
    await context.close(); live.audio = null;
    throw exc;
  }
}
async function startListening() {
  if (!live.session || live.listening || live.starting) return;
  error(""); live.speaker = speakerNow(); live.starting = true; controls();
  try {
    if (!window.isSecureContext) throw new Error("请通过 HTTPS 打开网站以启用麦克风。");
    live.listening = true;
    if (el("live-asr").value === "server") await startServer();
    else startBrowser();
  } catch (exc) {
    error(exc.message); live.listening = false;
    clearInterval(live.flushTimer); clearTimeout(live.restartTimer);
    live.recognition?.abort(); live.recognition = null;
  } finally { live.starting = false; controls(); }
}
async function pauseListening() {
  if (!live.listening || live.stopping) return;
  live.listening = false; live.stopping = true; controls();
  clearInterval(live.flushTimer); clearTimeout(live.restartTimer);
  try {
    if (live.audio) {
      flushAudio();
      if (live.audio.capture.port) live.audio.capture.port.onmessage = null;
      live.audio.capture.onaudioprocess = null;
      live.audio.source.disconnect(); live.audio.capture.disconnect();
      live.audio.stream.getTracks().forEach(track => track.stop());
      await live.audio.context.close(); live.audio = null;
    }
    if (live.recognition) {
      const recognition = live.recognition;
      // Let final recognition results arrive before labeling a new speaker.
      await new Promise(resolve => {
        const timer = setTimeout(resolve, 1500);
        recognition.onend = () => { clearTimeout(timer); resolve(); };
        try { recognition.stop(); } catch { clearTimeout(timer); resolve(); }
      });
      recognition.onresult = null; recognition.onend = null; recognition.onerror = null;
      live.recognition = null;
      flushText();
      if (live.interimText.trim()) {
        // Keep uncertain unfinished speech visible for manual correction, do not mislabel it as final.
        el("manual-turn").value = live.interimText;
        el("live-transcript").textContent = "末尾有未确认转写，已放入补录框。请检查后提交。";
      }
      live.interimText = "";
    }
  } finally { live.stopping = false; controls(); }
}
async function ask(message) {
  if (!live.session || live.questionController) return;
  error("");
  const controller = new AbortController(); live.questionController = controller;
  const timer = setTimeout(() => controller.abort(), 150000);
  el("ask-button").disabled = true; el("cancel-question").hidden = false; controls();
  try {
    await readStream(`/api/live/sessions/${live.session.session_id}/ask`, {message}, controller.signal, event => {
      if (event.type === "progress") el("question-status").textContent = event.message;
      if (event.type === "advice") showAdvice(event.advice, `你的问题：${message}`, null, "live-answer");
      if (event.type === "error") error(event.error);
    });
  } catch (exc) {
    el("question-status").textContent = "";
    error(exc.name === "AbortError" ? "回答已停止，可重新提问。" : exc.message);
  }
  finally {
    clearTimeout(timer); live.questionController = null;
    el("ask-button").disabled = false; el("cancel-question").hidden = true; controls();
  }
}
function asrHelp() {
  const mode = el("live-asr").value;
  el("asr-help").textContent = mode === "server"
    ? "服务器 ASR 模型：每约 5 秒识别一段，再提炼摘要。双方轮流发言；换人时先暂停再切换。网络或模型较慢时会自动暂停，防止积压。"
    : mode === "manual"
      ? "无需麦克风，在下方补录双方发言。先选择正确的发言方和轮次。"
      : "浏览器语音识别（非本站配置的大模型 ASR）。建议使用 Chrome；需要麦克风权限和识别服务网络。换人时先暂停，再切换发言方。";
  controls();
  if (mode === "manual" && live.session) document.querySelector(".live-manual").open = true;
}
async function init() {
  el("live-setup").addEventListener("submit", async event => {
    event.preventDefault(); el("create-match").disabled = true; error("");
    try {
      const generation = el("live-topic-source").value;
      const data = await api("/api/live/sessions", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({
        motion: el("live-motion").value, side: el("live-side").value,
        speaking_round: el("live-my-round").value, language: el("live-output-language").value,
        generation_id: generation === "new" ? null : generation,
      })});
      openSession(data); await loadMatches();
    } catch (exc) { error(exc.message); if (!live.session) el("create-match").disabled = false; }
  });
  el("live-topic-source").addEventListener("change", () => {
    const pack = live.packs.find(p => p.generation_id === el("live-topic-source").value);
    el("live-motion").readOnly = !!pack;
    if (pack) el("live-motion").value = pack.motion;
    else el("live-motion").value = "";
  });
  el("new-match").addEventListener("click", () => {
    live.session = null; live.records = []; live.advice = ""; live.finalText = ""; live.interimText = "";
    el("manual-turn").value = ""; el("live-query").value = "";
    el("live-arena").hidden = true; el("new-match").hidden = true;
    el("live-setup").hidden = false; el("live-match-summary").hidden = true;
    document.querySelector(".live-resume").hidden = false;
    el("live-setup").querySelectorAll("input,select,button").forEach(n => n.disabled = false);
    history.replaceState(null, "", "/live"); error(""); controls();
  });
  el("resume-match").addEventListener("click", async () => {
    const id = el("live-saved-matches").value;
    if (!id) return error("请先选择已保存的比赛。");
    try { openSession(await api(`/api/live/sessions/${id}`)); } catch (exc) { error(exc.message); }
  });
  el("more-matches").addEventListener("click", () => loadMatches(true).catch(exc => error(exc.message)));
  el("listen-button").addEventListener("click", startListening);
  el("pause-button").addEventListener("click", () => pauseListening().catch(exc => error(exc.message)));
  el("live-asr").addEventListener("change", asrHelp);
  el("retry-turn").addEventListener("click", () => { live.failed = false; error(""); processQueue(); });
  el("live-manual-form").addEventListener("submit", event => {
    event.preventDefault();
    const text = el("manual-turn").value.trim();
    if (!text || live.failed || live.pending.length >= 8) return;
    enqueue({turn: turnFor(text, speakerNow())});
    el("manual-turn").value = "";
  });
  el("live-query-form").addEventListener("submit", event => { event.preventDefault(); if (el("live-query").value.trim()) ask(el("live-query").value.trim()); });
  document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => {
    el("live-query").value = button.dataset.question; ask(button.dataset.question);
  }));
  el("cancel-question").addEventListener("click", () => live.questionController?.abort());
  el("copy-advice").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(live.advice); el("advice-status").textContent = "建议已复制。"; }
    catch { error("无法复制，请手动选中建议文字。"); }
  });
  el("export-match").addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify({session: live.session, records: live.records}, null, 2)], {type: "application/json"}));
    const link = node("a"); link.href = url; link.download = `debate-live-${live.session.session_id}.json`;
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  window.addEventListener("beforeunload", event => {
    if (live.listening || live.starting || live.stopping || live.pending.length || el("manual-turn").value.trim()) { event.preventDefault(); event.returnValue = ""; }
  });
  window.addEventListener("pagehide", () => {
    live.listening = false; clearInterval(live.flushTimer); clearTimeout(live.restartTimer);
    live.recognition?.abort(); live.audio?.stream?.getTracks().forEach(track => track.stop());
    live.audio?.context.close(); live.questionController?.abort();
  });
  try {
    const cap = await api("/api/live/capabilities");
    if (!cap.storage_ready || !cap.llm_configured) {
      el("live-status").textContent = "服务暂未就绪";
      throw new Error(!cap.storage_ready ? "摘要存储不可用，暂不能开始比赛。" : "文字模型尚未配置。");
    }
    live.ready = true; el("create-match").disabled = false;
    const server = el("live-asr").querySelector('[value="server"]');
    if (cap.asr_configured) {
      server.disabled = false;
      server.textContent = cap.asr_provider === "seed" ? "Seed-Speech ASR 2.0" : "服务器 ASR 大模型";
      el("live-asr").value = "server";
    }
    const hasBrowser = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    if (!hasBrowser) {
      el("live-asr").querySelector('[value="browser"]').disabled = true;
      if (!cap.asr_configured) el("live-asr").value = "manual";
    }
    el("live-storage-note").textContent = `比赛摘要长期保存，不保存原始音频或完整转写；语音识别服务会处理音频。${cap.is_guest ? "当前为访客，请到用户资料注册，以便以后找回比赛。" : "摘要保存在当前账号下。"}${!cap.asr_configured ? " 服务器 ASR 模型尚未配置，可用浏览器识别或补录。" : ""}`;
    asrHelp();
    await loadMatches();
    const params = new URLSearchParams(location.search);
    const packData = await api("/api/history?limit=100");
    live.packs = packData.items;
    live.packs.forEach(pack => el("live-topic-source").add(new Option(`准备包 · ${pack.motion}`, pack.generation_id)));
    const requestedPack = params.get("pack");
    if (requestedPack && !live.packs.some(p => p.generation_id === requestedPack)) {
      const pack = await api(`/api/history/${encodeURIComponent(requestedPack)}`);
      live.packs.push({generation_id: requestedPack, motion: pack.request.motion});
      el("live-topic-source").add(new Option(`准备包 · ${pack.request.motion}`, requestedPack));
    }
    if (requestedPack) {
      el("live-topic-source").value = requestedPack;
      el("live-topic-source").dispatchEvent(new Event("change"));
    }
    if (params.get("session")) openSession(await api(`/api/live/sessions/${encodeURIComponent(params.get("session"))}`));
  } catch (exc) { error(exc.message); }
}
init();
