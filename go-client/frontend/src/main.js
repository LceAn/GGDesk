import "./style.css";
import { WindowMinimise, WindowToggleMaximise, Quit } from "../wailsjs/runtime/runtime";
import {
  AddScanResults,
  AnalyzeDuplicates,
  AutoClassify,
  BackupDatabase,
  CreateCategory,
  DeleteCategory,
  DeleteShortcut,
  GenerateShortcutsFromScan,
  GetCategories,
  GetOverview,
  GetSettingsBundle,
  LaunchShortcut,
  ListShortcuts,
  OpenFileLocation,
  PreviewOutputShortcuts,
  RemoveDuplicateShortcuts,
  RenameCategory,
  ResetDatabase,
  ResolveOutputPath,
  SaveOutputPath,
  SaveSettingsBundle,
  ScanPrograms,
  UpdateShortcutCategory,
} from "../wailsjs/go/main/App";

const SETTINGS_VIEWS = [
  ["settings", "快捷页", "C"],
  ["scan", "扫描程序", "S"],
  ["output", "生成路径", "O"],
  ["dedup", "清理去重", "D"],
  ["rules", "扫描规则", "R"],
  ["data", "数据管理", "M"],
  ["about", "关于", "i"],
];

const state = {
  view: "quick",
  shortcuts: [],
  categories: ["全部", "默认"],
  overview: null,
  settings: null,
  scanResults: [],
  outputPreview: [],
  dedupGroups: [],
  selectedCategory: "全部",
  query: "",
  sortBy: "name",
  outputPath: "",
  dedupThreshold: 0.6,
  busy: false,
  toast: "",
  error: "",
};

const app = document.querySelector("#app");
document.documentElement.dataset.theme = "light";

boot();

async function boot() {
  renderShell();
  await refreshAll();
}

function renderShell() {
  app.innerHTML = `
    <header class="titlebar">
      <div class="titlebar-left">
        <button class="titlebar-btn icon-only" data-view="quick" title="返回快捷启动">G</button>
        <span class="titlebar-title">GGDesk</span>
      </div>
      <div class="titlebar-right">
        ${state.view === "quick"
          ? `<button class="titlebar-btn" data-view="settings" title="设置">设置</button>`
          : `<button class="titlebar-btn" data-view="quick" title="返回快捷启动">返回启动页</button>`}
        <span class="titlebar-divider"></span>
        <button class="titlebar-btn win-ctrl" data-window="min">-</button>
        <button class="titlebar-btn win-ctrl" data-window="max">□</button>
        <button class="titlebar-btn win-ctrl close" data-window="close">×</button>
      </div>
    </header>
    <div class="body">
      <main class="main">
        <div id="view"></div>
      </main>
    </div>
    <div id="toast" class="toast"></div>
  `;
  if (!renderShell.bound) {
    app.addEventListener("click", handleClick);
    app.addEventListener("change", handleChange);
    app.addEventListener("input", debounce(handleInput, 180));
    app.addEventListener("dblclick", handleDoubleClick);
    app.addEventListener("keydown", handleKeyDown);
    renderShell.bound = true;
  }
  render();
}

async function refreshAll() {
  state.error = "";
  try {
    await Promise.all([loadOverview(), loadCategories(), loadSettings()]);
    await loadShortcuts();
    state.outputPath ||= state.settings?.settings?.output_path || "";
  } catch (error) {
    state.error = readableError(error);
  }
  render();
}

async function loadOverview() {
  state.overview = await GetOverview();
}

async function loadCategories() {
  state.categories = await GetCategories(true);
  if (!state.categories.includes(state.selectedCategory)) {
    state.selectedCategory = "全部";
  }
}

async function loadSettings() {
  state.settings = await GetSettingsBundle();
  const savedSort = state.settings?.settings?.launcher_sort_by;
  if (["name", "count", "added"].includes(savedSort)) {
    state.sortBy = savedSort;
  }
  const savedTheme = state.settings?.settings?.theme;
  document.documentElement.dataset.theme = savedTheme === "dark" ? "dark" : "light";
}

async function loadShortcuts() {
  state.shortcuts = await ListShortcuts({
    category: state.selectedCategory,
    query: state.query,
    sortBy: state.sortBy,
  });
}

function render() {
  const view = document.querySelector("#view");
  if (!view) return;

  if (state.error) {
    view.innerHTML = errorView(state.error);
  } else if (state.view === "quick") {
    view.innerHTML = quickView();
  } else {
    view.innerHTML = settingsHub();
  }
  renderToast();
}

function settingsHub() {
  return `
    <div class="settings-hub">
      <aside class="settings-nav">
        ${SETTINGS_VIEWS.map(([id, label, icon]) => `
          <button class="settings-tab ${state.view === id ? "active" : ""}" data-settings-view="${id}">
            <span class="settings-tab-icon">${icon}</span>
            <span>${label}</span>
          </button>
        `).join("")}
      </aside>
      <section class="settings-content">
        ${settingsContent()}
      </section>
    </div>
  `;
}

function settingsContent() {
  if (state.view === "scan") return scanView();
  if (state.view === "output") return outputView();
  if (state.view === "dedup") return dedupView();
  if (state.view === "rules") return rulesView();
  if (state.view === "data") return dataView();
  if (state.view === "about") return aboutView();
  return shortcutSettingsView();
}

function header(title, subtitle = "") {
  return `
    <header class="page-header">
      <div>
        <h1>${esc(title)}</h1>
        ${subtitle ? `<p>${esc(subtitle)}</p>` : ""}
      </div>
      <div class="summary">
        <div><strong>${state.overview?.total ?? 0}</strong><span>快捷方式</span></div>
        <div><strong>${Math.max(0, (state.overview?.categories?.length ?? 1) - 1)}</strong><span>分类</span></div>
      </div>
    </header>
  `;
}

function quickView() {
  const visibleCategories = state.categories.slice(0, 12);
  return `
    <section class="launcher-shell">
      <div class="launcher-hero">
        <div class="launcher-searchbox">
          <span class="search-glyph">⌕</span>
          <input id="searchBox" value="${esc(state.query)}" placeholder="输入应用名、分类或路径，按 Enter 启动第一项">
        </div>
        <div class="launcher-filters">
          ${visibleCategories.map((category) => `
            <button class="filter-chip ${category === state.selectedCategory ? "active" : ""}" data-category-filter="${esc(category)}">${esc(category)}</button>
          `).join("")}
          <select id="sortBy" class="launcher-sort" title="排序">
            <option value="name" ${state.sortBy === "name" ? "selected" : ""}>名称</option>
            <option value="count" ${state.sortBy === "count" ? "selected" : ""}>热度</option>
            <option value="added" ${state.sortBy === "added" ? "selected" : ""}>添加时间</option>
          </select>
          <span class="launcher-count">${state.overview?.total ?? 0} 个 · ${state.shortcuts.length} 个结果</span>
        </div>
      </div>
      <div class="launcher-results">
        ${state.shortcuts.map(shortcutRow).join("") || empty("没有匹配的快捷方式")}
      </div>
    </section>
  `;
}

function shortcutRow(item) {
  return `
    <article class="launcher-result" data-id="${item.id}">
      <div class="app-icon-wrap">${appIcon(item.name, item.category)}</div>
      <div class="result-main">
        <h2 title="${esc(item.name)}">${esc(item.name)}</h2>
        <div class="result-path" title="${esc(item.exePath || item.lnkPath)}">${esc(item.exePath || item.lnkPath || "无路径")}</div>
      </div>
      <div class="result-meta">
        <span>${esc(item.category || "默认")}</span>
        <span>${item.runCount || 0} 次</span>
      </div>
      <div class="result-actions">
        <button class="primary" data-action="launch" data-id="${item.id}">启动</button>
        <button class="ghost" data-action="locate" data-id="${item.id}">位置</button>
      </div>
    </article>
  `;
}

function shortcutSettingsView() {
  const categories = state.categories.filter((item) => item !== "全部");
  return `
    ${header("快捷页设置", "管理分类、排序和智能整理；这些维护动作不再占据主界面。")}
    <section class="settings-grid">
      <div class="panel">
        <h2>快捷页行为</h2>
        <div class="stack">
          <label>默认排序
            <select id="settingSort">
              <option value="name" ${state.sortBy === "name" ? "selected" : ""}>名称</option>
              <option value="count" ${state.sortBy === "count" ? "selected" : ""}>热度</option>
              <option value="added" ${state.sortBy === "added" ? "selected" : ""}>添加时间</option>
            </select>
          </label>
          <button class="primary" id="autoClassify">一键智能分类</button>
        </div>
      </div>
      <div class="panel">
        <h2>分类管理</h2>
        <div class="stack">
          <select id="categoryManage">${options(categories, categories[0] || "默认")}</select>
          <input id="categoryName" placeholder="输入分类名称">
          <div class="button-row">
            <button class="primary" id="createCategory">新增</button>
            <button class="ghost" id="renameCategory">重命名</button>
            <button class="danger" id="deleteCategory">删除</button>
          </div>
        </div>
      </div>
    </section>
    <section class="panel">
      <h2>快捷方式分类</h2>
      ${shortcutTable(categories)}
    </section>
  `;
}

function shortcutTable(categories) {
  const rows = state.shortcuts.map((item) => `
    <tr>
      <td>${esc(item.name)}</td>
      <td><select class="row-category" data-id="${item.id}">${options(categories, item.category || "默认")}</select></td>
      <td>${esc(item.sourceType)}</td>
      <td>${item.runCount}</td>
      <td class="path-cell" title="${esc(item.exePath || item.lnkPath)}">${esc(item.exePath || item.lnkPath)}</td>
      <td><button class="danger compact" data-action="delete" data-id="${item.id}">移除</button></td>
    </tr>
  `).join("");
  return table(["名称", "分类", "来源", "次数", "路径", ""], rows || `<tr><td colspan="6">${empty("暂无快捷方式")}</td></tr>`);
}

function scanView() {
  return `
    ${header("扫描程序", "从设置里发起扫描，避免扫描工具抢占启动页关注点。")}
    <section class="panel">
      <div class="scan-controls">
        <label class="search">自定义目录
          <input id="scanPath" value="${esc(state.settings?.settings?.last_scan_path || "")}" placeholder="例如 D:\\Win\\JetBrains">
        </label>
        <label class="checkline"><input id="scanStartMenu" type="checkbox" checked> 开始菜单</label>
        <button class="primary" id="scanButton">${state.busy ? "扫描中..." : "开始扫描"}</button>
        <button class="ghost" id="addScanButton">加入快捷启动</button>
        <button class="ghost" id="generateButton">生成快捷方式</button>
      </div>
      ${scanTable()}
    </section>
  `;
}

function scanTable() {
  const rows = state.scanResults.map((item, index) => `
    <tr>
      <td><input type="checkbox" data-scan-index="${index}" ${item.selected ? "checked" : ""}></td>
      <td>${esc(item.name)}</td>
      <td><span class="pill">${esc(item.category || "默认")}</span></td>
      <td>${esc(item.sourceType)}</td>
      <td>${status(item.status)}</td>
      <td class="path-cell" title="${esc(item.exePath || item.lnkPath)}">${esc(item.exePath || item.lnkPath)}</td>
    </tr>
  `).join("");
  return table(["", "名称", "分类", "来源", "状态", "路径"], rows || `<tr><td colspan="6">${empty("暂无扫描结果")}</td></tr>`);
}

function outputView() {
  return `
    ${header("生成路径", "设置 .lnk 输出目录，并预览当前目录已有快捷方式。")}
    <section class="panel">
      <div class="scan-controls">
        <label class="search">输出目录
          <input id="outputPathInput" value="${esc(state.outputPath)}" placeholder="留空则使用桌面 MyTestShortcuts">
        </label>
        <button class="ghost" id="outputResolve">使用默认路径</button>
        <button class="primary" id="outputSave">保存</button>
        <button class="ghost" id="outputPreviewBtn">刷新预览</button>
      </div>
      ${table(["快捷方式", "目标", "文件"], state.outputPreview.map((item) => `
        <tr><td>${esc(item.name)}</td><td class="path-cell">${esc(item.target)}</td><td class="path-cell">${esc(item.path)}</td></tr>
      `).join("") || `<tr><td colspan="3">${empty("暂无预览")}</td></tr>`)}
    </section>
  `;
}

function dedupView() {
  const rows = state.dedupGroups.map((group) => `
    <tr><th colspan="6">${esc(group.reason)} · ${esc(group.key)}</th></tr>
    ${group.items.map((item) => `
      <tr>
        <td><input class="dedup-del" data-id="${item.id}" type="checkbox" ${item.keep ? "" : "checked"}></td>
        <td>${item.keep ? "保留" : "建议清理"}</td>
        <td>${esc(item.name)}</td>
        <td>${esc(item.sourceType)}</td>
        <td>${item.runCount}</td>
        <td class="path-cell">${esc(item.exePath || item.lnkPath)}</td>
      </tr>
    `).join("")}
  `).join("");
  return `
    ${header("清理去重", "分析重复快捷方式，默认保留得分最高的一项。")}
    <section class="panel">
      <div class="scan-controls">
        <label>相似度阈值
          <input id="dedupThreshold" type="number" min="0.1" max="1" step="0.05" value="${state.dedupThreshold}">
        </label>
        <button class="primary" id="dedupAnalyze">开始分析</button>
        <button class="danger" id="dedupClean">清理勾选项</button>
      </div>
      ${table(["", "建议", "名称", "来源", "次数", "路径"], rows || `<tr><td colspan="6">${empty("尚未分析")}</td></tr>`)}
    </section>
  `;
}

function rulesView() {
  const bundle = state.settings || { rules: {}, lists: {} };
  return `
    ${header("扫描规则", "配置扫描过滤项和规则列表。")}
    <section class="settings-grid">
      ${ruleSwitch("enable_blacklist", "启用黑名单")}
      ${ruleSwitch("enable_ignored_dirs", "忽略目录")}
      ${ruleSwitch("enable_size_filter", "文件大小过滤")}
      ${ruleSwitch("enable_deduplication", "扫描时去重")}
      ${ruleSwitch("enable_bad_path", "排除低质量路径")}
      ${ruleSwitch("enable_smart_root", "智能根目录识别")}
    </section>
    <section class="settings-grid">
      ${listEditor("blocklist", "文件黑名单", bundle.lists?.blocklist)}
      ${listEditor("ignored_dirs", "忽略目录", bundle.lists?.ignored_dirs)}
      ${listEditor("prog_runtimes", "运行时程序", bundle.lists?.prog_runtimes)}
      ${listEditor("bad_path_keywords", "低质量路径关键词", bundle.lists?.bad_path_keywords)}
    </section>
    <button class="primary" id="saveRules">保存规则</button>
  `;
}

function dataView() {
  return `
    ${header("数据管理", "备份、重置和查看当前数据位置。")}
    <section class="panel data-panel">
      <dl>
        <dt>项目目录</dt><dd>${esc(state.settings?.paths?.projectRoot || "")}</dd>
        <dt>数据库</dt><dd>${esc(state.overview?.dbPath || state.settings?.paths?.userDB || "")}</dd>
        <dt>配置文件</dt><dd>${esc(state.settings?.paths?.configFile || "")}</dd>
      </dl>
      <div class="button-row">
        <button class="primary" id="refreshData">刷新数据</button>
        <button class="ghost" id="backupData">备份数据库</button>
        <button class="danger" id="resetData">重置数据库</button>
      </div>
    </section>
  `;
}

function aboutView() {
  return `
    ${header("关于", "GGDesk Go 长期维护版。")}
    <section class="panel">
      <div class="about-hero">
        <div class="about-logo">G</div>
        <div>
          <div class="about-name">GGDesk Go</div>
          <div class="about-tag">以快捷启动为中心的 Windows 工具</div>
        </div>
      </div>
      <div class="about-grid">
        <div class="about-item"><div class="about-key">运行时</div><div class="about-val">Go + Wails</div></div>
        <div class="about-item"><div class="about-key">数据库</div><div class="about-val about-path">${esc(state.overview?.dbPath || "")}</div></div>
      </div>
    </section>
  `;
}

function errorView(message) {
  return `
    ${header("启动失败", "前端已渲染，但后端数据加载失败。")}
    <section class="panel">
      <h2>错误信息</h2>
      <pre class="error-box">${esc(message)}</pre>
      <button class="primary" id="refreshData">重试</button>
    </section>
  `;
}

async function handleClick(event) {
  const windowButton = event.target.closest("[data-window]");
  if (windowButton) {
    if (windowButton.dataset.window === "min") return WindowMinimise();
    if (windowButton.dataset.window === "max") return WindowToggleMaximise();
    if (windowButton.dataset.window === "close") return Quit();
  }

  const mainView = event.target.closest("[data-view]");
  if (mainView) {
    try {
      await setView(mainView.dataset.view);
    } catch (error) {
      showToast(readableError(error));
    }
    return;
  }

  const settingsViewButton = event.target.closest("[data-settings-view]");
  if (settingsViewButton) {
    try {
      await setView(settingsViewButton.dataset.settingsView);
    } catch (error) {
      showToast(readableError(error));
    }
    return;
  }

  const categoryChip = event.target.closest("[data-category-filter]");
  if (categoryChip) {
    state.selectedCategory = categoryChip.dataset.categoryFilter;
    await loadShortcuts();
    render();
    focusSearchEnd();
    return;
  }

  const action = event.target.closest("[data-action]");
  if (action) {
    await runShortcutAction(action.dataset.action, Number(action.dataset.id));
    return;
  }

  const id = event.target.id;
  try {
    if (id === "scanButton") await runScan();
    else if (id === "addScanButton") await addScanResults();
    else if (id === "generateButton") await generateShortcuts();
    else if (id === "createCategory") await createCategory();
    else if (id === "renameCategory") await renameCategory();
    else if (id === "deleteCategory") await deleteCategoryAction();
    else if (id === "autoClassify") await autoClassify();
    else if (id === "outputResolve") await resolveOutput();
    else if (id === "outputSave") await saveOutput();
    else if (id === "outputPreviewBtn") await loadOutputPreview(true);
    else if (id === "dedupAnalyze") await analyzeDuplicates();
    else if (id === "dedupClean") await cleanDuplicates();
    else if (id === "saveRules") await saveRules();
    else if (id === "refreshData") await refreshAll();
    else if (id === "backupData") await backupData();
    else if (id === "resetData") await resetData();
  } catch (error) {
    showToast(readableError(error));
  }
}

async function setView(view) {
  // 切换视图必须立即生效：先切换 state.view 并重绘界面，
  // 再在后台刷新该视图所需的数据。这样即使后端取数报错或卡住，
  // 界面也一定会切过去，绝不会出现"点了没反应"。
  state.view = view || "quick";
  renderShell();

  try {
    if (state.view === "quick") {
      await loadShortcuts();
    } else if (state.view === "output") {
      await loadOutputPreview(false);
    } else if (state.view === "data") {
      await Promise.all([loadOverview(), loadSettings()]);
    }
    state.error = "";
  } catch (error) {
    state.error = readableError(error);
  }
  render();
}

async function handleChange(event) {
  const target = event.target;
  if (target.id === "categoryFilter") {
    state.selectedCategory = target.value;
    await loadShortcuts();
    render();
  } else if (target.id === "sortBy" || target.id === "settingSort") {
    state.sortBy = target.value;
    await persistSetting("launcher_sort_by", target.value);
    await loadShortcuts();
    render();
  } else if (target.dataset.scanIndex !== undefined) {
    state.scanResults[Number(target.dataset.scanIndex)].selected = target.checked;
  } else if (target.id === "dedupThreshold") {
    state.dedupThreshold = Number(target.value) || 0.6;
  } else if (target.classList.contains("row-category")) {
    await UpdateShortcutCategory(Number(target.dataset.id), target.value);
    await refreshAll();
    showToast("分类已更新");
  }
}

async function handleInput(event) {
  if (event.target.id === "searchBox") {
    state.query = event.target.value;
    await loadShortcuts();
    render();
    focusSearchEnd();
  }
}

async function handleDoubleClick(event) {
  const card = event.target.closest(".shortcut-card");
  const result = event.target.closest(".launcher-result");
  if (card) await runShortcutAction("launch", Number(card.dataset.id));
  if (result) await runShortcutAction("launch", Number(result.dataset.id));
}

async function handleKeyDown(event) {
  if (state.view !== "quick") return;
  if (event.key === "Enter" && event.target?.id === "searchBox" && state.shortcuts[0]) {
    event.preventDefault();
    await runShortcutAction("launch", Number(state.shortcuts[0].id));
  }
}

async function runShortcutAction(action, id) {
  if (action === "launch") {
    await LaunchShortcut(id);
    showToast("已启动");
  } else if (action === "locate") {
    await OpenFileLocation(id);
  } else if (action === "delete") {
    await DeleteShortcut(id);
    await refreshAll();
    showToast("已移除");
  }
}

async function runScan() {
  state.busy = true;
  render();
  try {
    state.scanResults = await ScanPrograms({
      customPath: document.querySelector("#scanPath")?.value || "",
      includeStartMenu: document.querySelector("#scanStartMenu")?.checked ?? true,
      includeUWP: false,
      limit: 300,
    });
    showToast(`发现 ${state.scanResults.length} 项`);
  } finally {
    state.busy = false;
    render();
  }
}

async function addScanResults() {
  const count = await AddScanResults(state.scanResults);
  state.scanResults = [];
  await refreshAll();
  showToast(`已加入 ${count} 项`);
}

async function generateShortcuts() {
  const report = await GenerateShortcutsFromScan(state.scanResults, state.outputPath || "", true);
  state.scanResults = [];
  await refreshAll();
  showToast(`已生成 ${report.created} 个，入库 ${report.added} 个`);
}

async function createCategory() {
  const name = document.querySelector("#categoryName")?.value || "";
  await CreateCategory(name);
  await refreshAll();
  showToast("分类已新增");
}

async function renameCategory() {
  const oldName = document.querySelector("#categoryManage")?.value || "";
  const newName = document.querySelector("#categoryName")?.value || "";
  await RenameCategory(oldName, newName);
  await refreshAll();
  showToast("分类已重命名");
}

async function deleteCategoryAction() {
  const name = document.querySelector("#categoryManage")?.value || "";
  if (!confirm(`删除分类“${name}”？其中快捷方式会回到默认分类。`)) return;
  await DeleteCategory(name);
  await refreshAll();
  showToast("分类已删除");
}

async function autoClassify() {
  const count = await AutoClassify();
  await refreshAll();
  showToast(`已更新 ${count} 项`);
}

async function resolveOutput() {
  state.outputPath = await ResolveOutputPath(document.querySelector("#outputPathInput")?.value || "");
  render();
}

async function saveOutput() {
  state.outputPath = document.querySelector("#outputPathInput")?.value || "";
  await SaveOutputPath(state.outputPath);
  await loadSettings();
  showToast("输出路径已保存");
}

async function loadOutputPreview(showMessage) {
  state.outputPreview = await PreviewOutputShortcuts(state.outputPath || state.settings?.settings?.output_path || "");
  if (showMessage) showToast(`预览 ${state.outputPreview.length} 项`);
  render();
}

async function analyzeDuplicates() {
  state.dedupGroups = (await AnalyzeDuplicates(state.dedupThreshold)).groups || [];
  render();
  showToast(`发现 ${state.dedupGroups.length} 组`);
}

async function cleanDuplicates() {
  const ids = [...document.querySelectorAll(".dedup-del:checked")].map((item) => Number(item.dataset.id));
  if (!ids.length) return showToast("请先勾选要清理的项目");
  if (!confirm(`确定清理 ${ids.length} 项？`)) return;
  const count = await RemoveDuplicateShortcuts(ids);
  await refreshAll();
  await analyzeDuplicates();
  showToast(`已清理 ${count} 项`);
}

async function saveRules() {
  const bundle = state.settings || await GetSettingsBundle();
  document.querySelectorAll("[data-rule]").forEach((item) => {
    bundle.rules[item.dataset.rule] = item.checked ? "true" : "false";
  });
  document.querySelectorAll(".list-editor").forEach((item) => {
    bundle.lists[item.dataset.list] = item.value.split("\n").map((value) => value.trim()).filter(Boolean);
  });
  await SaveSettingsBundle(bundle);
  state.settings = bundle;
  showToast("规则已保存");
}

async function backupData() {
  const report = await BackupDatabase();
  showToast(`已备份到 ${report.path}`);
}

async function resetData() {
  if (!confirm("确定重置数据库？建议先备份。")) return;
  if (!confirm("再次确认：此操作会清空快捷方式数据。")) return;
  await ResetDatabase();
  await refreshAll();
  showToast("数据库已重置");
}

async function persistSetting(key, value) {
  const bundle = state.settings || await GetSettingsBundle();
  bundle.settings[key] = value;
  await SaveSettingsBundle(bundle);
  state.settings = bundle;
}

function table(headers, rows) {
  return `
    <div class="table-wrap">
      <table>
        <thead><tr>${headers.map((item) => `<th>${esc(item)}</th>`).join("")}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function ruleSwitch(key, label) {
  const checked = (state.settings?.rules?.[key] ?? "true") === "true";
  return `<div class="panel"><label class="checkline"><input data-rule="${key}" type="checkbox" ${checked ? "checked" : ""}> ${label}</label></div>`;
}

function listEditor(key, label, values = []) {
  return `
    <div class="panel">
      <h2>${esc(label)}</h2>
      <textarea class="list-editor" data-list="${key}" rows="8">${esc((values || []).join("\n"))}</textarea>
    </div>
  `;
}

function appIcon(name, category) {
  return `<div class="app-icon ${toneFor(category)}">${initials(name)}</div>`;
}

function status(value) {
  const cls = value === "新增" ? "new" : "old";
  return `<span class="status ${cls}">${esc(value || "")}</span>`;
}

function options(values, selected) {
  return (values || []).map((value) => `<option ${value === selected ? "selected" : ""}>${esc(value)}</option>`).join("");
}

function empty(text) {
  return `<div class="empty">${esc(text)}</div>`;
}

function initials(name) {
  const clean = String(name || "?").trim();
  const ascii = clean.match(/[A-Za-z0-9]/g);
  return ascii?.length ? ascii.slice(0, 2).join("").toUpperCase() : clean.slice(0, 1);
}

function toneFor(category = "") {
  return {
    "开发": "tone-blue",
    "AI 工具": "tone-violet",
    "设计": "tone-rose",
    "游戏": "tone-green",
    "办公": "tone-yellow",
    "浏览器": "tone-cyan",
    "通讯": "tone-indigo",
    "媒体": "tone-red",
    "系统工具": "tone-slate",
  }[category] || "tone-default";
}

function showToast(message) {
  state.toast = message;
  renderToast();
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    state.toast = "";
    renderToast();
  }, 2600);
}

function renderToast() {
  const toast = document.querySelector("#toast");
  if (!toast) return;
  toast.textContent = state.toast;
  toast.classList.toggle("visible", Boolean(state.toast));
}

function focusSearchEnd() {
  const input = document.querySelector("#searchBox");
  if (!input) return;
  input.focus();
  const end = input.value.length;
  input.setSelectionRange(end, end);
}

function readableError(error) {
  if (!error) return "未知错误";
  return error.message || String(error);
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
