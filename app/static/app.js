const state = {
  uiLanguage: localStorage.getItem("debateBuddyLanguage") || "en",
  markdown: "",
  result: null,
  loadingTimer: null,
};

const copy = {
  en: {
    subtitle: "A simple debate research coach for middle school students",
    newPrep: "NEW PREP",
    prepareDebate: "Prepare your debate",
    setupHint: "Tell your coach what you are preparing for.",
    motion: "Debate motion",
    side: "Side",
    proposition: "Proposition",
    supportMotion: "Support the motion",
    opposition: "Opposition",
    opposeMotion: "Oppose the motion",
    speechTime: "Speech time",
    minutes: "min",
    researchDepth: "Research depth",
    myRoles: "My speaker role",
    selectMany: "Select one or more.",
    firstSpeaker: "1st Speaker",
    secondSpeaker: "2nd Speaker",
    thirdSpeaker: "3rd Speaker",
    replySpeaker: "Reply / Summary",
    outputLanguage: "Output language",
    addSources: "Add your own sources",
    sourceLinks: "Source links",
    onePerLine: "One public web link per line.",
    generate: "Generate my prep pack",
    readyTitle: "Ready when you are",
    readyText: "Your research, case, questions, speeches, and practice plan will appear here.",
    researching: "Building your prep pack",
    loadingOne: "Reading the motion and finding both sides...",
    prepPack: "PREP PACK",
    copyAll: "Copy all",
    rolesRequired: "Select at least one speaker role.",
    motionRequired: "Please enter a debate motion.",
    requestFailed: "Could not generate the prep pack.",
    copied: "Copied to clipboard.",
    downloaded: "Markdown downloaded.",
    sections: [
      "Motion Understanding", "Definitions", "Overall Case Strategy",
      "Attack & Defense", "Cross Fire", "Team Outline",
      "1st Speaker Speech", "My Role Research", "Evidence Bank",
      "Vocabulary Builder", "Practice Plan",
    ],
  },
  zh: {
    subtitle: "给中学生使用的简单辩论研究教练",
    newPrep: "新建准备",
    prepareDebate: "准备你的辩论",
    setupHint: "告诉教练你正在准备什么。",
    motion: "辩论题目",
    side: "立场",
    proposition: "正方",
    supportMotion: "支持辩题",
    opposition: "反方",
    opposeMotion: "反对辩题",
    speechTime: "发言时间",
    minutes: "分钟",
    researchDepth: "研究深度",
    myRoles: "我的辩位",
    selectMany: "可选择一个或多个。",
    firstSpeaker: "一辩",
    secondSpeaker: "二辩",
    thirdSpeaker: "三辩",
    replySpeaker: "总结辩",
    outputLanguage: "输出语言",
    addSources: "添加自己的资料",
    sourceLinks: "资料链接",
    onePerLine: "每行一个公开网页链接。",
    generate: "生成辩论准备包",
    readyTitle: "准备好了就开始",
    readyText: "研究、论点、提问、发言稿和练习计划会显示在这里。",
    researching: "正在生成辩论准备包",
    loadingOne: "正在理解辩题并研究双方观点...",
    prepPack: "辩论准备包",
    copyAll: "复制全部",
    rolesRequired: "请至少选择一个辩位。",
    motionRequired: "请输入辩论题目。",
    requestFailed: "无法生成辩论准备包。",
    copied: "已复制。",
    downloaded: "Markdown 已下载。",
    sections: [
      "辩题解读", "概念定义", "整体策略", "攻防地图", "交叉质询",
      "团队大纲", "一辩发言稿", "我的辩位研究", "证据库", "词汇表", "练习计划",
    ],
  },
};

const loadingMessages = {
  en: [
    "Reading the motion and finding both sides...",
    "Checking useful evidence and its sources...",
    "Building your team case and defense...",
    "Writing clear practice lines...",
  ],
  zh: [
    "正在理解辩题并研究双方观点...",
    "正在核对证据和来源...",
    "正在建立团队论点和防守...",
    "正在编写清楚、可练习的句子...",
  ],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const esc = (value = "") =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

function init() {
  applyLanguage(state.uiLanguage);
  $(".language-switch").addEventListener("click", handleLanguageSwitch);
  $("#debate-form").addEventListener("submit", submitForm);
  $("#time-minus").addEventListener("click", () => changeTime(-1));
  $("#time-plus").addEventListener("click", () => changeTime(1));
  $("#copy-all").addEventListener("click", () => copyText(state.markdown));
  $("#download-markdown").addEventListener("click", downloadMarkdown);
  $("#print-pdf").addEventListener("click", () => window.print());
  $("#result-sections").addEventListener("click", handleSectionCopy);
  if (window.lucide) window.lucide.createIcons();
}

function handleLanguageSwitch(event) {
  const button = event.target.closest("[data-ui-language]");
  if (!button) return;
  applyLanguage(button.dataset.uiLanguage);
}

function applyLanguage(language) {
  state.uiLanguage = language;
  localStorage.setItem("debateBuddyLanguage", language);
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  $$("[data-ui-language]").forEach((button) => {
    button.classList.toggle("active", button.dataset.uiLanguage === language);
  });
  $$("[data-i18n]").forEach((element) => {
    const value = copy[language][element.dataset.i18n];
    if (typeof value === "string") element.textContent = value;
  });
  if (state.result) renderResult(state.result);
}

function changeTime(delta) {
  const field = $("#speech-time");
  const value = Math.min(10, Math.max(1, Number(field.value || 4) + delta));
  field.value = value;
}

async function submitForm(event) {
  event.preventDefault();
  const error = $("#form-error");
  error.hidden = true;
  const roles = $$('input[name="speaker_roles"]:checked').map((item) => item.value);
  const motion = $("#motion").value.trim();
  if (!motion) return showFormError(copy[state.uiLanguage].motionRequired);
  if (!roles.length) return showFormError(copy[state.uiLanguage].rolesRequired);

  const sourceUrls = $("#source-urls").value
    .split("\n")
    .map((url) => url.trim())
    .filter(Boolean);
  const payload = {
    motion,
    side: $('input[name="side"]:checked').value,
    speech_time_minutes: Number($("#speech-time").value),
    speaker_roles: roles,
    language: $("#output-language").value,
    research_depth: $("#research-depth").value,
    source_urls: sourceUrls,
  };

  setLoading(true);
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(body.detail)
        ? body.detail.map((item) => item.msg).join(" ")
        : body.detail;
      throw new Error(detail || `HTTP ${response.status}`);
    }
    state.result = body;
    state.markdown = body.markdown_result;
    renderResult(body);
  } catch (requestError) {
    showFormError(`${copy[state.uiLanguage].requestFailed} ${requestError.message}`);
    $("#empty-state").hidden = false;
  } finally {
    setLoading(false);
  }
}

function showFormError(message) {
  const error = $("#form-error");
  error.textContent = message;
  error.hidden = false;
  error.scrollIntoView({ behavior: "smooth", block: "center" });
}

function setLoading(isLoading) {
  const button = $(".generate-button");
  button.disabled = isLoading;
  $("#empty-state").hidden = isLoading || Boolean(state.result);
  $("#loading-state").hidden = !isLoading;
  $("#result-state").hidden = isLoading || !state.result;
  clearInterval(state.loadingTimer);
  if (!isLoading) return;
  let index = 0;
  $("#loading-message").textContent = loadingMessages[state.uiLanguage][0];
  state.loadingTimer = setInterval(() => {
    index = (index + 1) % loadingMessages[state.uiLanguage].length;
    $("#loading-message").textContent = loadingMessages[state.uiLanguage][index];
  }, 3500);
}

function renderResult(response) {
  const result = response.structured_result;
  const labels = copy[state.uiLanguage].sections;
  $("#empty-state").hidden = true;
  $("#loading-state").hidden = true;
  $("#result-state").hidden = false;
  $("#result-motion").textContent = result.motion;
  $("#result-meta").textContent =
    `${result.side} · ${result.speech_time_minutes} min · ${result.speaker_roles.join(", ")}`;

  const warnings = response.research_warnings || [];
  const warningBox = $("#warning-list");
  warningBox.hidden = !warnings.length;
  warningBox.innerHTML = warnings.map((warning) => `<p>${esc(warning)}</p>`).join("");

  const sections = [
    renderMotion(result.motion_understanding),
    renderDefinitions(result.definitions),
    renderStrategy(result.overall_case_strategy),
    renderAttackDefense(result.attack_defense_map),
    renderCrossFire(result.cross_fire),
    renderTeamOutline(result.team_outline),
    renderFirstSpeech(result.first_speaker_speech),
    renderRoles(result.my_role_research),
    renderEvidence(result.evidence_bank),
    renderVocabulary(result.vocabulary_builder),
    renderPractice(result.practice_plan),
  ];

  $("#section-nav").innerHTML = labels
    .map((label, index) => `<a href="#section-${index + 1}">${index + 1}. ${esc(label)}</a>`)
    .join("");
  $("#result-sections").innerHTML = sections
    .map((body, index) => section(index + 1, labels[index], body))
    .join("");
  if (window.lucide) window.lucide.createIcons();
  $("#result-state").scrollIntoView({ behavior: "smooth", block: "start" });
}

function section(number, title, body) {
  return `
    <article class="result-section" id="section-${number}">
      <header class="section-header">
        <span class="section-number">${number}</span>
        <h3>${esc(title)}</h3>
        <button class="copy-section" type="button" title="Copy section" aria-label="Copy section">
          <i data-lucide="copy"></i>
        </button>
      </header>
      <div class="section-body">${body}</div>
    </article>`;
}

function renderMotion(data) {
  return `
    <p>${esc(data.plain_meaning)}</p>
    <div class="key-line"><strong>Main clash:</strong> ${esc(data.main_clash)}</div>
    <h4>Key concepts</h4>
    ${list(data.key_concepts.map((item) => `<strong>${esc(item.term)}:</strong> ${esc(item.simple_explanation)}`), true)}
    <h4>What each side must prove</h4>
    <p><strong>Proposition:</strong> ${esc(data.proposition_burden)}</p>
    <p><strong>Opposition:</strong> ${esc(data.opposition_burden)}</p>
    <h4>Easy attacks against the opponent</h4>${list(data.easy_attacks_against_opponent)}
    <h4>Risks for our side</h4>${list(data.risks_for_our_side)}`;
}

function renderDefinitions(items) {
  return items.map((item) => `
    <div class="argument-block">
      <h4>${esc(item.term)}</h4>
      <p><strong>Possible meanings:</strong> ${esc(item.possible_definitions.join("; "))}</p>
      <p><strong>Recommended:</strong> ${esc(item.recommended_definition)}</p>
      <p><strong>Why it helps:</strong> ${esc(item.why_it_helps)}</p>
      <p><strong>Possible challenge:</strong> ${esc(item.possible_challenge)}</p>
    </div>`).join("") || "<p>No definitions returned.</p>";
}

function renderStrategy(data) {
  return `
    <div class="key-line"><strong>Our stance:</strong> ${esc(data.one_sentence_stance)}</div>
    ${data.main_arguments.map((item, index) => `
      <div class="argument-block">
        <h4>Argument ${index + 1}: ${esc(item.title)}</h4>
        <p>${esc(item.explanation)}</p>
        <p><strong>Evidence direction:</strong> ${esc(item.evidence_direction)}</p>
        <p class="practice-line">You can say: “${esc(item.practice_line)}”</p>
      </div>`).join("")}
    <p><strong>Strongest argument:</strong> ${esc(data.strongest_argument)}</p>
    <p><strong>Most vulnerable:</strong> ${esc(data.most_vulnerable_argument)}</p>
    <h4>Emphasize</h4>${list(data.emphasize)}
    <h4>Avoid</h4>${list(data.avoid)}`;
}

function renderAttackDefense(items) {
  const rows = items.map((item) => `
    <tr>
      <td>${esc(item.opponent_point)}</td>
      <td>${esc(item.our_attack_or_risk)}</td>
      <td>${esc(item.our_response)}</td>
      <td>${esc(item.practice_line)}</td>
    </tr>`).join("");
  return table(["Opponent point", "Our attack or risk", "Our response", "Practice line"], rows);
}

function renderCrossFire(data) {
  return `
    <h4>Goals</h4>${list(data.goals)}
    ${data.questions.map((item, index) => `
      <div class="question-block">
        <h4>${index + 1}. “${esc(item.question)}”</h4>
        <p><strong>Purpose:</strong> ${esc(item.purpose)}</p>
        <p><strong>If yes:</strong> ${esc(item.follow_up_if_yes)}</p>
        <p><strong>If no:</strong> ${esc(item.follow_up_if_no)}</p>
        <p><strong>Best for:</strong> ${esc(item.best_for)}</p>
      </div>`).join("")}
    <h4>Keep emphasizing</h4>${list(data.emphasize)}
    <h4>Avoid</h4>${list(data.avoid)}`;
}

function renderTeamOutline(data) {
  const speakers = [
    ["1st Speaker", data.first_speaker],
    ["2nd Speaker", data.second_speaker],
    ["3rd Speaker", data.third_speaker],
    ["4th / Reply Speaker", data.fourth_speaker],
  ];
  return speakers.map(([name, item]) => `
    <div class="role-block">
      <h4>${name}</h4>
      <strong>Main tasks</strong>${list(item.main_tasks)}
      <strong>Avoid</strong>${list(item.avoid)}
    </div>`).join("");
}

function renderFirstSpeech(data) {
  return `
    <h4>Outline</h4>${list(data.outline, false, true)}
    <h4>Speech text</h4>
    <div class="speech-text">${esc(data.speech_text)}</div>`;
}

function renderRoles(items) {
  return items.map((item) => `
    <div class="role-block">
      <h4>${esc(item.role)}</h4>
      <strong>Role tasks</strong>${list(item.role_tasks)}
      <strong>Key points</strong>${list(item.key_points)}
      ${item.detailed_arguments.map((argument) => `
        <div class="argument-block">
          <h4>${esc(argument.title)}</h4>
          <p>${esc(argument.explanation)}</p>
          <p><strong>Evidence direction:</strong> ${esc(argument.evidence_direction)}</p>
          <p class="practice-line">You can say: “${esc(argument.practice_line)}”</p>
        </div>`).join("")}
      <strong>Evidence IDs</strong>${list(item.supporting_evidence_ids)}
      <strong>Possible attacks</strong>${list(item.possible_attacks)}
      <strong>Responses</strong>${list(item.responses)}
      <strong>Speech outline</strong>${list(item.speech_outline, false, true)}
      <h4>Practice speech</h4>
      <div class="speech-text">${esc(item.speech_text)}</div>
    </div>`).join("") || "<p>No role research returned.</p>";
}

function renderEvidence(items) {
  if (!items.length) {
    return `<div class="key-line">No verified web evidence was available. Do not present unsupported claims as facts.</div>`;
  }
  return items.map((item) => `
    <div class="evidence-item">
      <h4>${esc(item.evidence_id)} · ${esc(item.claim)}
        ${item.credibility === "Needs verification" ? '<span class="status-badge">Needs verification</span>' : ""}
      </h4>
      <p><strong>Fact:</strong> ${esc(item.evidence_summary)}</p>
      <p><strong>Source:</strong> <a class="source-link" href="${esc(item.source_url)}" target="_blank" rel="noopener noreferrer">${esc(item.source_title)}</a></p>
      <p><strong>Date:</strong> ${esc(item.published_date_or_accessed_at)}</p>
      <p><strong>Why it helps:</strong> ${esc(item.why_it_helps_our_side)}</p>
      <p class="practice-line">You can say: “${esc(item.simple_practice_line)}”</p>
    </div>`).join("");
}

function renderVocabulary(items) {
  const rows = items.map((item) => `
    <tr>
      <td><strong>${esc(item.word)}</strong></td>
      <td>${esc(item.simple_english)}</td>
      <td>${esc(item.chinese)}</td>
      <td>${esc(item.example_sentence)}</td>
      <td>${item.debate_useful ? "Yes" : "No"}</td>
    </tr>`).join("");
  return table(["Word", "Simple English", "中文", "Example", "Debate word?"], rows);
}

function renderPractice(data) {
  return `
    <h4>Today</h4>${list(data.today, false, true)}
    <h4>Tomorrow</h4>${list(data.tomorrow, false, true)}
    <h4>Before the tournament</h4>${list(data.before_tournament, false, true)}
    <h4>Learn from YouTube</h4>${list(data.youtube_learning, false, true)}`;
}

function list(items = [], allowHtml = false, ordered = false) {
  const tag = ordered ? "ol" : "ul";
  const content = items
    .map((item) => `<li>${allowHtml ? item : esc(item)}</li>`)
    .join("");
  return `<${tag}>${content}</${tag}>`;
}

function table(headers, rows) {
  return `
    <div class="data-table-wrap">
      <table class="data-table">
        <thead><tr>${headers.map((item) => `<th>${esc(item)}</th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

async function handleSectionCopy(event) {
  const button = event.target.closest(".copy-section");
  if (!button) return;
  const sectionElement = button.closest(".result-section");
  await copyText(sectionElement.innerText.replace("Copy section", "").trim());
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast(copy[state.uiLanguage].copied);
  } catch {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
    showToast(copy[state.uiLanguage].copied);
  }
}

function downloadMarkdown() {
  if (!state.markdown) return;
  const blob = new Blob([state.markdown], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "debate-buddy-prep.md";
  link.click();
  URL.revokeObjectURL(link.href);
  showToast(copy[state.uiLanguage].downloaded);
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 1800);
}

document.addEventListener("DOMContentLoaded", init);
