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
  visitorTotal: document.querySelector("#visitorTotal"),
  visitorToday: document.querySelector("#visitorToday"),
  visitorNote: document.querySelector("#visitorNote"),
  updateBtn: document.querySelector("#updateBtn"),
  reviewBtn: document.querySelector("#reviewBtn"),
  sourcesBtn: document.querySelector("#sourcesBtn"),
  summaryGrid: document.querySelector("#summaryGrid"),
  reviewPanel: document.querySelector("#reviewPanel"),
  reviewTag: document.querySelector("#reviewTag"),
  reviewSummary: document.querySelector("#reviewSummary"),
  reviewMetrics: document.querySelector("#reviewMetrics"),
  reviewCharts: document.querySelector("#reviewCharts"),
  reviewStageTable: document.querySelector("#reviewStageTable"),
  performanceTag: document.querySelector("#performanceTag"),
  performanceGrid: document.querySelector("#performanceGrid"),
  resultComparison: document.querySelector("#resultComparison"),
  simulationCount: document.querySelector("#simulationCount"),
  championStrip: document.querySelector("#championStrip"),
  stageGrid: document.querySelector("#stageGrid"),
  bracketGrid: document.querySelector("#bracketGrid"),
  bettingDayTag: document.querySelector("#bettingDayTag"),
  bettingNote: document.querySelector("#bettingNote"),
  bettingList: document.querySelector("#bettingList"),
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

const VISITOR_HIGH_WATER_KEY = "worldcupPredictorVisitorTotal";

const translations = {
  zh: {
    appTitle: "2026 男足世界杯预测",
    loadingStatus: "正在读取模型状态...",
    updateData: "更新数据并重算",
    reviewButton: "统计回顾",
    sourceStatus: "来源状态",
    reviewTitle: "统计回顾",
    performanceTitle: "真实赛果对比",
    tournamentTitle: "淘汰赛推演",
    bettingValueTitle: "当日比赛分析预测",
    fairOdds: "公平赔率",
    valueOdds: "价值赔率",
    bookmakerOverround: "庄家超额水位",
    noBettingOdds: "以下按北京时间当日未完赛比赛生成总进球数、比分、半全场和爆冷观察；仅供赛前分析和理性观赛参考。",
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
    contextSignal: "临场信息",
    technicalStatsSignal: "技术统计",
    simulations: "模拟次数",
    enabled: "已启用",
    disabled: "未启用",
    actualSamples: "真实样本",
    outcomeAccuracy: "方向命中",
    exactScoreAccuracy: "比分命中",
    averageGoalError: "平均进球误差",
    completedComparison: "已完赛对比",
    prediction: "模型预测",
    regularTimePrediction: "90分钟预测",
    regularTimeActual: "90分钟真实",
    extraTimePrediction: "加时比分",
    penaltyPrediction: "点球比分",
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
    updating: "正在联网更新数据源并重新计算模型...",
    stillRunning: "后台任务仍在运行，稍后会继续更新；你可以过一会儿刷新页面查看结果。",
    updateFailed: "更新数据失败：{message}",
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
    regularTimeScore: "90分钟预测比分",
    extraTimeScore: "加时比分参考",
    penaltyScore: "点球比分参考",
    modalScore: "精确众数比分",
    favorite: "预测倾向",
    expectedGoals: "预期进球 xG",
    expectedTotalGoals: "总 xG",
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
    visitorNote: "访问次数按页面打开计数，不记录个人身份信息。",
    visitorBaseline: "其中历史基数 {count} 次，当前程序已统计 {tracked} 次。",
  },
};

const teamNamesZh = {
  "Algeria": "阿尔及利亚",
  "Argentina": "阿根廷",
  "Australia": "澳大利亚",
  "Austria": "奥地利",
  "Belgium": "比利时",
  "Bosnia & Herzegovina": "波黑",
  "Brazil": "巴西",
  "Canada": "加拿大",
  "Cape Verde": "佛得角",
  "Colombia": "哥伦比亚",
  "Croatia": "克罗地亚",
  "Curacao": "库拉索",
  "Czech Republic": "捷克",
  "DR Congo": "刚果（金）",
  "Ecuador": "厄瓜多尔",
  "Egypt": "埃及",
  "England": "英格兰",
  "France": "法国",
  "Germany": "德国",
  "Ghana": "加纳",
  "Haiti": "海地",
  "Iran": "伊朗",
  "Iraq": "伊拉克",
  "Ivory Coast": "科特迪瓦",
  "Japan": "日本",
  "Jordan": "约旦",
  "Mexico": "墨西哥",
  "Morocco": "摩洛哥",
  "Netherlands": "荷兰",
  "New Zealand": "新西兰",
  "Norway": "挪威",
  "Panama": "巴拿马",
  "Paraguay": "巴拉圭",
  "Portugal": "葡萄牙",
  "Qatar": "卡塔尔",
  "Saudi Arabia": "沙特阿拉伯",
  "Scotland": "苏格兰",
  "Senegal": "塞内加尔",
  "South Africa": "南非",
  "South Korea": "韩国",
  "Spain": "西班牙",
  "Sweden": "瑞典",
  "Switzerland": "瑞士",
  "Tunisia": "突尼斯",
  "Turkey": "土耳其",
  "United States": "美国",
  "Uruguay": "乌拉圭",
  "Uzbekistan": "乌兹别克斯坦",
};

function teamName(value) {
  if (!value) return "待定";
  if (isPlaceholderTeamName(value)) return "待定";
  return teamNamesZh[value] || value;
}

function isPlaceholderTeamName(value) {
  const text = String(value || "").trim();
  return /^(W|L)\d{2,3}$/i.test(text)
    || /^[123][A-L](\/[A-L])*$/.test(text)
    || /winner|runner-up|runner up|tbd|to be decided|third/i.test(text);
}

function localizeTeamText(value) {
  let text = String(value ?? "");
  Object.entries(teamNamesZh)
    .sort((a, b) => b[0].length - a[0].length)
    .forEach(([english, chinese]) => {
      text = text.replaceAll(english, chinese);
    });
  return text;
}

function matchupName(team1, team2) {
  return `${teamName(team1)} vs ${teamName(team2)}`;
}

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
  return formatBeijingDateTime(match.starts_at);
}

function formatBeijingDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function beijingDateKey(match) {
  if (!match.starts_at) return match.date || "待定";
  const date = new Date(match.starts_at);
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function setBusy(isBusy, label = t("loading")) {
  state.loading = isBusy;
  els.updateBtn.disabled = isBusy;
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

function formatInteger(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("zh-CN").format(number);
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
    cache: "no-store",
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
    [t("contextSignal"), summary.context_signal_available ? t("enabled") : t("disabled")],
    [t("technicalStatsSignal"), summary.technical_stat_match_count ?? 0],
    [t("simulations"), summary.tournament_simulations ?? "--"],
  ];
  els.summaryGrid.innerHTML = items
    .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderVisitorStats(stats = {}) {
  if (!els.visitorTotal || !els.visitorToday || !els.visitorNote) return;
  rememberVisitorTotal(stats.total_visits);
  els.visitorTotal.textContent = formatInteger(stats.total_visits);
  els.visitorToday.textContent = formatInteger(stats.today_visits);
  const baseline = Number(stats.baseline_count || 0);
  const tracked = Number(stats.tracked_visits || 0);
  els.visitorNote.textContent = baseline > 0
    ? t("visitorBaseline", { count: formatInteger(baseline), tracked: formatInteger(tracked) })
    : (stats.note || t("visitorNote"));
}

async function recordVisit() {
  try {
    const stats = await api("/api/visits", { method: "POST" });
    const restored = await restoreVisitorTotalIfNeeded(stats);
    renderVisitorStats(restored);
  } catch (error) {
    try {
      renderVisitorStats(await api("/api/visits"));
    } catch (_) {
      if (els.visitorNote) els.visitorNote.textContent = "访问统计暂时不可用。";
    }
  }
}

async function restoreVisitorTotalIfNeeded(stats = {}) {
  const remembered = rememberedVisitorTotal();
  const total = Number(stats.total_visits || 0);
  if (remembered <= total) return stats;
  try {
    return await api("/api/visits/sync", {
      method: "POST",
      body: JSON.stringify({ min_total: remembered + 1 }),
    });
  } catch (_) {
    return { ...stats, total_visits: remembered + 1 };
  }
}

function rememberedVisitorTotal() {
  try {
    return Number(localStorage.getItem(VISITOR_HIGH_WATER_KEY) || 0);
  } catch (_) {
    return 0;
  }
}

function rememberVisitorTotal(value) {
  const total = Number(value || 0);
  if (!Number.isFinite(total) || total <= rememberedVisitorTotal()) return;
  try {
    localStorage.setItem(VISITOR_HIGH_WATER_KEY, String(Math.floor(total)));
  } catch (_) {}
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
      <span>${escapeHtml(t("regularTimePrediction"))}</span>
      <span>${escapeHtml(t("regularTimeActual"))}</span>
      <span>${escapeHtml(t("extraTimePrediction"))}</span>
      <span>${escapeHtml(t("penaltyPrediction"))}</span>
      <span>${escapeHtml(t("result"))}</span>
    </div>
    ${rows.map(renderPerformanceRow).join("")}
  `;
}

function renderPerformanceRow(row) {
  const extraTimeScore = row.extra_time_score || "不适用";
  const penaltyScore = row.penalty_score || "不适用";
  return `
    <div class="comparison-row">
      <span>${escapeHtml(matchupName(row.team1, row.team2))}<small>${escapeHtml(formatBeijingDateTime(row.starts_at))} 北京时间</small></span>
      <strong>${escapeHtml(row.predicted_score || "--")}</strong>
      <strong>${escapeHtml(row.actual_90_score || row.actual_score || "--")}</strong>
      <strong>${escapeHtml(extraTimeScore)}</strong>
      <strong>${escapeHtml(penaltyScore)}</strong>
      <span class="${row.exact_score_hit ? "hit" : row.outcome_hit ? "partial-hit" : "miss"}">
        ${escapeHtml(row.exact_score_hit ? t("exactHit") : row.outcome_hit ? t("outcomeHit") : t("miss"))}
      </span>
    </div>
  `;
}

function toggleReviewPanel() {
  if (!els.reviewPanel) return;
  els.reviewPanel.classList.toggle("hidden");
  if (!els.reviewPanel.classList.contains("hidden")) {
    renderReviewPanel();
    els.reviewPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function renderReviewPanel() {
  const review = buildReviewStats(state.matches, state.performance);
  els.reviewTag.textContent = review.finished ? "已完赛 · 全量复盘" : "进行中 · 动态复盘";
  els.reviewSummary.textContent = review.summaryText;
  els.reviewMetrics.innerHTML = review.metrics
    .map((item) => `
      <div class="review-metric">
        <span>${escapeHtml(item.label)}</span>
        <strong>${escapeHtml(item.value)}</strong>
        <small>${escapeHtml(item.note)}</small>
      </div>
    `).join("");
  els.reviewCharts.innerHTML = `
    ${renderReviewBarChart("预测命中率", review.accuracyBars)}
    ${renderReviewBarChart("阶段表现", review.stageBars)}
    ${renderReviewBarChart("预测倾向分布", review.outcomeBars)}
  `;
  els.reviewStageTable.innerHTML = renderReviewStageTable(review.stageRows);
}

function buildReviewStats(matches = [], performance = {}) {
  const completed = matches.filter((match) => match.actual_score && match.prediction_result);
  const sampleSize = completed.length || Number(performance.sample_size || 0);
  const outcomeHits = completed.filter((match) => (match.prediction_result || {}).outcome_hit).length;
  const exactHits = completed.filter((match) => (match.prediction_result || {}).exact_score_hit).length;
  const errors = completed
    .map((match) => Number((match.prediction_result || {}).goal_error))
    .filter((value) => Number.isFinite(value));
  const knockout = completed.filter((match) => match.is_knockout);
  const highConfidence = completed.filter((match) => match.confidence_label === "高");
  const finished = matches.length > 0 && matches.every((match) => match.actual_score || match.status === "已结束");
  const outcomeAccuracy = sampleSize ? outcomeHits / sampleSize * 100 : 0;
  const exactAccuracy = sampleSize ? exactHits / sampleSize * 100 : 0;
  const highConfidenceHits = highConfidence.filter((match) => (match.prediction_result || {}).outcome_hit).length;
  const highConfidenceAccuracy = highConfidence.length ? highConfidenceHits / highConfidence.length * 100 : 0;
  const averageError = errors.length ? errors.reduce((sum, value) => sum + value, 0) / errors.length : 0;
  const biggestMisses = [...completed]
    .filter((match) => Number.isFinite(Number((match.prediction_result || {}).goal_error)))
    .sort((a, b) => Number((b.prediction_result || {}).goal_error) - Number((a.prediction_result || {}).goal_error))
    .slice(0, 3);
  const stageRows = buildReviewStageRows(completed);
  const stageBars = stageRows.map((row) => ({ label: row.stage, value: row.outcomeAccuracy, detail: `${row.outcomeHits}/${row.count}` }));
  const predictedOutcomes = countBy(completed, (match) => (match.prediction_result || {}).predicted_outcome || "unknown");
  const outcomeBars = [
    { label: "主胜", value: percentOf(predictedOutcomes.team1_win || 0, sampleSize), detail: `${predictedOutcomes.team1_win || 0}场` },
    { label: "平局", value: percentOf(predictedOutcomes.draw || 0, sampleSize), detail: `${predictedOutcomes.draw || 0}场` },
    { label: "客胜", value: percentOf(predictedOutcomes.team2_win || 0, sampleSize), detail: `${predictedOutcomes.team2_win || 0}场` },
  ];
  const bestStage = [...stageRows].sort((a, b) => b.outcomeAccuracy - a.outcomeAccuracy)[0];
  const finalMatch = completed.find((match) => /^Final$/i.test(String(match.round || "").trim()));
  const champion = finalMatch ? actualWinnerName(finalMatch) : "待定";
  const runnerUp = finalMatch ? actualLoserName(finalMatch) : "待定";
  const topProjectedChampion = (state.tournament.stage_probabilities || [])[0]?.team || "";
  const championHit = champion !== "待定" && topProjectedChampion && canonicalTeamName(champion) === canonicalTeamName(topProjectedChampion);
  const missText = biggestMisses.length
    ? `偏差最大的场次是 ${biggestMisses.map((match) => `${teamName(match.team1)}vs${teamName(match.team2)}(${(match.prediction_result || {}).goal_error}球误差)`).join("、")}。`
    : "暂无明显异常场次。";
  return {
    finished,
    summaryText: sampleSize
      ? `共复盘 ${sampleSize} 场比赛，方向命中 ${formatPercent(outcomeAccuracy)}，比分命中 ${formatPercent(exactAccuracy)}，平均进球误差 ${averageError.toFixed(2)}。${bestStage ? `表现最好的阶段是${bestStage.stage}。` : ""}${missText}`
      : "暂无可复盘的完赛数据，请先更新赛果。",
    metrics: [
      { label: "复盘比赛", value: `${sampleSize}场`, note: finished ? "已覆盖全届世界杯" : "随赛果继续更新" },
      { label: "冠军结果", value: champion, note: runnerUp !== "待定" ? `亚军 ${runnerUp}${topProjectedChampion ? ` · 赛前冠军倾向 ${teamName(topProjectedChampion)}${championHit ? "命中" : "未命中"}` : ""}` : "等待决赛结果" },
      { label: "方向命中", value: formatPercent(outcomeAccuracy), note: `${outcomeHits}/${sampleSize} 场胜平负方向正确` },
      { label: "比分命中", value: formatPercent(exactAccuracy), note: `${exactHits}/${sampleSize} 场精确比分正确` },
      { label: "平均误差", value: averageError.toFixed(2), note: "预测比分与90分钟真实比分的总进球差" },
      { label: "淘汰赛样本", value: `${knockout.length}场`, note: "按90分钟口径复盘，另列加时/点球" },
      { label: "高置信命中", value: highConfidence.length ? formatPercent(highConfidenceAccuracy) : "--", note: `${highConfidenceHits}/${highConfidence.length} 场` },
    ],
    accuracyBars: [
      { label: "方向命中", value: outcomeAccuracy, detail: `${outcomeHits}/${sampleSize}` },
      { label: "比分命中", value: exactAccuracy, detail: `${exactHits}/${sampleSize}` },
      { label: "高置信方向", value: highConfidenceAccuracy, detail: `${highConfidenceHits}/${highConfidence.length}` },
    ],
    stageBars,
    outcomeBars,
    stageRows,
  };
}

function buildReviewStageRows(matches = []) {
  const groups = new Map();
  matches.forEach((match) => {
    const stage = stageLabelForReview(match);
    if (!groups.has(stage)) groups.set(stage, []);
    groups.get(stage).push(match);
  });
  return Array.from(groups.entries()).map(([stage, rows]) => {
    const outcomeHits = rows.filter((match) => (match.prediction_result || {}).outcome_hit).length;
    const exactHits = rows.filter((match) => (match.prediction_result || {}).exact_score_hit).length;
    const errors = rows.map((match) => Number((match.prediction_result || {}).goal_error)).filter((value) => Number.isFinite(value));
    return {
      stage,
      count: rows.length,
      outcomeHits,
      exactHits,
      outcomeAccuracy: percentOf(outcomeHits, rows.length),
      exactAccuracy: percentOf(exactHits, rows.length),
      averageError: errors.length ? errors.reduce((sum, value) => sum + value, 0) / errors.length : 0,
    };
  }).sort((a, b) => reviewStageOrder(a.stage) - reviewStageOrder(b.stage));
}

function renderReviewBarChart(title, rows = []) {
  return `
    <section class="review-chart-card">
      <h3>${escapeHtml(title)}</h3>
      ${rows.map((row) => `
        <div class="review-bar-row">
          <span>${escapeHtml(row.label)}</span>
          <div class="review-bar"><i style="width:${Math.max(0, Math.min(100, Number(row.value || 0)))}%"></i></div>
          <strong>${formatPercent(row.value)}</strong>
          <small>${escapeHtml(row.detail || "")}</small>
        </div>
      `).join("") || `<div class="empty-line">暂无数据</div>`}
    </section>
  `;
}

function renderReviewStageTable(rows = []) {
  return `
    <div class="review-table-head">
      <span>阶段</span><span>场次</span><span>方向命中</span><span>比分命中</span><span>平均误差</span>
    </div>
    ${rows.map((row) => `
      <div class="review-table-row">
        <span>${escapeHtml(row.stage)}</span>
        <strong>${row.count}</strong>
        <strong>${formatPercent(row.outcomeAccuracy)}</strong>
        <strong>${formatPercent(row.exactAccuracy)}</strong>
        <strong>${row.averageError.toFixed(2)}</strong>
      </div>
    `).join("") || `<div class="empty-line">暂无阶段复盘数据</div>`}
  `;
}

function stageLabelForReview(match = {}) {
  const round = String(match.round || match.stage || "");
  if (/Group/i.test(round) || match.group) return "小组赛";
  if (/Round of 32/i.test(round)) return "32强";
  if (/Round of 16/i.test(round)) return "16强";
  if (/Quarter/i.test(round)) return "8强";
  if (/Semi/i.test(round)) return "半决赛";
  if (/third/i.test(round)) return "三四名";
  if (/Final/i.test(round)) return "决赛";
  return round || "其他";
}

function reviewStageOrder(stage) {
  const index = ["小组赛", "32强", "16强", "8强", "半决赛", "三四名", "决赛", "其他"].indexOf(stage);
  return index < 0 ? 99 : index;
}

function countBy(rows, getter) {
  return rows.reduce((acc, row) => {
    const key = getter(row);
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function percentOf(count, total) {
  return total ? count / total * 100 : 0;
}

function formatPercent(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return "--";
  return `${Number(value).toFixed(1)}%`;
}

function actualWinnerName(match = {}) {
  const actual = match.actual_score || {};
  const team1 = Number(actual.team1);
  const team2 = Number(actual.team2);
  const penalty1 = Number(actual.penalty_team1);
  const penalty2 = Number(actual.penalty_team2);
  if (Number.isFinite(team1) && Number.isFinite(team2) && team1 !== team2) return team1 > team2 ? teamName(match.team1) : teamName(match.team2);
  if (Number.isFinite(penalty1) && Number.isFinite(penalty2) && penalty1 !== penalty2) return penalty1 > penalty2 ? teamName(match.team1) : teamName(match.team2);
  return "待定";
}

function actualLoserName(match = {}) {
  const winner = actualWinnerName(match);
  if (winner === "待定") return "待定";
  return winner === teamName(match.team1) ? teamName(match.team2) : teamName(match.team1);
}

function canonicalTeamName(value) {
  return String(teamName(value) || value || "").trim().toLowerCase();
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
      <strong>${escapeHtml(teamName(team.team))}</strong>
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
            <span>${escapeHtml(teamName(team.team))}</span>
            <strong>${percent(team[key])}</strong>
          </div>
        `).join("")}
      </section>
    `;
  }).join("");

  const matchupRounds = tournament.matchup_rounds || buildMatchupRoundsFromLegacy(tournament);
  els.bracketGrid.innerHTML = matchupRounds.map(renderMatchupRound).join("");
}

function renderBettingDailyFromMatches(matches = []) {
  const now = Date.now();
  const upcoming = [...matches]
    .filter((match) => match.teams_confirmed && !match.actual_score && match.betting_analysis && match.starts_at && new Date(match.starts_at).getTime() > now)
    .sort(compareMatchTime);
  if (!upcoming.length) {
    els.bettingDayTag.textContent = "--";
    els.bettingNote.textContent = t("noBettingOdds");
    els.bettingList.innerHTML = `<div class="empty-line">暂无未赛比赛。</div>`;
    return;
  }
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const availableDays = [...new Set(upcoming.map(beijingDateKey))].sort();
  const day = availableDays.includes(today) ? today : availableDays[0];
  const rows = upcoming.filter((match) => beijingDateKey(match) === day);
  const rowsWithRecommendations = attachDailyRecommendations(rows);
  els.bettingDayTag.textContent = `${day} 北京时间 · ${rows.length} 场`;
  els.bettingNote.textContent = t("noBettingOdds");
  els.bettingList.innerHTML = rowsWithRecommendations.map(renderBettingCard).join("");
}

function renderBettingDaily(payload = {}) {
  const current = payload.current_day || {};
  const rows = current.matches || [];
  if (!rows.length) {
    els.bettingDayTag.textContent = "--";
    els.bettingNote.textContent = "北京时间今天暂无未开赛投注参考。";
    els.bettingList.innerHTML = `<div class="empty-line">暂无未开赛比赛。</div>`;
    return;
  }
  els.bettingDayTag.textContent = `${current.date} 北京时间 · ${rows.length} 场`;
  els.bettingNote.textContent = payload.note || t("noBettingOdds");
  els.bettingList.innerHTML = rows.map(renderBettingCard).join("");
}

async function loadBettingDaily() {
  try {
    const payload = await api("/api/betting/daily");
    renderBettingDaily(payload);
  } catch (error) {
    renderBettingDailyFromMatches(state.matches);
    showNotice(`投注参考读取失败，已使用本地列表降级：${error.message}`);
  }
}

function attachDailyRecommendations(rows) {
  return rows.map((match) => ({
    ...match,
    daily_recommendation: match.daily_recommendation || buildClientDailyRecommendation(match),
  }));
}

function buildClientDailyRecommendation(match) {
  const probabilities = probabilityMap(match);
  const entries = Object.entries(probabilities).sort((a, b) => Number(b[1]) - Number(a[1]));
  const favorite = entries[0]?.[0] || "team1_win";
  const favoriteProbability = Number(entries[0]?.[1] || 0);
  const secondProbability = Number(entries[1]?.[1] || 0);
  const confidence = confidenceFromProbabilityGap(favoriteProbability, favoriteProbability - secondProbability);
  return {
    total_goals: buildClientTotalGoalsPick(match),
    score: buildClientScorePick(match),
    half_full: buildClientHalfFullPick(match, favorite, confidence),
    upset: buildClientUpsetPick(match, favorite),
  };
}

function probabilityMap(match) {
  const raw = (match.betting_analysis || {}).model_probabilities || match.probabilities || {};
  return {
    team1_win: Number(raw.team1_win || 0),
    draw: Number(raw.draw || 0),
    team2_win: Number(raw.team2_win || 0),
  };
}

function confidenceFromProbabilityGap(probability, gap) {
  if (probability >= 64 && gap >= 24) return "高";
  if (probability >= 48 && gap >= 10) return "中";
  return "观察";
}

function buildClientTotalGoalsPick(match) {
  const summary = match.score_summary || {};
  const expected = match.expected_goals || {};
  const expectedTotal = Number(summary.expected_total_goals ?? (Number(expected.team1 || 0) + Number(expected.team2 || 0)));
  const over25 = Number(summary.over_2_5 || 0);
  const over35 = Number(summary.over_3_5 || 0);
  const bothScore = Number(summary.both_teams_score || 0);
  let selection = "2-3球";
  let confidence = "观察";
  if (expectedTotal >= 3.6 || over35 >= 58) {
    selection = "4球及以上";
    confidence = over35 >= 62 ? "高" : "中";
  } else if (expectedTotal >= 2.75 || over25 >= 58) {
    selection = "3球左右";
    confidence = "中";
  } else if (expectedTotal <= 2.15 || over25 <= 42) {
    selection = "0-2球";
    confidence = "中";
  }
  return {
    play_type: "总进球数",
    selection,
    confidence,
    reason: `总 xG ${expectedTotal.toFixed(2)}，大2.5概率 ${over25.toFixed(1)}%，双方进球 ${bothScore.toFixed(1)}%。`,
  };
}

function buildClientScorePick(match) {
  const summary = match.score_summary || {};
  const primary = summary.representative_score || match.predicted_score || "待定";
  const modal = summary.modal_score || primary;
  const expected = match.expected_goals || {};
  return {
    play_type: "比分",
    selection: primary,
    secondary: modal !== primary ? modal : "",
    confidence: "观察",
    reason: `xG ${Number(expected.team1 || 0).toFixed(2)}:${Number(expected.team2 || 0).toFixed(2)}${modal !== primary ? `，精确众数比分 ${modal}。` : "。"}`
  };
}

function buildClientHalfFullPick(match, favorite, confidence) {
  const probabilities = probabilityMap(match);
  const expectedTotal = Number((match.score_summary || {}).expected_total_goals || 0);
  const drawProbability = Number(probabilities.draw || 0);
  const favoriteProbability = Number(probabilities[favorite] || 0);
  if (favorite === "draw" || (drawProbability >= 30 && favoriteProbability < 48)) {
    return {
      play_type: "半全场",
      selection: "平平",
      confidence,
      reason: `平局概率 ${drawProbability.toFixed(1)}%，双方差距不大。`,
    };
  }
  if (favorite === "team1_win") {
    return {
      play_type: "半全场",
      selection: favoriteProbability >= 62 && expectedTotal >= 2.7 ? "胜胜" : "平胜",
      confidence,
      reason: `${teamName(match.team1)} 取胜概率 ${favoriteProbability.toFixed(1)}%，上半场按谨慎节奏估计。`,
    };
  }
  return {
    play_type: "半全场",
    selection: favoriteProbability >= 62 && expectedTotal >= 2.7 ? "负负" : "平负",
    confidence,
    reason: `${teamName(match.team2)} 取胜概率 ${favoriteProbability.toFixed(1)}%，上半场按谨慎节奏估计。`,
  };
}

function buildClientUpsetPick(match, favorite) {
  const probabilities = probabilityMap(match);
  const threshold = (match.betting_analysis || {}).value_threshold_odds || {};
  const labels = { team1_win: teamName(match.team1), draw: "平局", team2_win: teamName(match.team2) };
  const favoriteProbability = Number(probabilities[favorite] || 0);
  const [coldKey, coldProbability] = Object.entries(probabilities)
    .filter(([key]) => key !== favorite)
    .sort((a, b) => Number(b[1]) - Number(a[1]))[0] || ["draw", 0];
  let selection;
  let confidence = "观察";
  let reason;
  if (favoriteProbability >= 66 && Number(coldProbability) < 22) {
    selection = "爆冷风险低";
    confidence = "高";
    reason = `热门方向概率 ${favoriteProbability.toFixed(1)}%，最大冷门方向 ${labels[coldKey]} 仅 ${Number(coldProbability).toFixed(1)}%。`;
  } else if (coldKey === "draw") {
    selection = "防平";
    confidence = Number(coldProbability) >= 24 ? "中" : "观察";
    reason = `平局概率 ${Number(coldProbability).toFixed(1)}%，适合列为冷门观察项。`;
  } else {
    selection = `关注${labels[coldKey]}爆冷`;
    reason = `${labels[coldKey]} 概率 ${Number(coldProbability).toFixed(1)}%，属于低概率高波动方向。`;
  }
  if (threshold[coldKey]) reason += ` 公开赔率高于 ${Number(threshold[coldKey]).toFixed(2)} 时才进入价值观察。`;
  return {
    play_type: "爆冷观察",
    selection,
    confidence,
    probability: Number(coldProbability),
    value_threshold_odds: threshold[coldKey] || null,
    reason,
  };
}

function renderBettingCard(match) {
  const analysis = match.betting_analysis || {};
  const fair = analysis.fair_odds || {};
  const threshold = analysis.value_threshold_odds || {};
  const probs = match.probabilities || {};
  const recommendation = match.daily_recommendation || buildClientDailyRecommendation(match);
  return `
    <div class="betting-card">
      <div>
        <strong>${escapeHtml(matchupName(match.team1, match.team2))}</strong>
        <small>${escapeHtml(formatDateTime(match))} · ${escapeHtml(match.round || "")} · ${escapeHtml(match.status || "")} · 预测 ${escapeHtml(match.predicted_score || "待定")}</small>
      </div>
      ${renderExpectedGoalsStrip(match)}
      ${renderDailyRecommendation(recommendation)}
      <div class="odds-grid">
        ${renderOddsCell(teamName(match.team1), probs.team1_win, fair.team1_win, threshold.team1_win)}
        ${renderOddsCell("平局", probs.draw, fair.draw, threshold.draw)}
        ${renderOddsCell(teamName(match.team2), probs.team2_win, fair.team2_win, threshold.team2_win)}
      </div>
      <p>${escapeHtml(localizeTeamText(analysis.suggestion || ""))}</p>
      ${renderLotteryReference(analysis.lottery_reference)}
      ${analysis.overround !== undefined ? `<p>${escapeHtml(t("bookmakerOverround"))}：${percent(analysis.overround)}</p>` : ""}
    </div>
  `;
}

function renderExpectedGoalsStrip(match = {}) {
  const expected = match.expected_goals || {};
  if (expected.team1 === undefined || expected.team2 === undefined) return "";
  const summary = match.score_summary || {};
  return `
    <div class="xg-strip">
      <span>${escapeHtml(t("expectedGoals"))}</span>
      <strong>${escapeHtml(teamName(match.team1))} ${Number(expected.team1 || 0).toFixed(2)} : ${Number(expected.team2 || 0).toFixed(2)} ${escapeHtml(teamName(match.team2))}</strong>
      <em>${escapeHtml(t("expectedTotalGoals"))} ${summary.expected_total_goals ?? (Number(expected.team1 || 0) + Number(expected.team2 || 0)).toFixed(2)} · 大2.5 ${percent(summary.over_2_5)} · 双方进球 ${percent(summary.both_teams_score)}</em>
    </div>
  `;
}

function formatExpectedGoals(expected = {}) {
  if (expected.team1 === undefined || expected.team2 === undefined) return "--";
  return `${Number(expected.team1 || 0).toFixed(2)}:${Number(expected.team2 || 0).toFixed(2)}`;
}

function renderDailyRecommendation(recommendation = {}) {
  const items = [
    recommendation.total_goals,
    recommendation.score,
    recommendation.half_full,
    recommendation.upset,
  ].filter(Boolean);
  if (!items.length) return "";
  return `
    <div class="analysis-pick-grid">
      ${items.map(renderAnalysisPick).join("")}
    </div>
  `;
}

function renderAnalysisPick(item = {}) {
  const secondary = item.secondary ? `<em>备选：${escapeHtml(localizeTeamText(item.secondary))}</em>` : "";
  return `
    <div class="analysis-pick ${item.play_type === "爆冷观察" ? "upset" : ""}">
      <span>${escapeHtml(item.play_type || "")}</span>
      <strong>${escapeHtml(localizeTeamText(item.selection || ""))}</strong>
      <em>置信度：${escapeHtml(item.confidence || "观察")}</em>
      ${secondary}
      <small>${escapeHtml(localizeTeamText(item.reason || ""))}</small>
    </div>
  `;
}

function renderLotteryReference(reference = {}) {
  if (!reference.source) return "";
  const playTypes = reference.play_types || [];
  return `
    <p>体彩口径：${escapeHtml(reference.primary_play || "胜平负")} · ${escapeHtml(reference.source)}</p>
    <p>玩法参考：${playTypes.map((item) => escapeHtml(item)).join(" / ")}</p>
  `;
}

function renderOddsCell(label, probability, fair, threshold) {
  return `
    <div class="odds-cell">
      <span>${escapeHtml(label)} ${percent(probability)}</span>
      <strong>${escapeHtml(t("fairOdds"))} ${fair ?? "--"}</strong>
      <em>${escapeHtml(t("valueOdds"))} >= ${threshold ?? "--"}</em>
    </div>
  `;
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
          ${teams.map((team) => `<span class="team-chip">${escapeHtml(teamName(team))}</span>`).join("") || `<span class="empty-line">待定</span>`}
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
          <span class="matchup-line">${escapeHtml(teamName(match.team1))} <em>vs</em> ${escapeHtml(teamName(match.team2))}</span>
          <strong>${escapeHtml(teamName(match.winner))}</strong>
          ${renderBracketScoreProjection(match)}
        </div>
      `).join("") || `<div class="empty-line">待定</div>`}
    </section>
  `;
}

function renderBracketScoreProjection(match = {}) {
  if (!match.is_knockout && !match.knockout_score_projection && !match.predicted_score) {
    return `<small>${escapeHtml(match.confidence_label || "")}</small>`;
  }
  const projection = knockoutProjection(match);
  return `
    <small>90分钟 ${escapeHtml(projection.regular_time_score || "待定")} · ${escapeHtml(match.confidence_label || "")}</small>
    <small>加时 ${escapeHtml(projection.extra_time_score || "待定")} · 点球 ${escapeHtml(projection.penalty_score || "待定")}</small>
  `;
}

function knockoutProjection(match = {}) {
  if (match.knockout_score_projection) return match.knockout_score_projection;
  const regular = match.predicted_score || "待定";
  const goals = parseScore(regular);
  const advance = match.advance_probabilities || {};
  const team1Advance = Number(advance.team1 || 50);
  const team2Advance = Number(advance.team2 || 50);
  const team1Favored = team1Advance >= team2Advance;
  if (!goals) {
    return {
      regular_time_score: regular,
      regular_time_note: "90分钟正赛比分，不含加时赛和点球大战。",
      extra_time_score: "待定",
      extra_time_note: "仅在90分钟打平时参考。",
      penalty_score: "待定",
      penalty_note: "点球波动极高，只按晋级倾向给出方向性参考。",
    };
  }
  if (goals[0] !== goals[1]) {
    return {
      regular_time_score: regular,
      regular_time_note: "90分钟正赛比分，不含加时赛和点球大战。",
      extra_time_score: "不适用",
      extra_time_note: "模型判断90分钟已分胜负，预计不进入加时。",
      penalty_score: "不适用",
      penalty_note: "模型判断90分钟已分胜负，预计不进入点球大战。",
    };
  }
  const extra = Math.abs(team1Advance - team2Advance) >= 8
    ? team1Favored ? `${goals[0] + 1}-${goals[1]}` : `${goals[0]}-${goals[1] + 1}`
    : regular;
  return {
    regular_time_score: regular,
    regular_time_note: "90分钟正赛比分，不含加时赛和点球大战。",
    extra_time_score: extra,
    extra_time_note: "仅在90分钟打平时参考。",
    penalty_score: team1Favored ? "4-3" : "3-4",
    penalty_note: `若进入点球，轻微倾向${teamName(team1Favored ? match.team1 : match.team2)}。`,
  };
}

function parseScore(score) {
  const match = String(score || "").match(/(\d+)\s*-\s*(\d+)/);
  return match ? [Number(match[1]), Number(match[2])] : null;
}

function fillSelect(select, values, allLabel) {
  const current = select.value;
  const options = [`<option value="">${allLabel}</option>`].concat(
    (values || []).map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(teamName(value))}</option>`)
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
  return state.matches
    .filter((match) => {
      if (round && match.round !== round) return false;
      if (team && match.team1 !== team && match.team2 !== team) return false;
      if (confidence && match.confidence_label !== confidence) return false;
      if (query) {
        const haystack = `${match.team1} ${match.team2} ${teamName(match.team1)} ${teamName(match.team2)} ${match.ground} ${match.round} ${match.group}`.toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    })
    .sort(compareMatchTime);
}

function compareMatchTime(a, b) {
  const timeA = a.starts_at ? new Date(a.starts_at).getTime() : Number.MAX_SAFE_INTEGER;
  const timeB = b.starts_at ? new Date(b.starts_at).getTime() : Number.MAX_SAFE_INTEGER;
  if (timeA !== timeB) return timeA - timeB;
  return Number(a.index || 0) - Number(b.index || 0);
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
  const actual = match.actual_score;
  const scoreLabel = actual
    ? `完赛 ${actual.score}`
    : match.is_knockout
      ? `90分钟 ${match.predicted_score || "待定"}`
      : match.predicted_score || "待定";
  return `
    <button class="match-row ${state.selectedId === match.id ? "active" : ""}" data-id="${escapeHtml(match.id)}">
      <div class="match-meta">
        <strong>${escapeHtml(match.round || "")}</strong><br />
        ${escapeHtml(match.group || match.status || "")}<br />
        ${escapeHtml(formatDateTime(match))}
      </div>
      <div class="teams">
        <div class="team-line">
          <span class="team-name">${escapeHtml(teamName(match.team1))}</span>
          <span class="team-prob">${percent(team1Prob)}</span>
        </div>
        <div class="team-line">
          <span class="team-name">${escapeHtml(teamName(match.team2))}</span>
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
        <span class="score">${escapeHtml(scoreLabel)}</span>
        ${actual ? `<span class="badge">真实赛果</span>` : ""}
        <span class="badge ${confidenceClass(match.confidence_label)}">${escapeHtml(confidenceText(match.confidence_label))}</span>
        ${renderContextBadges(match)}
      </div>
    </button>
  `;
}

function renderContextBadges(match) {
  const offField = match.off_field || {};
  const rules = match.rule_adaptation || {};
  const context = match.match_context || {};
  const offDelta = Number((offField.team1 || {}).adjustment || 0) - Number((offField.team2 || {}).adjustment || 0);
  const ruleDelta = Number(rules.team1 || 0) - Number(rules.team2 || 0);
  const contextDelta = Number((context.team1 || {}).adjustment || 0) - Number((context.team2 || {}).adjustment || 0);
  const badges = [];
  if (Math.abs(offDelta) >= 0.1) badges.push(`<span class="context-badge">场外 ${formatSigned(offDelta)}</span>`);
  if (Math.abs(ruleDelta) >= 0.1) badges.push(`<span class="context-badge">规则 ${formatSigned(ruleDelta)}</span>`);
  if (Math.abs(contextDelta) >= 0.1) badges.push(`<span class="context-badge">临场 ${formatSigned(contextDelta)}</span>`);
  return badges.join("");
}

function formatSigned(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${number.toFixed(1)}`;
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

async function loadStatus(options = {}) {
  const status = await api(options.forceSync ? "/api/status?force_sync=true" : "/api/status");
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
  await loadBettingDaily();
  renderMatches();
  if (els.reviewPanel && !els.reviewPanel.classList.contains("hidden")) {
    renderReviewPanel();
  }
  if (payload.generated_at) {
    els.statusLine.textContent = t("modelUpdated", {
      version: payload.model_version || (state.lastStatus || {}).model_version || "--",
      time: new Date(payload.generated_at).toLocaleString("zh-CN"),
    });
  } else if (!state.matches.length) {
    els.statusLine.textContent = t("noData");
  }
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
      <h2>${escapeHtml(matchupName(match.team1, match.team2))}</h2>
      <p class="detail-sub">${escapeHtml(match.round || "")} · ${escapeHtml(match.ground || "")}</p>
      <div class="notice">${escapeHtml((match.explanation || [t("unavailablePrediction")])[0])}</div>
    `;
    return;
  }
  const probs = match.probabilities;
  const bettingMarket = match.betting_market || { team1: {}, team2: {} };
  const matchContext = match.match_context || { team1: {}, team2: {} };
  const tradeMarket = match.market || { team1: {}, team2: {} };
  els.detailPanel.innerHTML = `
    <h2>${escapeHtml(matchupName(match.team1, match.team2))}</h2>
    <p class="detail-sub">${escapeHtml(match.round || "")} · ${escapeHtml(match.ground || "")} · ${escapeHtml(formatDateTime(match))}</p>
    <div class="prob-grid">
      ${probBox(teamName(match.team1), probs.team1_win)}
      ${probBox("平局", probs.draw)}
      ${probBox(teamName(match.team2), probs.team2_win)}
    </div>
    <div class="kv-list">
      <div class="kv"><span>${escapeHtml(match.is_knockout ? t("regularTimeScore") : t("representativeScore"))}</span><strong>${escapeHtml(match.predicted_score)}</strong></div>
      ${match.actual_score ? `<div class="kv"><span>真实赛果</span><strong>${escapeHtml(match.actual_score.score || "")}</strong></div>` : ""}
      <div class="kv"><span>${escapeHtml(t("modalScore"))}</span><strong>${escapeHtml((match.score_summary || {}).modal_score || match.predicted_score)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("favorite"))}</span><strong>${escapeHtml(teamName(match.favorite))}</strong></div>
      <div class="kv"><span>${escapeHtml(t("confidence"))}</span><strong>${escapeHtml(confidenceText(match.confidence_label))}</strong></div>
      <div class="kv"><span>${escapeHtml(t("expectedGoals"))}</span><strong>${match.expected_goals.team1} : ${match.expected_goals.team2}</strong></div>
      <div class="kv"><span>${escapeHtml(t("expectedTotalGoals"))}</span><strong>${(match.score_summary || {}).expected_total_goals ?? "--"}</strong></div>
      <div class="kv"><span>${escapeHtml(t("over25"))}</span><strong>${percent((match.score_summary || {}).over_2_5)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("bothScore"))}</span><strong>${percent((match.score_summary || {}).both_teams_score)}</strong></div>
    </div>
    ${renderKnockoutScoreProjection(match)}
    ${renderAdvance(match)}
    ${renderTechnicalIndicators(match)}
    ${renderBettingAnalysis(match)}
    <h3 class="section-title">${escapeHtml(t("modelExplanation"))}</h3>
    <div class="kv-list">
      ${(match.explanation || []).map((item) => `<div class="kv"><span>${escapeHtml(localizeTeamText(item))}</span></div>`).join("")}
    </div>
    <h3 class="section-title">${escapeHtml(t("contributors"))}</h3>
    <div class="kv-list">
      ${(match.contributors || []).map(renderContributor).join("")}
    </div>
    ${renderContextFactors(match)}
    <h3 class="section-title">${escapeHtml(t("scoreDistribution"))}</h3>
    <div class="score-list">
      ${(match.scoreline_distribution || []).map((item) => `<div class="score-pill"><strong>${escapeHtml(item.score)}</strong><span>${percent(item.probability)}</span></div>`).join("")}
    </div>
    <h3 class="section-title">${escapeHtml(t("teamMetrics"))}</h3>
    <div class="kv-list">
      ${renderTeamMetric(match.team1, match.team_metrics[match.team1], tradeMarket.team1, bettingMarket.team1)}
      ${renderTeamMetric(match.team2, match.team_metrics[match.team2], tradeMarket.team2, bettingMarket.team2)}
      ${renderContextMetric(match.team1, matchContext.team1)}
      ${renderContextMetric(match.team2, matchContext.team2)}
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
      <span>${escapeHtml(item.name)}<small>${escapeHtml(localizeTeamText(item.description || ""))}</small></span>
      <strong>${sign}${value.toFixed(1)}</strong>
    </div>
  `;
}

function renderContextFactors(match) {
  const offField = match.off_field || {};
  const rules = match.rule_adaptation || {};
  const rows = [];
  [offField.team1, offField.team2].forEach((signal, index) => {
    const team = index === 0 ? match.team1 : match.team2;
    (signal && signal.factors ? signal.factors : []).forEach((factor) => {
      rows.push(`
        <div class="kv">
          <span>${escapeHtml(teamName(team))}<small>${escapeHtml(factor.description || factor.name || "")}</small></span>
          <strong>${Number(factor.adjustment || 0).toFixed(1)}</strong>
        </div>
      `);
    });
  });
  if (rules.team1 !== undefined || rules.team2 !== undefined) {
    rows.push(`
      <div class="kv">
        <span>新规则适应性<small>补水暂停、门将持球限制、界外球/门球倒计时等综合影响。</small></span>
        <strong>${Number(rules.team1 || 0).toFixed(1)} : ${Number(rules.team2 || 0).toFixed(1)}</strong>
      </div>
    `);
  }
  if (!rows.length) return "";
  return `
    <h3 class="section-title">场外与规则因素</h3>
    <div class="kv-list">${rows.join("")}</div>
  `;
}

function renderTechnicalIndicators(match) {
  const projected = match.technical_indicators || {};
  const actual = match.technical_stats || {};
  if (!projected.available && !actual.available) return "";
  const profile = match.technical_profile || {};
  return `
    <h3 class="section-title">技术统计层</h3>
    <div class="kv-list">
      ${projected.available ? renderTechnicalBlock("赛前技术统计预测", projected.team1 || {}, projected.team2 || {}, match, projected.source_note) : ""}
      ${actual.available ? renderTechnicalBlock("真实技术统计", actual.team1 || {}, actual.team2 || {}, match, `${actual.source_name || ""}${actual.referee ? ` · 裁判 ${actual.referee}` : ""}`) : ""}
      ${profile.available ? `
        <div class="kv">
          <span>技术统计修正<small>${escapeHtml(profile.description || "")}</small></span>
          <strong>${formatSigned(profile.delta || 0)}</strong>
        </div>
      ` : ""}
    </div>
  `;
}

function renderTechnicalBlock(title, team1Stats, team2Stats, match, note = "") {
  const rows = [
    ["xg", "xG / 近似xG"],
    ["possession_pct", "控球率"],
    ["shots", "射门"],
    ["shots_on_target", "射正"],
    ["corners", "角球"],
    ["tackles", "抢断"],
    ["yellow_cards", "黄牌"],
    ["red_cards", "红牌"],
    ["substitutions", "换人"],
  ];
  return `
    <div class="kv">
      <span>${escapeHtml(title)}<small>${escapeHtml(note || "")}</small></span>
      <strong>${escapeHtml(teamName(match.team1))} : ${escapeHtml(teamName(match.team2))}</strong>
    </div>
    ${rows.map(([key, label]) => `
      <div class="kv">
        <span>${escapeHtml(label)}</span>
        <strong>${formatTechnicalValue(key, team1Stats)} : ${formatTechnicalValue(key, team2Stats)}</strong>
      </div>
    `).join("")}
  `;
}

function formatTechnicalValue(key, stats = {}) {
  const sourceKey = key === "xg" && stats.xg === undefined ? "xg_proxy" : key;
  const value = stats[sourceKey];
  if (value === undefined || value === null || value === "") return "--";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return escapeHtml(String(value));
  if (key === "possession_pct") return `${numeric.toFixed(1)}%`;
  if (key === "red_cards" || key === "xg") return numeric.toFixed(2);
  return numeric.toFixed(1);
}

function renderBettingAnalysis(match) {
  const analysis = match.betting_analysis || {};
  if (!analysis.available) return "";
  return `
    <h3 class="section-title">赔率价值参考</h3>
    <div class="betting-list">
      ${renderBettingCard(match)}
    </div>
  `;
}

function renderContextMetric(team, context = {}) {
  if (!context || !context.available) return "";
  return `
    <div class="kv">
      <span>${escapeHtml(teamName(team))}
        <small>伤停 ${context.injury_hits ?? 0} · 首发 ${context.lineup_hits ?? 0} · 裁判/天气 ${context.weather_referee_hits ?? 0}</small>
      </span>
      <strong>临场 ${formatSigned(context.adjustment || 0)}</strong>
    </div>
  `;
}

function renderTeamMetric(team, metric = {}, market = {}, betting = {}) {
  return `
    <div class="kv">
      <span>${escapeHtml(teamName(team))}
        <small>Elo ${metric.elo ?? "--"} · 高盛修正 ${metric.goldman_adjustment ?? "--"} · 世界杯阶段 ${metric.world_cup_stage_adjustment ?? "--"} · 淘汰赛 ${metric.world_cup_knockout_matches ?? 0} 场 · 攻 ${metric.goldman_attack ?? metric.attack ?? "--"} / 防 ${metric.goldman_defense ?? metric.defense ?? "--"}</small>
      </span>
      <strong>热度 ${market.index ?? 0} · 盘口 ${betting.index ?? 0}</strong>
    </div>
  `;
}

function renderKnockoutScoreProjection(match) {
  if (!match.is_knockout) return "";
  const projection = knockoutProjection(match);
  return `
    <h3 class="section-title">淘汰赛比分口径</h3>
    <div class="kv-list">
      <div class="kv">
        <span>${escapeHtml(t("regularTimeScore"))}<small>${escapeHtml(localizeTeamText(projection.regular_time_note || "90分钟正赛比分，不含加时赛和点球大战。"))}</small></span>
        <strong>${escapeHtml(projection.regular_time_score || match.predicted_score || "待定")}</strong>
      </div>
      <div class="kv">
        <span>${escapeHtml(t("extraTimeScore"))}<small>${escapeHtml(localizeTeamText(projection.extra_time_note || "仅在90分钟打平时参考。"))}</small></span>
        <strong>${escapeHtml(projection.extra_time_score || "待定")}</strong>
      </div>
      <div class="kv">
        <span>${escapeHtml(t("penaltyScore"))}<small>${escapeHtml(localizeTeamText(projection.penalty_note || "点球波动极高，只按晋级倾向给出方向性参考。"))}</small></span>
        <strong>${escapeHtml(projection.penalty_score || "待定")}</strong>
      </div>
    </div>
  `;
}

function renderAdvance(match) {
  if (!match.advance_probabilities) return "";
  return `
    <h3 class="section-title">${escapeHtml(t("knockoutAdvance"))}</h3>
    <div class="kv-list">
      <div class="kv"><span>${escapeHtml(teamName(match.team1))}</span><strong>${percent(match.advance_probabilities.team1)}</strong></div>
      <div class="kv"><span>${escapeHtml(teamName(match.team2))}</span><strong>${percent(match.advance_probabilities.team2)}</strong></div>
      <div class="kv"><span>${escapeHtml(localizeTeamText(match.advance_probabilities.note || ""))}</span></div>
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
  els.reviewBtn.addEventListener("click", toggleReviewPanel);
  els.sourcesBtn.addEventListener("click", openSources);
  els.closeDrawerBtn.addEventListener("click", closeSources);
  els.drawerBackdrop.addEventListener("click", closeSources);
  [els.roundFilter, els.teamFilter, els.confidenceFilter].forEach((el) => el.addEventListener("change", renderMatches));
  els.searchInput.addEventListener("input", renderMatches);
}

async function init() {
  applyLanguage();
  bindEvents();
  recordVisit();
  try {
    const status = await loadStatus({ forceSync: true });
    if (taskRunning(status)) {
      setBusy(true, taskMessage(status, "正在自动同步最新赛果并刷新预测。"));
      await waitForBackgroundTask("正在自动同步最新赛果并刷新预测。");
      setBusy(false);
      return;
    }
    const payload = await loadMatches();
    if (!status.generated_at && !payload.matches.length) {
      await updateData();
    }
  } catch (error) {
    showNotice(t("initFailed", { message: error.message }));
  }
}

init();

window.addEventListener("error", (event) => {
  showNotice(`页面脚本错误：${event.message}`);
});

window.addEventListener("unhandledrejection", (event) => {
  const message = event.reason && event.reason.message ? event.reason.message : String(event.reason || "未知错误");
  showNotice(`页面加载失败：${message}`);
});
