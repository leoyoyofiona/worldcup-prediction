const state = {
  matches: [],
  filters: {},
  tournament: {},
  performance: {},
  selectedId: null,
  loading: false,
  lang: "zh",
  lastStatus: null,
};

const els = {
  statusLine: document.querySelector("#statusLine"),
  updateBtn: document.querySelector("#updateBtn"),
  recalcBtn: document.querySelector("#recalcBtn"),
  sourcesBtn: document.querySelector("#sourcesBtn"),
  summaryGrid: document.querySelector("#summaryGrid"),
  performanceTag: document.querySelector("#performanceTag"),
  performanceGrid: document.querySelector("#performanceGrid"),
  resultComparison: document.querySelector("#resultComparison"),
  simulationCount: document.querySelector("#simulationCount"),
  championStrip: document.querySelector("#championStrip"),
  stageGrid: document.querySelector("#stageGrid"),
  bracketGrid: document.querySelector("#bracketGrid"),
  roundFilter: document.querySelector("#roundFilter"),
  teamFilter: document.querySelector("#teamFilter"),
  confidenceFilter: document.querySelector("#confidenceFilter"),
  searchInput: document.querySelector("#searchInput"),
  matchList: document.querySelector("#matchList"),
  detailPanel: document.querySelector("#detailPanel"),
  notice: document.querySelector("#notice"),
  sourceDrawer: document.querySelector("#sourceDrawer"),
  drawerBackdrop: document.querySelector("#drawerBackdrop"),
  closeDrawerBtn: document.querySelector("#closeDrawerBtn"),
  sourceList: document.querySelector("#sourceList"),
};

const translations = {
  zh: {
    appTitle: "2026 男足世界杯预测",
    loadingStatus: "正在读取模型状态...",
    updateData: "同步赛果",
    recalculate: "重新计算模型",
    sourceStatus: "来源状态",
    performanceTitle: "真实赛果对比",
    tournamentTitle: "淘汰赛推演",
    round: "阶段",
    team: "球队",
    confidence: "置信度",
    search: "搜索",
    searchPlaceholder: "球队 / 场地",
    all: "全部",
    high: "高",
    medium: "中",
    low: "低",
    pending: "待定",
    close: "关闭",
    noMatchSelected: "未选择比赛",
    matches: "比赛",
    teams: "球队",
    historyRows: "历史样本",
    worldCupRows: "世界杯正赛",
    marketSignal: "市场热度",
    bettingSignal: "盘口信号",
    simulations: "模拟次数",
    enabled: "已启用",
    disabled: "未启用",
    actualSamples: "真实样本",
    outcomeAccuracy: "方向命中",
    exactScoreAccuracy: "比分命中",
    averageGoalError: "平均进球误差",
    completedComparison: "已完赛对比",
    prediction: "模型预测",
    actual: "真实赛果",
    result: "结果",
    source: "来源",
    exactHit: "比分命中",
    outcomeHit: "方向命中",
    miss: "未命中",
    noActualResults: "暂无已接入真实赛果；有官方赛果后会自动生成模型预测能力对比。",
    earlySampleNote: "早期样本较小，命中率会随更多真实赛果持续更新。",
    modelUpdated: "模型 {version}，更新于 {time}",
    noData: "尚未生成预测数据",
    updating: "正在同步已完赛比分...",
    recalculating: "正在使用本地缓存重新计算模型...",
    stillRunning: "后台任务仍在运行，稍后会继续更新；你可以过一会儿刷新页面查看结果。",
    updateFailed: "同步赛果失败：{message}",
    recalcFailed: "重新计算失败：{message}",
    initFailed: "初始化失败：{message}",
    noFilteredMatches: "没有符合筛选条件的比赛。",
    allRounds: "全部阶段",
    allTeams: "全部球队",
    championSimulations: "{count} 次模拟",
    noTournament: "暂无淘汰赛推演",
    roundOf32: "32强",
    roundOf16: "16强",
    quarterFinal: "8强",
    semiFinal: "4强 / 半决赛",
    final: "决赛",
    draw: "平局",
    homeWin: "主胜",
    awayWin: "客胜",
    representativeScore: "代表比分",
    modalScore: "精确众数比分",
    favorite: "预测倾向",
    expectedGoals: "预计进球",
    expectedTotalGoals: "总进球期望",
    over25: "大于 2.5 球",
    bothScore: "双方进球",
    knockoutAdvance: "淘汰赛晋级倾向",
    modelExplanation: "模型解释",
    contributors: "贡献项",
    scoreDistribution: "比分分布",
    teamMetrics: "球队指标",
    loading: "正在加载...",
    unavailablePrediction: "暂不计算预测",
    detailFailed: "读取比赛详情失败：{message}",
    sourceLoading: "正在读取...",
    noSources: "尚无来源记录。",
    sourceFailed: "读取失败：{message}",
    available: "可用",
    failed: "失败",
    usingCache: "使用缓存",
  },
};

function t(key, replacements = {}) {
  let text = translations.zh[key] || key;
  Object.entries(replacements).forEach(([name, value]) => {
    text = text.replaceAll(`{${name}}`, value);
  });
  return text;
}

function applyLanguage() {
  document.documentElement.lang = "zh-CN";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
    node.setAttribute("placeholder", t(node.dataset.i18nPlaceholder));
  });
}

function formatDateTime(match) {
  if (!match.starts_at) return `${match.date || ""} ${match.time || ""}`.trim();
  const date = new Date(match.starts_at);
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function setBusy(isBusy, label = t("loading")) {
  state.loading = isBusy;
  els.updateBtn.disabled = isBusy;
  els.recalcBtn.disabled = isBusy;
  if (isBusy) els.statusLine.textContent = label;
}

function showNotice(message) {
  if (!message) {
    els.notice.classList.add("hidden");
    els.notice.textContent = "";
    return;
  }
  els.notice.textContent = message;
  els.notice.classList.remove("hidden");
}

function percent(value) {
  if (value === null || value === undefined) return "--";
  return `${Number(value).toFixed(1)}%`;
}

function confidenceClass(label) {
  if (label === "低") return "low";
  if (label === "待定") return "pending";
  return "";
}

function confidenceText(label) {
  return label || t("pending");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json();
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function taskRunning(payload = {}) {
  return Boolean(payload.task && payload.task.running);
}

function taskMessage(payload = {}, fallback = t("loading")) {
  return (payload.task && payload.task.message) || payload.message || fallback;
}

function renderSummary(summary = {}) {
  const items = [
    [t("matches"), summary.match_count ?? "--"],
    [t("teams"), summary.team_count ?? "--"],
    [t("historyRows"), summary.result_rows ?? "--"],
    [t("worldCupRows"), summary.world_cup_rows ?? "--"],
    [t("marketSignal"), summary.market_signal_available ? t("enabled") : t("disabled")],
    [t("bettingSignal"), summary.betting_signal_available ? t("enabled") : t("disabled")],
    [t("simulations"), summary.tournament_simulations ?? "--"],
  ];
  els.summaryGrid.innerHTML = items
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderPerformance(performance = {}) {
  const sampleSize = performance.sample_size || 0;
  els.performanceTag.textContent = sampleSize ? `${sampleSize} / ${sampleSize}` : "--";
  const metrics = [
    [t("actualSamples"), sampleSize],
    [t("outcomeAccuracy"), performance.outcome_accuracy ?? "--"],
    [t("exactScoreAccuracy"), performance.exact_score_accuracy ?? "--"],
    [t("averageGoalError"), performance.average_goal_error ?? "--"],
  ];
  els.performanceGrid.innerHTML = metrics
    .map(([label, value]) => `<div class="metric"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");

  const rows = performance.completed_matches || [];
  if (!rows.length) {
    els.resultComparison.innerHTML = `<div class="empty-line">${escapeHtml(t("noActualResults"))}</div>`;
    return;
  }
  els.resultComparison.innerHTML = `
    <div class="comparison-note">${escapeHtml(performance.note || t("earlySampleNote"))}</div>
    <div class="comparison-head">
      <span>${escapeHtml(t("completedComparison"))}</span>
      <span>${escapeHtml(t("prediction"))}</span>
      <span>${escapeHtml(t("actual"))}</span>
      <span>${escapeHtml(t("result"))}</span>
    </div>
    ${rows.map((row) => `
      <div class="comparison-row">
        <span>${escapeHtml(row.team1)} vs ${escapeHtml(row.team2)}</span>
        <strong>${escapeHtml(row.predicted_score || "--")}</strong>
        <strong>${escapeHtml(row.actual_score || "--")}</strong>
        <span class="${row.exact_score_hit ? "hit" : row.outcome_hit ? "partial-hit" : "miss"}">
          ${escapeHtml(row.exact_score_hit ? t("exactHit") : row.outcome_hit ? t("outcomeHit") : t("miss"))}
        </span>
      </div>
    `).join("")}
  `;
}

function renderTournament(tournament = {}) {
  const probabilities = tournament.stage_probabilities || [];
  const topChampions = probabilities.slice(0, 6);
  els.simulationCount.textContent = tournament.simulations ? t("championSimulations", { count: tournament.simulations }) : "--";
  if (!topChampions.length) {
    els.championStrip.innerHTML = `<div class="empty-line">${escapeHtml(t("noTournament"))}</div>`;
    els.stageGrid.innerHTML = "";
    els.bracketGrid.innerHTML = "";
    return;
  }
  els.championStrip.innerHTML = topChampions.map((team, index) => `
    <div class="champion-item">
      <span>${index + 1}</span>
      <strong>${escapeHtml(team.team)}</strong>
      <em>${percent(team.champion)}</em>
    </div>
  `).join("");

  const stageDefs = [
    ["round_of_32", t("roundOf32")],
    ["round_of_16", t("roundOf16")],
    ["quarter_final", t("quarterFinal")],
    ["semi_final", t("semiFinal")],
    ["final", t("final")],
  ];
  els.stageGrid.innerHTML = stageDefs.map(([key, label]) => {
    const teams = [...probabilities]
      .sort((a, b) => Number(b[key] || 0) - Number(a[key] || 0) || a.team.localeCompare(b.team))
      .slice(0, 8);
    return `
      <section class="stage-card">
        <h3>${escapeHtml(label)}</h3>
        ${teams.map((team) => `
          <div class="stage-row">
            <span>${escapeHtml(team.team)}</span>
            <strong>${percent(team[key])}</strong>
          </div>
        `).join("")}
      </section>
    `;
  }).join("");

  const matchupRounds = tournament.matchup_rounds || buildMatchupRoundsFromLegacy(tournament);
  els.bracketGrid.innerHTML = matchupRounds.map(renderMatchupRound).join("");
}

function buildMatchupRoundsFromLegacy(tournament = {}) {
  const projected = tournament.projected_matches || [];
  const stageMap = new Map((tournament.predicted_stages || []).map((stage) => [stage.key, stage.teams || []]));
  const defs = [
    ["round_of_32", "32强对阵"],
    ["round_of_16", "16强对阵"],
    ["quarter_final", "8强对阵"],
    ["semi_finalists", "4强名单"],
    ["semi_final", "半决赛对阵"],
    ["final", "决赛对阵"],
  ];
  return defs.map(([key, label]) => {
    if (key === "semi_finalists") {
      return { key, label, type: "teams", teams: stageMap.get("semi_final") || [] };
    }
    return { key, label, type: "matches", matches: projected.filter((match) => match.stage_key === key) };
  });
}

function renderMatchupRound(round) {
  if (round.type === "teams") {
    const teams = round.teams || [];
    return `
      <section class="bracket-round team-round">
        <h3>${escapeHtml(round.label)}</h3>
        <div class="team-chip-list">
          ${teams.map((team) => `<span class="team-chip">${escapeHtml(team)}</span>`).join("") || `<span class="empty-line">待定</span>`}
        </div>
      </section>
    `;
  }
  const rows = round.matches || [];
  return `
    <section class="bracket-round">
      <h3>${escapeHtml(round.label)}</h3>
      ${rows.map((match) => `
        <div class="bracket-match">
          <span class="matchup-line">${escapeHtml(match.team1)} <em>vs</em> ${escapeHtml(match.team2)}</span>
          <strong>${escapeHtml(match.winner || "待定")}</strong>
          <small>${escapeHtml(match.predicted_score || "")} · ${escapeHtml(match.confidence_label || "")}</small>
        </div>
      `).join("") || `<div class="empty-line">待定</div>`}
    </section>
  `;
}

function fillSelect(select, values, allLabel) {
  const current = select.value;
  const options = [`<option value="">${allLabel}</option>`].concat(
    (values || []).map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
  );
  select.innerHTML = options.join("");
  if ([...select.options].some((option) => option.value === current)) {
    select.value = current;
  }
}

function renderFilters(filters = {}) {
  fillSelect(els.roundFilter, filters.rounds || [], t("allRounds"));
  fillSelect(els.teamFilter, filters.teams || [], t("allTeams"));
}

function filteredMatches() {
  const round = els.roundFilter.value;
  const team = els.teamFilter.value;
  const confidence = els.confidenceFilter.value;
  const query = els.searchInput.value.trim().toLowerCase();
  return state.matches.filter((match) => {
    if (round && match.round !== round) return false;
    if (team && match.team1 !== team && match.team2 !== team) return false;
    if (confidence && match.confidence_label !== confidence) return false;
    if (query) {
      const haystack = `${match.team1} ${match.team2} ${match.ground} ${match.round} ${match.group}`.toLowerCase();
      if (!haystack.includes(query)) return false;
    }
    return true;
  });
}

function renderMatches() {
  const matches = filteredMatches();
  if (!matches.length) {
    els.matchList.innerHTML = `<div class="notice">${escapeHtml(t("noFilteredMatches"))}</div>`;
    return;
  }
  els.matchList.innerHTML = matches.map(renderMatchRow).join("");
  document.querySelectorAll(".match-row").forEach((row) => {
    row.addEventListener("click", () => loadMatchDetail(row.dataset.id));
  });
}

function renderMatchRow(match) {
  const probs = match.probabilities;
  const team1Prob = probs ? probs.team1_win : null;
  const drawProb = probs ? probs.draw : null;
  const team2Prob = probs ? probs.team2_win : null;
  return `
    <button class="match-row ${state.selectedId === match.id ? "active" : ""}" data-id="${escapeHtml(match.id)}">
      <div class="match-meta">
        <strong>${escapeHtml(match.round || "")}</strong><br />
        ${escapeHtml(match.group || match.status || "")}<br />
        ${escapeHtml(formatDateTime(match))}
      </div>
      <div class="teams">
        <div class="team-line">
          <span class="team-name">${escapeHtml(match.team1 || "待定")}</span>
          <span class="team-prob">${percent(team1Prob)}</span>
        </div>
        <div class="team-line">
          <span class="team-name">${escapeHtml(match.team2 || "待定")}</span>
          <span class="team-prob">${percent(team2Prob)}</span>
        </div>
        <div class="match-meta">${escapeHtml(match.ground || "")}</div>
      </div>
      <div class="prob-strip">
        ${bar(t("homeWin"), team1Prob, "")}
        ${bar(t("draw"), drawProb, "draw")}
        ${bar(t("awayWin"), team2Prob, "away")}
      </div>
      <div class="prediction-cell">
        <span class="score">${escapeHtml(match.predicted_score || "待定")}</span>
        <span class="badge ${confidenceClass(match.confidence_label)}">${escapeHtml(confidenceText(match.confidence_label))}</span>
      </div>
    </button>
  `;
}

function bar(label, value, className) {
  const width = value === null || value === undefined ? 0 : Math.max(0, Math.min(100, Number(value)));
  return `
    <div>
      <div class="match-meta">${label} ${percent(value)}</div>
      <div class="bar ${className}"><span style="width:${width}%"></span></div>
    </div>
  `;
}

async function loadStatus() {
  const status = await api("/api/status");
  state.lastStatus = status;
  renderSummary(status.summary);
  if (taskRunning(status)) {
    els.statusLine.textContent = taskMessage(status);
  } else if (status.generated_at) {
    els.statusLine.textContent = t("modelUpdated", {
      version: status.model_version,
      time: new Date(status.generated_at).toLocaleString("zh-CN"),
    });
  } else {
    els.statusLine.textContent = t("noData");
  }
  showNotice(status.error);
  return status;
}

async function loadMatches() {
  const payload = await api("/api/matches");
  state.matches = payload.matches || [];
  state.filters = payload.filters || {};
  state.tournament = payload.tournament || {};
  state.performance = payload.performance || {};
  renderSummary(payload.summary);
  renderPerformance(state.performance);
  renderFilters(state.filters);
  renderTournament(state.tournament);
  renderMatches();
  showNotice(payload.error);
  return payload;
}

async function waitForBackgroundTask(label) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    await sleep(3000);
    const status = await loadStatus();
    if (!taskRunning(status)) {
      await loadMatches();
      return;
    }
    setBusy(true, taskMessage(status, label));
  }
  showNotice(t("stillRunning"));
  await loadMatches();
}

async function updateData() {
  const label = t("updating");
  setBusy(true, label);
  try {
    const payload = await api("/api/update", { method: "POST" });
    showNotice(payload.error || payload.message);
    if (taskRunning(payload)) {
      await waitForBackgroundTask(label);
    } else {
      await loadMatches();
    }
  } catch (error) {
    showNotice(t("updateFailed", { message: error.message }));
  } finally {
    setBusy(false);
  }
}

async function recalculateModel() {
  const label = t("recalculating");
  setBusy(true, label);
  try {
    const payload = await api("/api/recalculate", { method: "POST" });
    showNotice(payload.error || payload.message);
    if (taskRunning(payload)) {
      await waitForBackgroundTask(label);
    } else {
      await loadMatches();
    }
  } catch (error) {
    showNotice(t("recalcFailed", { message: error.message }));
  } finally {
    setBusy(false);
  }
}

async function loadMatchDetail(matchId) {
  state.selectedId = matchId;
  renderMatches();
  els.detailPanel.innerHTML = `<div class="empty-detail"><h2>${escapeHtml(t("loading"))}</h2></div>`;
  try {
    const match = await api(`/api/matches/${encodeURIComponent(matchId)}`);
    renderDetail(match);
  } catch (error) {
    els.detailPanel.innerHTML = `<div class="notice">${escapeHtml(t("detailFailed", { message: error.message }))}</div>`;
  }
}

function renderDetail(match) {
  if (!match.teams_confirmed) {
    els.detailPanel.innerHTML = `
      <h2>${escapeHtml(match.team1 || "待定")} vs ${escapeHtml(match.team2 || "待定")}</h2>
      <p class="detail-sub">${escapeHtml(match.round || "")} · ${escapeHtml(match.ground || "")}</p>
      <div class="notice">${escapeHtml((match.explanation || [t("unavailablePrediction")])[0])}</div>
    `;
    return;
  }
  const probs = match.probabilities;
  const bettingMarket = match.betting_market || { team1: {}, team2: {} };
  const tradeMarket = match.market || { team1: {}, team2: {} };
  els.detailPanel.innerHTML = `
    <h2>${escapeHtml(match.team1)} vs ${escapeHtml(match.team2)}</h2>
    <p class="detail-sub">${escapeHtml(match.round || "")} · ${escapeHtml(match.ground || "")} · ${escapeHtml(formatDateTime(match))}</p>
    <div class="prob-grid">
      ${probBox(match.team1, probs.team1_win)}
      ${probBox("平局", probs.draw)}
      ${probBox(match.team2, probs.team2_win)}
    </div>
    <div class="kv-list">
      <div class="kv"><span>${escapeHtml(t("representativeScore"))}</span><strong>${escapeHtml(match.predicted_score)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("modalScore"))}</span><strong>${escapeHtml((match.score_summary || {}).modal_score || match.predicted_score)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("favorite"))}</span><strong>${escapeHtml(match.favorite)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("confidence"))}</span><strong>${escapeHtml(confidenceText(match.confidence_label))}</strong></div>
      <div class="kv"><span>${escapeHtml(t("expectedGoals"))}</span><strong>${match.expected_goals.team1} : ${match.expected_goals.team2}</strong></div>
      <div class="kv"><span>${escapeHtml(t("expectedTotalGoals"))}</span><strong>${(match.score_summary || {}).expected_total_goals ?? "--"}</strong></div>
      <div class="kv"><span>${escapeHtml(t("over25"))}</span><strong>${percent((match.score_summary || {}).over_2_5)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("bothScore"))}</span><strong>${percent((match.score_summary || {}).both_teams_score)}</strong></div>
    </div>
    ${renderAdvance(match)}
    <h3 class="section-title">${escapeHtml(t("modelExplanation"))}</h3>
    <div class="kv-list">
      ${(match.explanation || []).map((item) => `<div class="kv"><span>${escapeHtml(item)}</span></div>`).join("")}
    </div>
    <h3 class="section-title">${escapeHtml(t("contributors"))}</h3>
    <div class="kv-list">
      ${(match.contributors || []).map(renderContributor).join("")}
    </div>
    <h3 class="section-title">${escapeHtml(t("scoreDistribution"))}</h3>
    <div class="score-list">
      ${(match.scoreline_distribution || []).map((item) => `<div class="score-pill"><strong>${escapeHtml(item.score)}</strong><span>${percent(item.probability)}</span></div>`).join("")}
    </div>
    <h3 class="section-title">${escapeHtml(t("teamMetrics"))}</h3>
    <div class="kv-list">
      ${renderTeamMetric(match.team1, match.team_metrics[match.team1], tradeMarket.team1, bettingMarket.team1)}
      ${renderTeamMetric(match.team2, match.team_metrics[match.team2], tradeMarket.team2, bettingMarket.team2)}
    </div>
  `;
}

function probBox(label, value) {
  return `<div class="prob-box"><span>${escapeHtml(label)}</span><strong>${percent(value)}</strong></div>`;
}

function renderContributor(item) {
  const value = Number(item.value || 0);
  const sign = value > 0 ? "+" : "";
  return `
    <div class="kv">
      <span>${escapeHtml(item.name)}<small>${escapeHtml(item.description || "")}</small></span>
      <strong>${sign}${value.toFixed(1)}</strong>
    </div>
  `;
}

function renderTeamMetric(team, metric = {}, market = {}, betting = {}) {
  return `
    <div class="kv">
      <span>${escapeHtml(team)}
        <small>Elo ${metric.elo ?? "--"} · 高盛修正 ${metric.goldman_adjustment ?? "--"} · 世界杯阶段 ${metric.world_cup_stage_adjustment ?? "--"} · 淘汰赛 ${metric.world_cup_knockout_matches ?? 0} 场 · 攻 ${metric.goldman_attack ?? metric.attack ?? "--"} / 防 ${metric.goldman_defense ?? metric.defense ?? "--"}</small>
      </span>
      <strong>热度 ${market.index ?? 0} · 盘口 ${betting.index ?? 0}</strong>
    </div>
  `;
}

function renderAdvance(match) {
  if (!match.advance_probabilities) return "";
  return `
    <h3 class="section-title">${escapeHtml(t("knockoutAdvance"))}</h3>
    <div class="kv-list">
      <div class="kv"><span>${escapeHtml(match.team1)}</span><strong>${percent(match.advance_probabilities.team1)}</strong></div>
      <div class="kv"><span>${escapeHtml(match.team2)}</span><strong>${percent(match.advance_probabilities.team2)}</strong></div>
      <div class="kv"><span>${escapeHtml(match.advance_probabilities.note)}</span></div>
    </div>
  `;
}

async function openSources() {
  els.sourceDrawer.classList.remove("hidden");
  els.sourceList.innerHTML = `<div class="source-item">${escapeHtml(t("sourceLoading"))}</div>`;
  try {
    const sources = await api("/api/sources");
    if (!sources.length) {
      els.sourceList.innerHTML = `<div class="source-item">${escapeHtml(t("noSources"))}</div>`;
      return;
    }
    els.sourceList.innerHTML = sources.map(renderSource).join("");
  } catch (error) {
    els.sourceList.innerHTML = `<div class="source-item bad">${escapeHtml(t("sourceFailed", { message: error.message }))}</div>`;
  }
}

function renderSource(source) {
  return `
    <div class="source-item">
      <strong class="${source.ok ? "ok" : "bad"}">${escapeHtml(source.name)} · ${source.ok ? t("available") : t("failed")}</strong>
      <p>${escapeHtml(source.message || "")}${source.using_cache ? ` · ${t("usingCache")}` : ""}</p>
      <p>${escapeHtml(source.url || "")}</p>
    </div>
  `;
}

function closeSources() {
  els.sourceDrawer.classList.add("hidden");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function bindEvents() {
  els.updateBtn.addEventListener("click", updateData);
  els.recalcBtn.addEventListener("click", recalculateModel);
  els.sourcesBtn.addEventListener("click", openSources);
  els.closeDrawerBtn.addEventListener("click", closeSources);
  els.drawerBackdrop.addEventListener("click", closeSources);
  [els.roundFilter, els.teamFilter, els.confidenceFilter].forEach((el) => el.addEventListener("change", renderMatches));
  els.searchInput.addEventListener("input", renderMatches);
}

async function init() {
  applyLanguage();
  bindEvents();
  try {
    const status = await loadStatus();
    const payload = await loadMatches();
    if (!status.generated_at && !payload.matches.length) {
      await updateData();
    }
  } catch (error) {
    showNotice(t("initFailed", { message: error.message }));
  }
}

init();
