const state = {
  uiLanguage: localStorage.getItem("debateBuddyLanguage") || "en",
  markdown: "",
  result: null,
  loadingTimer: null,
  activeGeneration: null,
  progressEvents: [],
  progressPercent: 0,
  user: null,
  currentPack: null,
  historyQueryTimer: null,
  webpageTimeoutSeconds: Number(
    document.body.dataset.webpageTimeoutSeconds || 1800,
  ),
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
    sourceLinks: "Text and links",
    onePerLine: "Add plain text, public URLs, or both.",
    history: "History",
    saveVersion: "Save",
    versions: "Versions",
    yourLibrary: "YOUR LIBRARY",
    historyTitle: "Debate research history",
    newPrepButton: "New prep",
    searchHistory: "Search motions",
    newestFirst: "Recently updated",
    oldestFirst: "Oldest updated",
    noHistory: "No debate packs found",
    agentPlaceholder: "Add a viewpoint or source, request a change, or ask a question...",
    profile: "PROFILE",
    register: "Register",
    login: "Log in",
    nickname: "Nickname",
    username: "Username",
    password: "Password",
    createAccount: "Create account",
    updateProfile: "Update profile",
    logout: "Log out",
    savedVersions: "SAVED VERSIONS",
    restoreVersion: "Restore a version",
    restore: "Restore",
    delete: "Delete",
    updated: "Updated",
    saved: "Version saved.",
    restored: "Version restored.",
    agentWorking: "Updating the complete pack...",
    generate: "Generate my prep pack",
    stopGeneration: "Stop generation",
    stoppingGeneration: "Stopping...",
    generationStopped: "Generation stopped. You can edit and try again.",
    progressSteps: "Progress",
    resourcesUsed: "Sources being used",
    elapsed: "Elapsed",
    currentlyWorking: "Still working",
    readyTitle: "Ready when you are",
    readyText: "Your research, case, questions, speeches, and practice plan will appear here.",
    researching: "Building your prep pack",
    loadingOne: "Reading the motion and finding both sides...",
    prepPack: "PREP PACK",
    copyAll: "Copy all",
    rolesRequired: "Select at least one speaker role.",
    motionRequired: "Please enter a debate motion.",
    requestFailed: "Could not generate the prep pack.",
    requestTimedOut: "The request exceeded the 30-minute time limit.",
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
    sourceLinks: "文字与链接",
    onePerLine: "可添加纯文字、公开 URL，或两者混合。",
    history: "历史",
    saveVersion: "保存",
    versions: "版本",
    yourLibrary: "你的资料库",
    historyTitle: "辩论研究历史",
    newPrepButton: "新建准备",
    searchHistory: "搜索辩题",
    newestFirst: "最近更新优先",
    oldestFirst: "最早更新优先",
    noHistory: "没有找到辩论准备包",
    agentPlaceholder: "添加观点或资料、要求修改，或提出问题...",
    profile: "用户资料",
    register: "注册",
    login: "登录",
    nickname: "昵称",
    username: "用户名",
    password: "密码",
    createAccount: "创建账号",
    updateProfile: "更新资料",
    logout: "退出登录",
    savedVersions: "已保存版本",
    restoreVersion: "恢复版本",
    restore: "恢复",
    delete: "删除",
    updated: "更新于",
    saved: "版本已保存。",
    restored: "版本已恢复。",
    agentWorking: "正在更新完整准备包...",
    generate: "生成辩论准备包",
    stopGeneration: "停止生成",
    stoppingGeneration: "正在停止...",
    generationStopped: "生成已停止，可以修改后重新提交。",
    progressSteps: "生成步骤",
    resourcesUsed: "正在使用的资料",
    elapsed: "已用时",
    currentlyWorking: "生成仍在进行",
    readyTitle: "准备好了就开始",
    readyText: "研究、论点、提问、发言稿和练习计划会显示在这里。",
    researching: "正在生成辩论准备包",
    loadingOne: "正在理解辩题并研究双方观点...",
    prepPack: "辩论准备包",
    copyAll: "复制全部",
    rolesRequired: "请至少选择一个辩位。",
    motionRequired: "请输入辩论题目。",
    requestFailed: "无法生成辩论准备包。",
    requestTimedOut: "请求超过 30 分钟时间限制。",
    copied: "已复制。",
    downloaded: "Markdown 已下载。",
    sections: [
      "辩题解读", "概念定义", "整体策略", "攻防地图", "交叉质询",
      "团队大纲", "一辩发言稿", "我的辩位研究", "证据库", "词汇表", "练习计划",
    ],
  },
};

const progressStepLabels = {
  en: {},
  zh: {},
};

Object.assign(progressStepLabels.en, {
  understanding_motion: "Understanding the motion and debate rules",
  analyzing_clash: "Analyzing the central clash and burdens",
  planning_research: "Planning balanced research queries",
  researching_sources: "Searching the web and academic sources",
  querying_web_sources: "Querying public web sources",
  querying_academic_sources: "Querying academic databases",
  opening_source_pages: "Opening and reading source pages",
  sources_collected: "Sources collected",
  evaluating_evidence: "Checking claims and source credibility",
  reasoning_about_evidence: "Model is reasoning about the evidence",
  checking_source_claims: "Cross-checking evidence against source text",
  building_case: "Building arguments, attacks, and defenses",
  reasoning_about_strategy: "Model is reasoning about case strategy",
  drafting_arguments: "Drafting arguments and responses",
  checking_case_consistency: "Checking the case for consistency",
  writing_pack: "Writing speeches, cross-fire, and vocabulary",
  reasoning_about_cross_fire: "Reasoning about cross-fire questions",
  building_vocabulary: "Building the debate vocabulary",
  planning_speeches: "Planning speeches for the selected roles",
  drafting_speeches: "Drafting speech text and speaking lines",
  reviewing_speeches: "Reviewing speeches against the evidence",
  cross_fire_ready: "Cross-fire questions completed",
  vocabulary_ready: "Vocabulary completed",
  speeches_ready: "Speeches and role research completed",
  reading_pack: "Reading the complete existing pack",
  loading_new_sources: "Opening new sources from your message",
  updating_pack: "Reasoning over the pack and your request",
  model_reading_context: "Model is reading the complete pack context",
  model_reasoning_request: "Model is reasoning about your new request",
  model_reworking_strategy: "Model is reworking the case strategy",
  model_updating_evidence: "Model is updating evidence and source links",
  model_rewriting_speeches: "Model is rewriting speeches and responses",
  model_checking_consistency: "Model is checking the updated pack for consistency",
  model_final_review: "Model is performing a final structured review",
  validating_update: "Validating evidence and updated content",
  finalizing_pack: "Formatting and saving the pack",
  completed: "Generation completed",
});

Object.assign(progressStepLabels.zh, {
  understanding_motion: "理解辩题并读取辩论规则",
  analyzing_clash: "分析核心冲突与双方举证责任",
  planning_research: "规划兼顾双方的研究问题",
  researching_sources: "搜索网页与学术资料",
  querying_web_sources: "查询公开网页资料",
  querying_academic_sources: "查询学术数据库",
  opening_source_pages: "打开并读取资料原文",
  sources_collected: "资料收集完成",
  evaluating_evidence: "核对论点、证据和来源可信度",
  reasoning_about_evidence: "大模型正在分析证据",
  checking_source_claims: "对照资料原文核查证据",
  building_case: "构建立论、攻击与防守",
  reasoning_about_strategy: "大模型正在推理整体策略",
  drafting_arguments: "撰写论点、攻击与回应",
  checking_case_consistency: "检查整套论证的一致性",
  writing_pack: "编写演讲稿、交叉质询和词汇",
  reasoning_about_cross_fire: "推理交叉质询问题",
  building_vocabulary: "整理辩论词汇",
  planning_speeches: "规划所选辩位的演讲稿",
  drafting_speeches: "撰写演讲文本与表达句",
  reviewing_speeches: "结合证据复核演讲稿",
  cross_fire_ready: "交叉质询已完成",
  vocabulary_ready: "词汇表已完成",
  speeches_ready: "演讲稿与辩位研究已完成",
  reading_pack: "读取现有研究包的全部内容",
  loading_new_sources: "读取本次输入中的新资料",
  updating_pack: "结合完整研究包处理新要求",
  model_reading_context: "大模型正在读取完整研究包",
  model_reasoning_request: "大模型正在推理本次更新要求",
  model_reworking_strategy: "大模型正在重构论证策略",
  model_updating_evidence: "大模型正在更新证据与来源",
  model_rewriting_speeches: "大模型正在改写演讲稿与回应",
  model_checking_consistency: "大模型正在检查更新内容的一致性",
  model_final_review: "大模型正在进行最终结构化复核",
  validating_update: "核对证据与更新内容",
  finalizing_pack: "整理并保存研究包",
  completed: "生成完成",
});

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
  $("#history-button").addEventListener("click", showHistory);
  $("#new-prep-button").addEventListener("click", showHome);
  $("#profile-button").addEventListener("click", openProfile);
  $("#history-sort").addEventListener("change", loadHistory);
  $("#history-search").addEventListener("input", () => {
    clearTimeout(state.historyQueryTimer);
    state.historyQueryTimer = setTimeout(loadHistory, 250);
  });
  $("#history-list").addEventListener("click", handleHistoryAction);
  $("#agent-form").addEventListener("submit", submitAgentMessage);
  $("#save-version").addEventListener("click", saveVersion);
  $("#show-versions").addEventListener("click", openVersions);
  $("#version-list").addEventListener("click", restoreVersion);
  $("#register-form").addEventListener("submit", register);
  $("#login-form").addEventListener("submit", login);
  $("#profile-form").addEventListener("submit", updateProfile);
  $("#logout-button").addEventListener("click", logout);
  $$(".auth-tab").forEach((button) => button.addEventListener("click", switchAuthView));
  $$(".modal-close").forEach((button) =>
    button.addEventListener("click", () => button.closest("dialog").close()));
  loadProfile();
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
  $$("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = copy[language][element.dataset.i18nPlaceholder] || "";
  });
  if (state.activeGeneration) renderProgress(state.activeGeneration.lastEvent);
  if (state.result) renderResult(state.result);
}

function changeTime(delta) {
  const field = $("#speech-time");
  const value = Math.min(10, Math.max(1, Number(field.value || 4) + delta));
  field.value = value;
}

async function submitForm(event) {
  event.preventDefault();
  if (state.activeGeneration) {
    stopGeneration();
    return;
  }
  const error = $("#form-error");
  error.hidden = true;
  const roles = $$('input[name="speaker_roles"]:checked').map((item) => item.value);
  const motion = $("#motion").value.trim();
  if (!motion) return showFormError(copy[state.uiLanguage].motionRequired);
  if (!roles.length) return showFormError(copy[state.uiLanguage].rolesRequired);

  const payload = {
    motion,
    side: $('input[name="side"]:checked').value,
    speech_time_minutes: Number($("#speech-time").value),
    speaker_roles: roles,
    language: $("#output-language").value,
    research_depth: $("#research-depth").value,
    source_material: $("#source-material").value.trim(),
  };

  setLoading(true);
  const controller = beginGeneration("new");
  try {
    const body = await consumeProgressStream(
      "/api/generate/stream",
      payload,
      controller,
    );
    state.result = body;
    state.markdown = body.markdown_result;
    state.currentPack = body.generation_id
      ? { generation_id: body.generation_id, latest: body, versions: [], messages: [] }
      : null;
    renderResult(body);
    updatePackMode(Boolean(state.currentPack));
  } catch (requestError) {
    if (state.activeGeneration?.cancelledByUser) {
      showToast(copy[state.uiLanguage].generationStopped);
    } else if (state.activeGeneration?.timedOut) {
      showFormError(
        `${copy[state.uiLanguage].requestFailed} ${copy[state.uiLanguage].requestTimedOut}`,
      );
    } else {
      showFormError(`${copy[state.uiLanguage].requestFailed} ${requestError.message}`);
    }
    $("#empty-state").hidden = false;
  } finally {
    finishGeneration();
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
  const button = $("#generate-button");
  $("#empty-state").hidden = isLoading || Boolean(state.result);
  $("#loading-state").hidden = !isLoading;
  $("#result-state").hidden = isLoading || !state.result;
  clearInterval(state.loadingTimer);
  lockInterface(isLoading, "new");
  if (!isLoading) {
    button.classList.remove("stop-button");
    button.innerHTML = `<i data-lucide="sparkles"></i><span id="generate-button-label">${esc(copy[state.uiLanguage].generate)}</span>`;
    if (window.lucide) window.lucide.createIcons();
    return;
  }
  state.progressEvents = [];
  state.progressPercent = 0;
  $("#generation-event-list").innerHTML = "";
  $("#generation-resource-list").innerHTML = "";
  $("#generation-resource-section").hidden = true;
  $("#generation-progress-bar").style.width = "2%";
  $("#loading-message").textContent =
    progressStepLabels[state.uiLanguage].understanding_motion;
  button.classList.add("stop-button");
  button.innerHTML = `<i data-lucide="square"></i><span id="generate-button-label">${esc(copy[state.uiLanguage].stopGeneration)}</span>`;
  button.disabled = false;
  const startedAt = Date.now();
  updateElapsed(startedAt);
  state.loadingTimer = setInterval(() => {
    updateElapsed(startedAt);
  }, 1000);
  if (window.lucide) window.lucide.createIcons();
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

async function api(url, options = {}) {
  const response = await fetchWithTimeout(url, options);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => item.msg).join(" ")
      : body.detail;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return body;
}

async function fetchWithTimeout(url, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    state.webpageTimeoutSeconds * 1000,
  );
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(copy[state.uiLanguage].requestTimedOut);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

function beginGeneration(kind) {
  const controller = new AbortController();
  state.activeGeneration = {
    kind,
    controller,
    cancelledByUser: false,
    timedOut: false,
    startedAt: Date.now(),
    lastEvent: null,
  };
  state.activeGeneration.timeout = window.setTimeout(() => {
    if (!state.activeGeneration) return;
    state.activeGeneration.timedOut = true;
    controller.abort();
  }, state.webpageTimeoutSeconds * 1000);
  return controller;
}

function finishGeneration() {
  if (state.activeGeneration?.timeout) {
    window.clearTimeout(state.activeGeneration.timeout);
  }
  state.activeGeneration = null;
}

function stopGeneration() {
  const active = state.activeGeneration;
  if (!active) return;
  active.cancelledByUser = true;
  active.controller.abort();
  if (active.kind === "new") {
    const button = $("#generate-button");
    button.disabled = true;
    $("#generate-button-label").textContent =
      copy[state.uiLanguage].stoppingGeneration;
  } else {
    const button = $("#agent-submit");
    button.disabled = true;
    button.innerHTML = `<i data-lucide="loader-circle"></i><span>${esc(copy[state.uiLanguage].stoppingGeneration)}</span>`;
    if (window.lucide) window.lucide.createIcons();
  }
}

async function consumeProgressStream(url, payload, controller) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/x-ndjson",
    },
    body: JSON.stringify(payload),
    signal: controller.signal,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${response.status}`);
  }
  if (!response.body) throw new Error("Streaming response is unavailable.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const event = JSON.parse(line);
      if (event.type === "progress") {
        state.activeGeneration.lastEvent = event;
        renderProgress(event);
      } else if (event.type === "result") {
        result = event.result;
      } else if (event.type === "error") {
        throw new Error(event.error || "Generation failed.");
      }
    }
    if (done) break;
  }
  if (state.activeGeneration?.timedOut) {
    throw new Error(copy[state.uiLanguage].requestTimedOut);
  }
  if (!result) throw new Error("Generation ended without a result.");
  return result;
}

function renderProgress(event) {
  if (!event || !state.activeGeneration) return;
  const label =
    progressStepLabels[state.uiLanguage][event.step] || event.message || event.step;
  const previousIndex = state.progressEvents.findIndex(
    (item) => item.step === event.step,
  );
  if (previousIndex >= 0) state.progressEvents.splice(previousIndex, 1);
  state.progressEvents.push(event);
  state.progressPercent = Math.max(
    state.progressPercent,
    Number(event.progress || 0),
  );
  const resources = event.resources || [];
  if (state.activeGeneration.kind === "new") {
    $("#loading-message").textContent = label;
    $("#generation-progress-bar").style.width = `${state.progressPercent}%`;
    $("#generation-event-list").innerHTML = state.progressEvents
      .map((item, index) => {
        const itemLabel =
          progressStepLabels[state.uiLanguage][item.step] || item.message || item.step;
        const current = index === state.progressEvents.length - 1;
        return `<li class="${current ? "current" : "completed"}">
          <i data-lucide="${current ? "loader-circle" : "check"}"></i>
          <span>${esc(itemLabel)}</span>
        </li>`;
      })
      .join("");
    renderResourceList(
      $("#generation-resource-list"),
      $("#generation-resource-section"),
      resources,
    );
  } else {
    $("#agent-progress-step").textContent = label;
    $("#agent-status").textContent =
      `${copy[state.uiLanguage].currentlyWorking}: ${label}`;
    $("#agent-progress-bar").style.width = `${state.progressPercent}%`;
    renderResourceList($("#agent-resource-list"), null, resources);
  }
  updateElapsed(state.activeGeneration.startedAt);
  if (window.lucide) window.lucide.createIcons();
}

function renderResourceList(list, section, resources) {
  if (section) section.hidden = !resources.length;
  list.innerHTML = resources
    .map((resource) => {
      const title = esc(resource.title || resource.url || "Source");
      const type = esc(resource.source_type || "");
      if (/^https?:\/\//.test(resource.url || "")) {
        return `<li><a href="${esc(resource.url)}" target="_blank" rel="noopener noreferrer">${title}</a>${type ? `<small>${type}</small>` : ""}</li>`;
      }
      return `<li><span>${title}</span>${type ? `<small>${type}</small>` : ""}</li>`;
    })
    .join("");
}

function updateElapsed(startedAt) {
  const totalSeconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  const text = `${copy[state.uiLanguage].elapsed}: ${minutes}:${seconds}`;
  $("#loading-elapsed").textContent = text;
  if (state.activeGeneration?.kind === "agent") {
    $("#agent-progress-detail").textContent = text;
  }
}

function lockInterface(locked, kind) {
  $$("#history-button, #profile-button, [data-ui-language]").forEach(
    (element) => {
      element.disabled = locked;
    },
  );
  if (kind === "new") {
    $$("#debate-form input, #debate-form textarea, #debate-form select, #debate-form button")
      .filter((element) => element.id !== "generate-button")
      .forEach((element) => {
        element.disabled = locked;
      });
  } else {
    $("#agent-message").disabled = locked;
    $$(".pack-action").forEach((button) => {
      button.disabled = locked;
    });
  }
}

async function loadProfile() {
  try {
    state.user = await api("/api/auth/me");
    renderProfile();
  } catch {
    $("#history-button").disabled = true;
    $("#profile-button").disabled = true;
    $("#profile-label").textContent = "Guest";
  }
}

function renderProfile() {
  if (!state.user) return;
  $("#profile-label").textContent = state.user.nickname;
  $("#profile-title").textContent = state.user.nickname;
  $("#guest-auth").hidden = !state.user.is_guest;
  $("#profile-form").hidden = state.user.is_guest;
  $("#profile-form [name=nickname]").value = state.user.nickname;
}

function openProfile() {
  $("#auth-error").hidden = true;
  renderProfile();
  $("#profile-dialog").showModal();
}

function switchAuthView(event) {
  const view = event.currentTarget.dataset.authView;
  $$(".auth-tab").forEach((button) =>
    button.classList.toggle("active", button.dataset.authView === view));
  $("#register-form").hidden = view !== "register";
  $("#login-form").hidden = view !== "login";
  $("#auth-error").hidden = true;
}

async function register(event) {
  event.preventDefault();
  await submitAuthForm("/api/auth/register", event.currentTarget);
}

async function login(event) {
  event.preventDefault();
  await submitAuthForm("/api/auth/login", event.currentTarget);
}

async function updateProfile(event) {
  event.preventDefault();
  await submitAuthForm("/api/profile", event.currentTarget, "PATCH");
}

async function logout() {
  try {
    state.user = await api("/api/auth/logout", { method: "POST" });
    renderProfile();
    $("#profile-dialog").close();
    showHome();
  } catch (requestError) {
    $("#auth-error").textContent = requestError.message;
    $("#auth-error").hidden = false;
  }
}

async function submitAuthForm(url, form, method = "POST") {
  const error = $("#auth-error");
  error.hidden = true;
  const payload = Object.fromEntries(new FormData(form));
  try {
    state.user = await api(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    renderProfile();
    $("#profile-dialog").close();
  } catch (requestError) {
    error.textContent = requestError.message;
    error.hidden = false;
  }
}

function showHome() {
  $("#history-view").hidden = true;
  $("#home-view").hidden = false;
  state.currentPack = null;
  state.result = null;
  state.markdown = "";
  $("#result-state").hidden = true;
  $("#empty-state").hidden = false;
  updatePackMode(false);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function showHistory() {
  updatePackMode(false);
  $("#home-view").hidden = true;
  $("#history-view").hidden = false;
  await loadHistory();
}

async function loadHistory() {
  const list = $("#history-list");
  const empty = $("#history-empty");
  list.innerHTML = '<div class="inline-loader"></div>';
  empty.hidden = true;
  const params = new URLSearchParams({
    sort: $("#history-sort").value,
    q: $("#history-search").value.trim(),
    limit: "100",
  });
  try {
    const history = await api(`/api/history?${params}`);
    $("#history-summary").textContent =
      `${history.total} pack${history.total === 1 ? "" : "s"} · ${history.retention_days} day retention`;
    list.innerHTML = history.items.map((item) => `
      <article class="history-item" data-pack-id="${item.generation_id}">
        <button type="button" class="history-open">
          <span class="history-motion">${esc(item.motion)}</span>
          <span class="history-meta">${esc(item.side)} · ${esc(item.research_depth)} ·
            ${copy[state.uiLanguage].updated} ${formatDate(item.updated_at)}</span>
        </button>
        <button type="button" class="icon-button history-delete" title="${copy[state.uiLanguage].delete}" aria-label="${copy[state.uiLanguage].delete}">
          <i data-lucide="trash-2"></i>
        </button>
      </article>`).join("");
    empty.hidden = Boolean(history.items.length);
    if (window.lucide) window.lucide.createIcons();
  } catch (requestError) {
    list.innerHTML = `<p class="form-error">${esc(requestError.message)}</p>`;
  }
}

async function handleHistoryAction(event) {
  const item = event.target.closest(".history-item");
  if (!item) return;
  const generationId = item.dataset.packId;
  if (event.target.closest(".history-delete")) {
    if (!window.confirm("Delete this debate pack?")) return;
    try {
      await api(`/api/history/${generationId}`, { method: "DELETE" });
      await loadHistory();
    } catch (requestError) {
      showToast(requestError.message);
    }
    return;
  }
  if (event.target.closest(".history-open")) await openPack(generationId);
}

async function openPack(generationId) {
  try {
    const pack = await api(`/api/history/${generationId}`);
    state.currentPack = pack;
    state.result = pack.latest;
    state.markdown = pack.latest.markdown_result;
    $("#history-view").hidden = true;
    $("#home-view").hidden = false;
    updatePackMode(true);
    renderResult(pack.latest);
  } catch (requestError) {
    showToast(requestError.message);
  }
}

function updatePackMode(active) {
  document.body.classList.toggle("pack-mode", active);
  $$(".pack-action").forEach((button) => {
    button.hidden = !active;
  });
  $("#agent-composer").hidden = !active;
  if (active) renderVersions();
}

async function submitAgentMessage(event) {
  event.preventDefault();
  if (state.activeGeneration) {
    stopGeneration();
    return;
  }
  if (!state.currentPack) return;
  const input = $("#agent-message");
  const message = input.value.trim();
  if (!message) return;
  const controller = beginGeneration("agent");
  setAgentLoading(true);
  try {
    const pack = await consumeProgressStream(
      `/api/history/${state.currentPack.generation_id}/agent/stream`,
      { message },
      controller,
    );
    input.value = "";
    state.currentPack = pack;
    state.result = pack.latest;
    state.markdown = pack.latest.markdown_result;
    renderResult(pack.latest);
  } catch (requestError) {
    showToast(
      state.activeGeneration?.cancelledByUser
        ? copy[state.uiLanguage].generationStopped
        : state.activeGeneration?.timedOut
          ? copy[state.uiLanguage].requestTimedOut
          : requestError.message,
    );
  } finally {
    finishGeneration();
    setAgentLoading(false);
  }
}

function setAgentLoading(isLoading) {
  const button = $("#agent-submit");
  $("#agent-form").classList.toggle("running", isLoading);
  lockInterface(isLoading, "agent");
  clearInterval(state.loadingTimer);
  $("#agent-progress").hidden = !isLoading;
  $("#agent-status").textContent = isLoading
    ? copy[state.uiLanguage].agentWorking
    : "";
  if (!isLoading) {
    button.classList.remove("stop-button");
    button.innerHTML = '<i data-lucide="arrow-up"></i>';
    button.setAttribute("aria-label", "Send");
    button.title = "Send";
    button.disabled = false;
    if (window.lucide) window.lucide.createIcons();
    return;
  }
  state.progressEvents = [];
  state.progressPercent = 0;
  $("#agent-progress-step").textContent =
    progressStepLabels[state.uiLanguage].reading_pack;
  $("#agent-progress-bar").style.width = "2%";
  $("#agent-resource-list").innerHTML = "";
  button.classList.add("stop-button");
  button.innerHTML = `<i data-lucide="square"></i><span>${esc(copy[state.uiLanguage].stopGeneration)}</span>`;
  button.setAttribute("aria-label", copy[state.uiLanguage].stopGeneration);
  button.title = copy[state.uiLanguage].stopGeneration;
  button.disabled = false;
  updateElapsed(state.activeGeneration.startedAt);
  state.loadingTimer = setInterval(() => {
    if (state.activeGeneration) updateElapsed(state.activeGeneration.startedAt);
  }, 1000);
  if (window.lucide) window.lucide.createIcons();
}

async function saveVersion() {
  if (!state.currentPack) return;
  try {
    await api(`/api/history/${state.currentPack.generation_id}/versions`, {
      method: "POST",
    });
    state.currentPack = await api(`/api/history/${state.currentPack.generation_id}`);
    renderVersions();
    showToast(copy[state.uiLanguage].saved);
  } catch (requestError) {
    showToast(requestError.message);
  }
}

function openVersions() {
  renderVersions();
  $("#versions-dialog").showModal();
}

function renderVersions() {
  const versions = state.currentPack?.versions || [];
  $("#version-list").innerHTML = versions.length
    ? versions.map((version) => `
      <div class="version-item">
        <div><strong>${esc(version.name)}</strong><small>${formatDate(version.created_at)}</small></div>
        <button type="button" class="secondary-button" data-version-id="${version.version_id}">
          <i data-lucide="rotate-ccw"></i>${copy[state.uiLanguage].restore}
        </button>
      </div>`).join("")
    : `<p class="field-help">${copy[state.uiLanguage].noHistory}</p>`;
  if (window.lucide) window.lucide.createIcons();
}

async function restoreVersion(event) {
  const button = event.target.closest("[data-version-id]");
  if (!button || !state.currentPack) return;
  try {
    const pack = await api(
      `/api/history/${state.currentPack.generation_id}/versions/${button.dataset.versionId}/restore`,
      { method: "POST" },
    );
    state.currentPack = pack;
    state.result = pack.latest;
    state.markdown = pack.latest.markdown_result;
    $("#versions-dialog").close();
    renderResult(pack.latest);
    showToast(copy[state.uiLanguage].restored);
  } catch (requestError) {
    showToast(requestError.message);
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat(
    state.uiLanguage === "zh" ? "zh-CN" : "en",
    { dateStyle: "medium", timeStyle: "short" },
  ).format(new Date(value));
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 1800);
}

document.addEventListener("DOMContentLoaded", init);
