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

const translations = {
  zh: {
    appTitle: "2026 男足世界杯预测",
    loadingStatus: "正在读取模型状态...",
    updateData: "更新数据并重算",
    recalculate: "重新计算模型",
    sourceStatus: "来源状态",
    performanceTitle: "真实赛果对比",
    tournamentTitle: "淘汰赛推演",
    bettingValueTitle: "当日投注价值参考",
    fairOdds: "公平赔率",
    valueOdds: "价值赔率",
    bookmakerOverround: "庄家超额水位",
    noBettingOdds: "以下按北京时间当日未完赛比赛生成，金额为每日 50 元示例预算，不构成购彩保证。",
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
    updating: "正在联网更新数据源并重新计算模型...",
    recalculating: "正在使用本地缓存重新计算模型...",
    stillRunning: "后台任务仍在运行，稍后会继续更新；你可以过一会儿刷新页面查看结果。",
    updateFailed: "更新数据失败：{message}",
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
  return teamNamesZh[value] || value;
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
        <span>${escapeHtml(matchupName(row.team1, row.team2))}<small>${escapeHtml(formatBeijingDateTime(row.starts_at))} 北京时间</small></span>
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
  const rowsWithStakes = attachBettingStakes(rows, 50);
  els.bettingDayTag.textContent = `${day} 北京时间 · ${rows.length} 场 · 示例预算 50 元`;
  els.bettingNote.textContent = t("noBettingOdds");
  els.bettingList.innerHTML = `${renderMixedPassPlan(buildClientMixedPassPlan(rowsWithStakes, 50))}${rowsWithStakes.map(renderBettingCard).join("")}`;
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
  els.bettingDayTag.textContent = `${current.date} 北京时间 · ${rows.length} 场 · 示例预算 ${Number(current.budget || 50).toFixed(0)} 元`;
  els.bettingNote.textContent = payload.note || t("noBettingOdds");
  els.bettingList.innerHTML = `${renderMixedPassPlan(current.mixed_pass_plan)}${rows.map(renderBettingCard).join("")}`;
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

function attachBettingStakes(rows, budget) {
  const weighted = rows.map((match) => {
    const probs = Object.values((match.betting_analysis || {}).model_probabilities || match.probabilities || {}).map(Number).sort((a, b) => b - a);
    const gap = probs.length > 1 ? probs[0] - probs[1] : probs[0] || 10;
    return { match, weight: Math.max(0.8, gap / 10) };
  });
  const totalWeight = weighted.reduce((sum, item) => sum + item.weight, 0) || 1;
  let used = 0;
  return weighted.map((item, index) => {
    const copy = { ...item.match };
    let stake = Math.max(2, Math.round((budget * item.weight / totalWeight) / 2) * 2);
    if (index === weighted.length - 1) stake = Math.max(2, Math.round((budget - used) / 2) * 2);
    used += stake;
    copy.betting_recommendation = buildClientBettingRecommendation(copy, stake);
    return copy;
  });
}

function buildClientBettingRecommendation(match, stake) {
  const analysis = match.betting_analysis || {};
  const probabilities = analysis.model_probabilities || match.probabilities || {};
  const favorite = analysis.favorite || Object.entries(probabilities).sort((a, b) => Number(b[1]) - Number(a[1]))[0]?.[0] || "team1_win";
  const labels = { team1_win: teamName(match.team1), draw: "平局", team2_win: teamName(match.team2) };
  const quoted = analysis.quoted_odds || {};
  const threshold = analysis.value_threshold_odds || {};
  const fair = analysis.fair_odds || {};
  const odds = Number(quoted[favorite] || threshold[favorite] || fair[favorite] || 1);
  return {
    play_type: "竞彩足球胜平负",
    selection: labels[favorite] || favorite,
    stake,
    reference_odds: odds,
    odds_type: quoted[favorite] ? "真实赔率" : "建议最低参考赔率",
    possible_payout: Number((stake * odds).toFixed(2)),
    possible_profit: Number((stake * odds - stake).toFixed(2)),
  };
}

function buildClientMixedPassPlan(rows = [], budget = 50) {
  const bettable = rows.filter((row) => row.bettable !== false && row.betting_recommendation?.reference_odds).slice(0, 4);
  if (bettable.length < 3) {
    return {
      available: false,
      title: "50元冲击万元目标混合过关",
      summary: "北京时间当日可投注比赛少于 3 场，暂不生成 3串1/4串1 混合过关方案。",
      warning: "过关投注需要组合内所有选择同时命中才中奖，不能保证收益。",
    };
  }
  const comboDefs = [];
  if (bettable.length >= 4) comboDefs.push({ pass_type: "4串1", indexes: [0, 1, 2, 3] });
  for (let a = 0; a < bettable.length - 2; a += 1) {
    for (let b = a + 1; b < bettable.length - 1; b += 1) {
      for (let c = b + 1; c < bettable.length; c += 1) {
        comboDefs.push({ pass_type: "3串1", indexes: [a, b, c] });
      }
    }
  }
  const stakes = comboDefs.length === 5 && Math.round(budget) === 50
    ? [18, 8, 8, 8, 8]
    : comboDefs.map((_, index) => index === 0 ? budget : 0);
  const tickets = comboDefs.map((combo, index) => {
    const selections = combo.indexes.map((rowIndex) => {
      const row = bettable[rowIndex];
      return {
        matchup: matchupName(row.team1, row.team2),
        selection: row.betting_recommendation.selection,
        reference_odds: Number(row.betting_recommendation.reference_odds || 1),
        expected_goals: row.expected_goals,
        predicted_score: row.predicted_score,
      };
    });
    const combinedOdds = selections.reduce((product, item) => product * Number(item.reference_odds || 1), 1);
    const stake = Number(stakes[index] || 0);
    const possiblePayout = Number((stake * combinedOdds).toFixed(2));
    return {
      pass_type: combo.pass_type,
      stake,
      required_hits: combo.indexes.length,
      combined_odds: Number(combinedOdds.toFixed(2)),
      possible_payout: possiblePayout,
      possible_profit: Number((possiblePayout - stake).toFixed(2)),
      selections,
    };
  });
  const totalStake = tickets.reduce((sum, ticket) => sum + Number(ticket.stake || 0), 0);
  const maxPayout = tickets.reduce((sum, ticket) => sum + Number(ticket.possible_payout || 0), 0);
  const maxProfit = maxPayout - totalStake;
  const targetGap = Math.max(10000 - maxProfit, 0);
  return {
    available: true,
    title: "50元冲击万元目标混合过关",
    budget,
    target_profit: 10000,
    tickets,
    total_stake: totalStake,
    max_possible_payout: Number(maxPayout.toFixed(2)),
    max_possible_profit: Number(maxProfit.toFixed(2)),
    target_gap: Number(targetGap.toFixed(2)),
    feasibility: targetGap <= 0 ? "理论奖金达到万元目标" : "当前赔率组合达不到万元目标",
    summary: targetGap <= 0
      ? `若全部过关票命中，理论最高奖金约 ${maxPayout.toFixed(2)} 元，理论盈利约 ${maxProfit.toFixed(2)} 元。`
      : `当前参考赔率下，全部命中理论盈利约 ${maxProfit.toFixed(2)} 元，距离 1 万元目标还差约 ${targetGap.toFixed(2)} 元。`,
    warning: "中国体彩过关投注需要每张票内所有选择同时命中才中奖；本方案只做模型和赔率测算，不保证中奖或盈利。",
  };
}

function renderMixedPassPlan(plan = {}) {
  if (!plan.title) return "";
  if (plan.available === false) {
    return `
      <section class="pass-plan">
        <div class="pass-plan-head">
          <strong>${escapeHtml(plan.title)}</strong>
          <span>预算 50 元</span>
        </div>
        <p>${escapeHtml(plan.summary || "")}</p>
        <p class="bad">${escapeHtml(plan.warning || "")}</p>
      </section>
    `;
  }
  const tickets = plan.tickets || [];
  return `
    <section class="pass-plan">
      <div class="pass-plan-head">
        <strong>${escapeHtml(plan.title || "50元混合过关")}</strong>
        <span>预算 ${Number(plan.total_stake || plan.budget || 0).toFixed(0)} 元 · 目标盈利 ${Number(plan.target_profit || 10000).toFixed(0)} 元</span>
      </div>
      <div class="pass-metrics">
        <div><span>理论最高奖金</span><strong>${Number(plan.max_possible_payout || 0).toFixed(2)} 元</strong></div>
        <div><span>理论最高盈利</span><strong>${Number(plan.max_possible_profit || 0).toFixed(2)} 元</strong></div>
        <div><span>目标缺口</span><strong>${Number(plan.target_gap || 0).toFixed(2)} 元</strong></div>
      </div>
      <p>${escapeHtml(plan.summary || "")}</p>
      <div class="pass-ticket-list">
        ${tickets.map(renderPassTicket).join("")}
      </div>
      <p class="bad">${escapeHtml(plan.warning || "")}</p>
    </section>
  `;
}

function renderPassTicket(ticket = {}) {
  const selections = ticket.selections || [];
  return `
    <div class="pass-ticket">
      <div>
        <strong>${escapeHtml(ticket.pass_type || "")} · ${Number(ticket.stake || 0).toFixed(0)} 元</strong>
        <span>组合赔率 ${Number(ticket.combined_odds || 0).toFixed(2)} · 理论奖金 ${Number(ticket.possible_payout || 0).toFixed(2)} 元 · 需中 ${ticket.required_hits || selections.length} 场</span>
      </div>
      <ul>
        ${selections.map((item) => `
          <li>
            <span>${escapeHtml(localizeTeamText(item.matchup || ""))}</span>
            <strong>${escapeHtml(localizeTeamText(item.selection || ""))}</strong>
            <em>${Number(item.reference_odds || 0).toFixed(2)} · xG ${formatExpectedGoals(item.expected_goals)}</em>
          </li>
        `).join("")}
      </ul>
    </div>
  `;
}

function renderBettingCard(match) {
  const analysis = match.betting_analysis || {};
  const fair = analysis.fair_odds || {};
  const threshold = analysis.value_threshold_odds || {};
  const probs = match.probabilities || {};
  return `
    <div class="betting-card">
      <div>
        <strong>${escapeHtml(matchupName(match.team1, match.team2))}</strong>
        <small>${escapeHtml(formatDateTime(match))} · ${escapeHtml(match.round || "")} · ${escapeHtml(match.status || "")} · 预测 ${escapeHtml(match.predicted_score || "待定")}</small>
      </div>
      ${renderExpectedGoalsStrip(match)}
      <div class="odds-grid">
        ${renderOddsCell(teamName(match.team1), probs.team1_win, fair.team1_win, threshold.team1_win)}
        ${renderOddsCell("平局", probs.draw, fair.draw, threshold.draw)}
        ${renderOddsCell(teamName(match.team2), probs.team2_win, fair.team2_win, threshold.team2_win)}
      </div>
      <p>${escapeHtml(localizeTeamText(analysis.suggestion || ""))}</p>
      ${renderBettingRecommendation(match.betting_recommendation)}
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

function renderBettingRecommendation(recommendation = {}) {
  if (!recommendation.play_type) return "";
  return `
    <div class="bet-slip">
      <span>玩法：${escapeHtml(recommendation.play_type)}</span>
      <span>选择：${escapeHtml(localizeTeamText(recommendation.selection || ""))}</span>
      <span>金额：${Number(recommendation.stake || 0).toFixed(0)} 元</span>
      <span>${escapeHtml(recommendation.odds_type || "参考赔率")}：${Number(recommendation.reference_odds || 0).toFixed(2)}</span>
      <strong>可能奖金：${Number(recommendation.possible_payout || 0).toFixed(2)} 元</strong>
      <em>可能盈利：${Number(recommendation.possible_profit || 0).toFixed(2)} 元</em>
      ${recommendation.risk_note ? `<span>${escapeHtml(recommendation.risk_note)}</span>` : ""}
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
          <small>${escapeHtml(match.predicted_score || "")} · ${escapeHtml(match.confidence_label || "")}</small>
        </div>
      `).join("") || `<div class="empty-line">待定</div>`}
    </section>
  `;
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
        <span class="score">${escapeHtml(actual ? `完赛 ${actual.score}` : match.predicted_score || "待定")}</span>
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
  await loadBettingDaily();
  renderMatches();
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
      <div class="kv"><span>${escapeHtml(t("representativeScore"))}</span><strong>${escapeHtml(match.predicted_score)}</strong></div>
      ${match.actual_score ? `<div class="kv"><span>真实赛果</span><strong>${escapeHtml(match.actual_score.score || "")}</strong></div>` : ""}
      <div class="kv"><span>${escapeHtml(t("modalScore"))}</span><strong>${escapeHtml((match.score_summary || {}).modal_score || match.predicted_score)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("favorite"))}</span><strong>${escapeHtml(teamName(match.favorite))}</strong></div>
      <div class="kv"><span>${escapeHtml(t("confidence"))}</span><strong>${escapeHtml(confidenceText(match.confidence_label))}</strong></div>
      <div class="kv"><span>${escapeHtml(t("expectedGoals"))}</span><strong>${match.expected_goals.team1} : ${match.expected_goals.team2}</strong></div>
      <div class="kv"><span>${escapeHtml(t("expectedTotalGoals"))}</span><strong>${(match.score_summary || {}).expected_total_goals ?? "--"}</strong></div>
      <div class="kv"><span>${escapeHtml(t("over25"))}</span><strong>${percent((match.score_summary || {}).over_2_5)}</strong></div>
      <div class="kv"><span>${escapeHtml(t("bothScore"))}</span><strong>${percent((match.score_summary || {}).both_teams_score)}</strong></div>
    </div>
    ${renderAdvance(match)}
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

function renderAdvance(match) {
  if (!match.advance_probabilities) return "";
  return `
    <h3 class="section-title">${escapeHtml(t("knockoutAdvance"))}</h3>
    <div class="kv-list">
      <div class="kv"><span>${escapeHtml(teamName(match.team1))}</span><strong>${percent(match.advance_probabilities.team1)}</strong></div>
      <div class="kv"><span>${escapeHtml(teamName(match.team2))}</span><strong>${percent(match.advance_probabilities.team2)}</strong></div>
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

window.addEventListener("error", (event) => {
  showNotice(`页面脚本错误：${event.message}`);
});

window.addEventListener("unhandledrejection", (event) => {
  const message = event.reason && event.reason.message ? event.reason.message : String(event.reason || "未知错误");
  showNotice(`页面加载失败：${message}`);
});
