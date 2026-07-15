/* ============================================================
   OpenGTM - 前端交互逻辑
   ============================================================ */

// ==================== 工具函数 ====================

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function showLoading(text = '处理中...') {
  $('#loadingText').textContent = text;
  $('#loadingOverlay').classList.remove('hidden');
}

function hideLoading() {
  $('#loadingOverlay').classList.add('hidden');
}

function toast(msg, type = 'info') {
  const container = $('#toastContainer');
  const icons = { success: 'ri-check-line', error: 'ri-error-warning-line', info: 'ri-information-line' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<i class="${icons[type] || icons.info}"></i><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateX(40px)'; setTimeout(() => el.remove(), 300); }, 4000);
}

async function api(url, data = null) {
  if (window.OpenGTMDemo?.enabled()) {
    return window.OpenGTMDemo.resolve(url, data);
  }
  const opts = data ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) } : {};
  try {
    const resp = await fetch(url, opts);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const json = await resp.json();
    if (json.error) throw new Error(json.error);
    return json;
  } catch (error) {
    if (window.OpenGTMDemo) return window.OpenGTMDemo.resolve(url, data);
    throw error;
  }
}

function disableBtn(btn) { btn.disabled = true; btn.dataset.origText = btn.innerHTML; btn.innerHTML = '<i class="ri-loader-4-line" style="animation:spin 0.8s linear infinite"></i> 处理中...'; }
function enableBtn(btn) { btn.disabled = false; btn.innerHTML = btn.dataset.origText || btn.innerHTML; }

// ==================== 导航 ====================

const pageTitles = {
  dashboard: '工作台', pipeline: '一键流水线', health: 'AEO健康检查', discover: '线索发现',
  research: '公司调研', qualify: 'ICP评分', outreach: '外展管理',
  context: '上下文提取', sync: '企业微信同步'
};

function navigateTo(page) {
  $$('.page').forEach(p => p.classList.remove('active'));
  $$('.nav-item').forEach(n => n.classList.remove('active'));
  const target = $(`#page-${page}`);
  const nav = $(`.nav-item[data-page="${page}"]`);
  if (target) target.classList.add('active');
  if (nav) nav.classList.add('active');
  $('#pageTitle').textContent = pageTitles[page] || page;
  // 进入外展页面时刷新数据
  if (page === 'outreach') refreshOutreach();
}

// 侧边栏导航点击
document.addEventListener('DOMContentLoaded', () => {
  $$('.nav-item').forEach(item => {
    item.addEventListener('click', e => {
      e.preventDefault();
      navigateTo(item.dataset.page);
      // 移动端关闭侧边栏
      $('#sidebar').classList.remove('open');
    });
  });

  // 统计卡片点击跳转
  $$('.stat-card[data-page-link]').forEach(card => {
    card.addEventListener('click', () => navigateTo(card.dataset.pageLink));
  });

  // 侧边栏切换
  $('#sidebarToggle').addEventListener('click', () => {
    $('#sidebar').classList.toggle('open');
  });

  // 初始化
  if (window.OpenGTMDemo?.enabled()) {
    document.body.classList.add('demo-mode');
    seedDemoInputs();
  }
  loadStatus();
  initParticles();
});

function seedDemoInputs() {
  const values = {
    pipeIndustry: 'B2B SaaS', pipeRegion: '上海',
    healthUrl: 'https://example-saas.cn',
    discoverIndustry: 'B2B SaaS', discoverRegion: '上海',
    researchDomain: 'lingyun-data.cn', researchCompany: '凌云数据', researchIndustry: 'B2B SaaS',
    qualifyDomain: 'lingyun-data.cn', qualifyCompany: '凌云数据',
    contextUrl: 'https://lingyun-data.cn',
    syncData: '[{"company":"凌云数据","domain":"lingyun-data.cn","score":86,"tier":"hot"}]'
  };
  Object.entries(values).forEach(([id, value]) => { const el = document.getElementById(id); if (el) el.value = value; });
  const badge = document.createElement('div');
  badge.className = 'demo-ribbon';
  badge.innerHTML = '<i class="ri-database-2-line"></i> GitHub Pages · 演示数据';
  document.querySelector('.topbar-actions')?.prepend(badge);
}

// ==================== 系统状态 ====================

async function loadStatus() {
  try {
    const data = await api('/api/status');
    // 更新模型徽章
    $('#modelBadge span').textContent = data.model || '未配置';

    // 更新系统状态
    const statusEl = $('#systemStatus');
    const dot = statusEl.querySelector('.status-dot');
    const label = statusEl.querySelector('span');
    if (data.static_mode) {
      dot.className = 'status-dot online';
      label.textContent = '演示数据已加载';
    } else if (data.llm_configured) {
      dot.className = 'status-dot online';
      label.textContent = 'LLM已连接';
    } else {
      dot.className = 'status-dot offline';
      label.textContent = 'LLM未配置';
    }

    // 更新配置列表
    const configList = $('#configList');
    configList.innerHTML = `
      <div class="config-item">
        <span class="config-key">LLM API</span>
        <span class="config-val ${data.llm_configured ? 'ok' : 'err'}">${data.llm_configured ? '✓ 已配置' : '✗ 未配置'}</span>
      </div>
      <div class="config-item">
        <span class="config-key">模型</span>
        <span class="config-val">${data.model}</span>
      </div>
      <div class="config-item">
        <span class="config-key">企业微信</span>
        <span class="config-val ${data.wecom_configured ? 'ok' : 'warn'}">${data.wecom_configured ? '✓ 已配置' : '○ 未配置'}</span>
      </div>
      <div class="config-item">
        <span class="config-key">腾讯文档</span>
        <span class="config-val ${data.doc_configured ? 'ok' : 'warn'}">${data.doc_configured ? '✓ 已配置' : '○ 未配置'}</span>
      </div>
      <div class="config-item">
        <span class="config-key">语言</span>
        <span class="config-val">${data.language === 'zh' ? '中文' : data.language}</span>
      </div>
      <div class="config-item">
        <span class="config-key">每日限额</span>
        <span class="config-val">${data.daily_limit} 条/天</span>
      </div>
    `;
  } catch (e) {
    toast('系统状态加载失败: ' + e.message, 'error');
  }
}

// ==================== 粒子动画 ====================

function initParticles() {
  const canvas = document.createElement('canvas');
  const container = $('#heroParticles');
  if (!container) return;
  container.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  let w, h, particles = [];

  function resize() {
    w = canvas.width = container.offsetWidth;
    h = canvas.height = container.offsetHeight;
  }

  function createParticles() {
    particles = [];
    for (let i = 0; i < 40; i++) {
      particles.push({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.5, vy: (Math.random() - 0.5) * 0.5,
        r: Math.random() * 2 + 1, a: Math.random() * 0.3 + 0.1
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(129, 140, 248, ${p.a})`;
      ctx.fill();
    });
    // 连线
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(129, 140, 248, ${0.08 * (1 - dist / 120)})`;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  resize();
  createParticles();
  draw();
  window.addEventListener('resize', () => { resize(); createParticles(); });
}

// ==================== AEO健康检查 ====================

async function runHealthCheck() {
  const url = $('#healthUrl').value.trim();
  if (!url) { toast('请输入网站URL', 'error'); return; }

  const btn = $('#btnHealthCheck');
  disableBtn(btn);
  showLoading('正在运行29项健康检查...');

  try {
    const data = await api('/api/health-check', { url, timeout: parseInt($('#healthTimeout').value) || 30 });
    renderHealthResult(data);
    toast('健康检查完成', 'success');
  } catch (e) {
    toast('健康检查失败: ' + e.message, 'error');
  } finally {
    enableBtn(btn);
    hideLoading();
  }
}

function renderHealthResult(data) {
  const area = $('#healthResult');
  area.classList.remove('hidden');

  const score = data.score || 0;
  const grade = data.grade || 'N/A';
  const band = data.band || '';
  const passed = data.checks_passed || 0;
  const failed = data.checks_failed || 0;
  const total = passed + failed;

  // 颜色映射
  const gradeClass = grade.startsWith('A') ? 'grade-a' : grade.startsWith('B') ? 'grade-b' : grade.startsWith('C') ? 'grade-c' : grade.startsWith('D') ? 'grade-d' : 'grade-f';
  const strokeColor = grade.startsWith('A') ? '#10b981' : grade.startsWith('B') ? '#3b82f6' : grade.startsWith('C') ? '#f59e0b' : '#ef4444';

  const circumference = 2 * Math.PI * 58;
  const offset = circumference - (score / 100) * circumference;

  // Score Hero
  $('#healthScoreHero').innerHTML = `
    <div class="score-circle">
      <svg viewBox="0 0 140 140">
        <circle class="track" cx="70" cy="70" r="58"/>
        <circle class="progress" cx="70" cy="70" r="58"
          stroke="${strokeColor}"
          stroke-dasharray="${circumference}"
          stroke-dashoffset="${offset}"/>
      </svg>
      <div class="score-value">
        <div class="score-number" style="color:${strokeColor}">${score}</div>
        <div class="score-label">/ 100</div>
      </div>
    </div>
    <div class="score-meta">
      <h3>${data.url || ''}</h3>
      <div class="grade-badge ${gradeClass}">
        <i class="ri-award-line"></i> 等级 ${grade}${band ? ' · ' + band : ''}
      </div>
      <div class="score-stats">
        <div class="score-stat-item">
          <span class="val" style="color:var(--success)">${passed}</span>
          <span class="lbl">通过</span>
        </div>
        <div class="score-stat-item">
          <span class="val" style="color:var(--danger)">${failed}</span>
          <span class="lbl">未通过</span>
        </div>
        <div class="score-stat-item">
          <span class="val">${total}</span>
          <span class="lbl">总检查</span>
        </div>
      </div>
    </div>
  `;

  // Tier Details
  const tiers = data.tier_details || {};
  const tierIcons = {
    'technical_seo': 'ri-code-s-slash-line',
    'structured_data': 'ri-database-2-line',
    'ai_crawler': 'ri-robot-line',
    'authority': 'ri-shield-star-line'
  };
  const tierNames = {
    'technical_seo': '技术SEO',
    'structured_data': '结构化数据',
    'ai_crawler': 'AI爬虫访问',
    'authority': '权威信号'
  };

  let tiersHtml = '';
  for (const [key, tier] of Object.entries(tiers)) {
    const tierScore = tier.score || 0;
    const tierMax = tier.max || 0;
    const pct = tierMax > 0 ? Math.round(tierScore / tierMax * 100) : 0;
    const tierColor = pct >= 80 ? 'var(--success)' : pct >= 50 ? 'var(--warning)' : 'var(--danger)';

    let checksHtml = '';
    (tier.checks || []).forEach(c => {
      const icon = c.passed ? 'ri-check-line' : 'ri-close-line';
      const cls = c.passed ? 'pass' : 'fail';
      checksHtml += `<div class="check-item ${cls}"><i class="${icon}"></i><span>${c.name || c.check || ''}</span></div>`;
    });

    tiersHtml += `
      <div class="tier-card">
        <div class="tier-card-header">
          <h4><i class="${tierIcons[key] || 'ri-checkbox-circle-line'}"></i> ${tierNames[key] || key}</h4>
          <span class="tier-score" style="background:${tierColor}20;color:${tierColor}">${tierScore}/${tierMax}</span>
        </div>
        <div class="check-list">${checksHtml || '<div class="empty-state" style="padding:12px"><p>无检查项</p></div>'}</div>
      </div>
    `;
  }

  // 如果没有tier_details，显示issues
  if (!Object.keys(tiers).length && data.issues) {
    tiersHtml = '<div class="tier-card" style="grid-column:1/-1"><div class="tier-card-header"><h4><i class="ri-error-warning-line"></i> 发现的问题</h4></div><div class="check-list">';
    (Array.isArray(data.issues) ? data.issues : []).forEach(issue => {
      tiersHtml += `<div class="check-item fail"><i class="ri-close-line"></i><span>${typeof issue === 'string' ? issue : JSON.stringify(issue)}</span></div>`;
    });
    tiersHtml += '</div></div>';
  }

  $('#healthDetails').innerHTML = tiersHtml;
}

// ==================== 线索发现 ====================

async function runDiscover() {
  const industry = $('#discoverIndustry').value.trim();
  const region = $('#discoverRegion').value.trim();
  const limit = parseInt($('#discoverLimit').value) || 10;

  if (!industry || !region) { toast('请输入行业和地区', 'error'); return; }

  const btn = $('#btnDiscover');
  disableBtn(btn);
  showLoading(`正在搜索${region}的${industry}公司...`);

  try {
    const data = await api('/api/discover', { industry, region, limit });
    renderDiscoverResult(data);
    toast(`发现 ${data.count} 家公司`, 'success');
  } catch (e) {
    toast('线索发现失败: ' + e.message, 'error');
  } finally {
    enableBtn(btn);
    hideLoading();
  }
}

function renderDiscoverResult(data) {
  const area = $('#discoverResult');
  area.classList.remove('hidden');

  if (!data.leads || data.leads.length === 0) {
    area.innerHTML = '<div class="empty-state"><i class="ri-search-line"></i><p>未找到符合条件的公司</p></div>';
    return;
  }

  let rows = '';
  data.leads.forEach((lead, i) => {
    rows += `
      <tr>
        <td>${i + 1}</td>
        <td><strong>${lead.company}</strong></td>
        <td><a href="https://${lead.domain}" target="_blank" class="domain-link">${lead.domain}</a></td>
        <td>${lead.industry || '-'}</td>
        <td>${lead.region || '-'}</td>
        <td>
          <button class="btn btn-sm btn-outline" onclick="quickResearch('${lead.domain}','${lead.company.replace(/'/g, "\\'")}','${(lead.industry || '').replace(/'/g, "\\'")}')">
            <i class="ri-microscope-line"></i> 调研
          </button>
          <button class="btn btn-sm btn-outline" onclick="quickQualify('${lead.domain}','${lead.company.replace(/'/g, "\\'")}','${(lead.industry || '').replace(/'/g, "\\'")}')">
            <i class="ri-bar-chart-grouped-line"></i> 评分
          </button>
        </td>
      </tr>
    `;
  });

  area.innerHTML = `
    <div class="leads-table-wrap">
      <table class="leads-table">
        <thead>
          <tr>
            <th>#</th>
            <th>公司名称</th>
            <th>域名</th>
            <th>行业</th>
            <th>地区</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

// 快捷操作：从发现结果跳转到调研
function quickResearch(domain, company, industry) {
  navigateTo('research');
  $('#researchDomain').value = domain;
  $('#researchCompany').value = company;
  $('#researchIndustry').value = industry;
}

function quickQualify(domain, company, industry) {
  navigateTo('qualify');
  $('#qualifyDomain').value = domain;
  $('#qualifyCompany').value = company;
  // 尝试匹配行业下拉
  const sel = $('#qualifyIndustry');
  for (let opt of sel.options) {
    if (opt.value === industry) { sel.value = industry; break; }
  }
}

// ==================== 公司调研 ====================

async function runResearch() {
  const domain = $('#researchDomain').value.trim();
  if (!domain) { toast('请输入公司域名', 'error'); return; }

  const btn = $('#btnResearch');
  disableBtn(btn);
  showLoading(`正在调研 ${domain}...`);

  try {
    const data = await api('/api/research', {
      domain,
      company: $('#researchCompany').value.trim(),
      industry: $('#researchIndustry').value.trim()
    });
    renderResearchResult(data);
    toast('调研完成', 'success');
  } catch (e) {
    toast('调研失败: ' + e.message, 'error');
  } finally {
    enableBtn(btn);
    hideLoading();
  }
}

function renderResearchResult(data) {
  const area = $('#researchResult');
  area.classList.remove('hidden');

  const contact = data.contact || {};
  const findings = data.findings || [];

  // 联系人卡片
  let contactHtml = `
    <div class="contact-card">
      <h4><i class="ri-user-3-line"></i> 决策者信息</h4>
      <div class="contact-field"><span class="field-label">姓名</span><span class="field-value">${contact.name || '未找到'}</span></div>
      <div class="contact-field"><span class="field-label">职位</span><span class="field-value">${contact.title || '未找到'}</span></div>
      <div class="contact-field"><span class="field-label">邮箱</span><span class="field-value">${contact.email || '未找到'}</span></div>
      <div class="contact-field"><span class="field-label">LinkedIn</span><span class="field-value">${contact.linkedin_url ? `<a href="${contact.linkedin_url}" target="_blank" class="domain-link">${contact.linkedin_url}</a>` : '未找到'}</span></div>
    </div>
  `;

  // 网站概览
  let overviewHtml = `
    <div class="contact-card">
      <h4><i class="ri-global-line"></i> 网站概览</h4>
      <div class="contact-field"><span class="field-label">标题标签</span><span class="field-value">${data.title_tag_text || '未知'}</span></div>
      <div class="contact-field"><span class="field-label">Meta描述</span><span class="field-value">${(data.meta_description_text || '').substring(0, 80) || '未知'}</span></div>
      <div class="contact-field"><span class="field-label">网站语言</span><span class="field-value">${data.site_language || '未知'}</span></div>
      <div class="contact-field"><span class="field-label">博客/新闻</span><span class="field-value">${data.has_blog_or_news ? '✓ 有' : '✗ 无'}</span></div>
      <div class="contact-field"><span class="field-label">社交链接</span><span class="field-value">${data.has_social_links ? '✓ 有' : '✗ 无'}</span></div>
      <div class="contact-field"><span class="field-label">总体评估</span><span class="field-value">${data.overall_assessment || '-'}</span></div>
    </div>
  `;

  // 发现列表
  let findingsHtml = '';
  if (findings.length > 0) {
    findingsHtml = `<div class="findings-card" style="grid-column:1/-1"><h4><i class="ri-error-warning-line"></i> 审计发现 (${findings.length}项)</h4>`;
    findings.forEach(f => {
      findingsHtml += `
        <div class="finding-item">
          <div class="finding-header">
            <span class="severity-badge ${f.severity || 'low'}">${f.severity || 'low'}</span>
            <span class="finding-type">${f.type || 'other'}</span>
          </div>
          <div class="finding-detail">${f.detail || ''}</div>
        </div>
      `;
    });
    findingsHtml += '</div>';
  }

  area.innerHTML = `<div class="research-grid">${contactHtml}${overviewHtml}${findingsHtml}</div>`;
}

// ==================== ICP评分 ====================

async function runQualify() {
  const domain = $('#qualifyDomain').value.trim();
  const company = $('#qualifyCompany').value.trim();
  const industry = $('#qualifyIndustry').value;
  const profile = $('#qualifyProfile').value;

  if (!domain) { toast('请输入域名', 'error'); return; }

  let researchData = {};
  const rawResearch = $('#qualifyResearch').value.trim();
  if (rawResearch) {
    try { researchData = JSON.parse(rawResearch); } catch { toast('调研数据JSON格式错误', 'error'); return; }
  }

  const btn = $('#btnQualify');
  disableBtn(btn);
  showLoading('正在进行ICP评分...');

  try {
    const lead = { domain, company: company || domain, industry, research_data: researchData };
    const data = await api('/api/qualify', { lead, icp_profile: profile });
    renderQualifyResult(data);
    toast(`评分完成: ${data.score}/100`, 'success');
  } catch (e) {
    toast('评分失败: ' + e.message, 'error');
  } finally {
    enableBtn(btn);
    hideLoading();
  }
}

function renderQualifyResult(data) {
  const area = $('#qualifyResult');
  area.classList.remove('hidden');

  const score = data.score || 0;
  const tier = data.tier || 'cold';
  const tierMap = { hot: '🔥 热门', warm: '🌤 温暖', cold: '❄️ 冷淡' };
  const tierClass = `tier-${tier}`;

  const circumference = 2 * Math.PI * 58;
  const offset = circumference - (score / 100) * circumference;
  const strokeColor = tier === 'hot' ? '#ef4444' : tier === 'warm' ? '#f59e0b' : '#3b82f6';

  // 评分明细
  const breakdown = data.breakdown || {};
  const dims = [
    { key: 'industry_fit', label: '行业匹配', max: 25 },
    { key: 'company_size', label: '公司规模', max: 20 },
    { key: 'pain_signals', label: '痛点信号', max: 20 },
    { key: 'digital_maturity', label: '数字化成熟度', max: 15 },
    { key: 'revenue_signals', label: '营收信号', max: 10 },
    { key: 'contact_quality', label: '联系人质量', max: 10 },
  ];

  let barsHtml = '';
  dims.forEach(d => {
    const val = breakdown[d.key] || 0;
    const pct = d.max > 0 ? (val / d.max * 100) : 0;
    barsHtml += `
      <div class="breakdown-bar">
        <span class="bar-label">${d.label}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
        <span class="bar-value">${val}/${d.max}</span>
      </div>
    `;
  });

  // 原因列表
  let reasonsHtml = '';
  (data.reasons || []).forEach(r => {
    reasonsHtml += `<div class="reason-item"><i class="ri-arrow-right-s-fill"></i><span>${r}</span></div>`;
  });

  area.innerHTML = `
    <div class="qualify-result">
      <div class="qualify-score-card">
        <div class="score-circle" style="margin:0 auto">
          <svg viewBox="0 0 140 140">
            <circle class="track" cx="70" cy="70" r="58"/>
            <circle class="progress" cx="70" cy="70" r="58"
              stroke="${strokeColor}"
              stroke-dasharray="${circumference}"
              stroke-dashoffset="${offset}"/>
          </svg>
          <div class="score-value">
            <div class="score-number" style="color:${strokeColor}">${score}</div>
            <div class="score-label">/ 100</div>
          </div>
        </div>
        <div class="tier-badge ${tierClass}">${tierMap[tier] || tier}</div>
        <div style="font-size:14px;font-weight:600;margin-bottom:4px">${data.company || data.domain || ''}</div>
        <div style="font-size:12px;color:var(--text-muted)">${data.domain || ''}</div>
        <div class="qualify-action">
          <strong>推荐操作：</strong><br>${data.recommended_action || '-'}
        </div>
      </div>
      <div class="qualify-details">
        <div class="breakdown-card">
          <h4><i class="ri-pie-chart-line"></i> 评分明细</h4>
          ${barsHtml}
        </div>
        <div class="reasons-card">
          <h4><i class="ri-lightbulb-line"></i> 评分原因</h4>
          ${reasonsHtml || '<div class="reason-item"><i class="ri-information-line"></i><span>暂无详细原因</span></div>'}
        </div>
      </div>
    </div>
  `;
}

// ==================== 外展管理 ====================

async function refreshOutreach() {
  try {
    const [stats, due] = await Promise.all([
      api('/api/outreach/stats'),
      api('/api/outreach/due')
    ]);

    $('#outTotal').textContent = stats.total_leads || 0;
    const sb = stats.status_breakdown || {};
    $('#outPending').textContent = sb.pending || 0;
    $('#outInSeq').textContent = sb.in_sequence || 0;
    $('#outCompleted').textContent = sb.completed || 0;
    $('#outDueToday').textContent = stats.due_today || 0;
    $('#outCapacity').textContent = stats.daily_capacity_remaining || 0;

    const list = $('#outreachDueList');
    if (!due.due || due.due.length === 0) {
      list.innerHTML = '<div class="empty-state"><i class="ri-inbox-line"></i><p>暂无待处理线索</p></div>';
      return;
    }

    const tierMap = { hot: '🔥热门', warm: '🌤温暖', cold: '❄️冷淡' };
    const tierClassMap = { hot: 'tier-hot', warm: 'tier-warm', cold: 'tier-cold' };

    list.innerHTML = due.due.map(item => `
      <div class="due-item">
        <span class="due-tier ${tierClassMap[item.tier] || 'tier-cold'}">${tierMap[item.tier] || item.tier || '-'}</span>
        <div class="due-info">
          <div class="due-company">${item.company || item.domain}</div>
          <div class="due-domain">${item.domain}</div>
        </div>
        <div class="due-touch">触点 #${item.next_touch || '?'}</div>
        <button class="btn btn-sm btn-success" onclick="markSent('${item.domain}', ${item.next_touch || 1})">
          <i class="ri-check-line"></i> 已发送
        </button>
      </div>
    `).join('');
  } catch (e) {
    console.error('刷新外展数据失败:', e);
  }
}

async function markSent(domain, touch) {
  try {
    await api('/api/outreach/send', { domain, touch });
    toast('已标记为已发送', 'success');
    refreshOutreach();
  } catch (e) {
    toast('标记失败: ' + e.message, 'error');
  }
}

// ==================== 上下文提取 ====================

async function runContext() {
  const url = $('#contextUrl').value.trim();
  if (!url) { toast('请输入公司网站URL', 'error'); return; }

  const btn = $('#btnContext');
  disableBtn(btn);
  showLoading('正在提取公司上下文信息...');

  try {
    const data = await api('/api/context', { url });
    renderContextResult(data);
    toast('上下文提取完成', 'success');
  } catch (e) {
    toast('上下文提取失败: ' + e.message, 'error');
  } finally {
    enableBtn(btn);
    hideLoading();
  }
}

function renderContextResult(data) {
  const area = $('#contextResult');
  area.classList.remove('hidden');

  function tagsHtml(arr) {
    if (!arr || arr.length === 0) return '<span style="color:var(--text-muted)">暂无数据</span>';
    return '<div class="tag-list">' + arr.map(t => `<span class="tag">${t}</span>`).join('') + '</div>';
  }

  area.innerHTML = `
    <div class="context-grid">
      <div class="context-card" style="grid-column:1/-1">
        <h4><i class="ri-building-2-line"></i> ${data.company_name || '未知公司'}</h4>
        <div class="context-value">${data.description || '暂无描述'}</div>
        <div style="margin-top:12px;display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--text-secondary)">
          <span><i class="ri-price-tag-3-line"></i> ${data.industry || '未知行业'}</span>
          <span><i class="ri-map-pin-line"></i> ${data.primary_region || '未知地区'}</span>
          <span><i class="ri-translate-2"></i> ${data.primary_language || '-'}</span>
          <span><i class="ri-palette-line"></i> ${data.tone || '-'}</span>
        </div>
      </div>
      <div class="context-card">
        <h4><i class="ri-box-3-line"></i> 产品</h4>
        ${tagsHtml(data.products)}
      </div>
      <div class="context-card">
        <h4><i class="ri-service-line"></i> 服务</h4>
        ${tagsHtml(data.services)}
      </div>
      <div class="context-card">
        <h4><i class="ri-group-line"></i> 目标受众</h4>
        <div class="context-value">${data.target_audience || '暂无数据'}</div>
        ${data.target_audiences && data.target_audiences.length ? '<div style="margin-top:8px">' + tagsHtml(data.target_audiences) + '</div>' : ''}
      </div>
      <div class="context-card">
        <h4><i class="ri-sword-line"></i> 竞争对手</h4>
        ${tagsHtml(data.competitors)}
      </div>
      <div class="context-card">
        <h4><i class="ri-emotion-sad-line"></i> 客户痛点</h4>
        ${tagsHtml(data.pain_points)}
      </div>
      <div class="context-card">
        <h4><i class="ri-star-line"></i> 价值主张</h4>
        ${tagsHtml(data.value_propositions)}
      </div>
      <div class="context-card">
        <h4><i class="ri-lightbulb-line"></i> 用例</h4>
        ${tagsHtml(data.use_cases)}
      </div>
      <div class="context-card">
        <h4><i class="ri-article-line"></i> 内容主题</h4>
        ${tagsHtml(data.content_themes)}
      </div>
    </div>
  `;
}

// ==================== 企业微信同步 ====================

async function runSync() {
  const raw = $('#syncData').value.trim();
  if (!raw) { toast('请输入线索数据', 'error'); return; }

  let leads;
  try { leads = JSON.parse(raw); } catch { toast('JSON格式错误', 'error'); return; }
  if (!Array.isArray(leads)) leads = [leads];

  const dryRun = $('#syncDryRun').checked;
  showLoading(dryRun ? '模拟同步中...' : '正在推送到企业微信...');

  try {
    const data = await api('/api/sync', { leads, dry_run: dryRun });
    const area = $('#syncResult');
    area.classList.remove('hidden');

    area.innerHTML = `
      <div class="card" style="text-align:center;padding:32px">
        <i class="${dryRun ? 'ri-test-tube-line' : 'ri-check-double-line'}" style="font-size:48px;color:${dryRun ? 'var(--warning)' : 'var(--success)'};margin-bottom:12px;display:block"></i>
        <h3 style="margin-bottom:8px">${dryRun ? '模拟运行完成' : '同步完成'}</h3>
        <p style="color:var(--text-secondary);font-size:14px">
          已同步: ${data.synced || 0} 条 · 跳过: ${data.skipped || 0} 条 · 错误: ${(data.errors || []).length} 个
        </p>
        ${data.errors && data.errors.length ? '<div style="margin-top:12px;text-align:left;padding:12px;background:var(--bg-input);border-radius:8px;font-size:12px;color:var(--danger)">' + data.errors.join('<br>') + '</div>' : ''}
      </div>
    `;

    toast(dryRun ? '模拟运行完成' : '同步完成', 'success');
  } catch (e) {
    toast('同步失败: ' + e.message, 'error');
  } finally {
    hideLoading();
  }
}

// ==================== 一键流水线 ====================

async function runPipeline() {
  const industry = $('#pipeIndustry').value.trim();
  const region = $('#pipeRegion').value.trim();
  if (!industry || !region) { toast('请填写行业和地区', 'error'); return; }

  const btn = $('#btnPipeline');
  disableBtn(btn);
  showLoading('流水线运行中（发现→调研→评分→消息），请耐心等待...');

  const area = $('#pipelineResult');
  area.classList.remove('hidden');
  area.innerHTML = `
    <div class="card" style="text-align:center;padding:48px;">
      <div class="spinner-ring" style="margin:0 auto 16px;"></div>
      <h3 style="margin-bottom:8px;">流水线运行中</h3>
      <p style="color:var(--text-secondary);font-size:14px;">发现 → 调研 → 评分 → 消息生成，可能需要数分钟...</p>
    </div>
  `;

  try {
    const data = await api('/api/pipeline', {
      industry,
      region,
      limit: parseInt($('#pipeLimit').value) || 5,
      icp_profile: $('#pipeProfile').value,
      language: $('#pipeLang').value,
    });

    const results = data.results || [];
    const summary = data.summary || {};

    const tierMap = { hot: '🔥 热门', warm: '🌤 温暖', cold: '❄️ 冷淡' };
    const tierClassMap = { hot: 'tier-hot', warm: 'tier-warm', cold: 'tier-cold' };

    // 构建每家公司的详细卡片
    let cardsHtml = results.map((r, i) => {
      const q = r.qualification || {};
      const m = r.messages || {};
      const audit = r.audit || {};
      const contact = audit.contact || {};
      const findings = audit.findings || [];
      const score = q.score || 0;
      const strokeColor = score >= 70 ? 'var(--success)' : score >= 45 ? 'var(--warning)' : 'var(--danger)';

      // 联系人信息
      const contactParts = [];
      if (contact.name) contactParts.push(`<strong>${contact.name}</strong> ${contact.title || ''}`);
      if (contact.email) contactParts.push(`📧 ${contact.email}`);
      if (contact.phone) contactParts.push(`📞 ${contact.phone}`);
      if (contact.wechat) contactParts.push(`💬 微信：${contact.wechat}`);
      if (contact.linkedin_url) contactParts.push(`🔗 <a href="${contact.linkedin_url}" target="_blank" style="color:var(--primary-light);">LinkedIn</a>`);
      const contactHtml = contactParts.length
        ? contactParts.join('<br>')
        : '<span style="color:var(--text-muted);">未找到联系人</span>';

      // 审计发现
      let findingsHtml = '';
      if (findings.length > 0) {
        const sevColors = { high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--text-muted)' };
        findingsHtml = findings.slice(0, 5).map(f =>
          `<div style="display:flex;gap:8px;align-items:flex-start;padding:6px 8px;background:var(--bg-input);border-radius:6px;font-size:12px;">
            <span style="color:${sevColors[f.severity] || 'var(--text-muted)'};font-weight:700;font-size:10px;text-transform:uppercase;flex-shrink:0;margin-top:2px;">${f.severity || ''}</span>
            <span style="color:var(--text-secondary);">${f.detail || ''}</span>
          </div>`
        ).join('');
        if (findings.length > 5) findingsHtml += `<div style="font-size:11px;color:var(--text-muted);padding:4px 8px;">...另外还有${findings.length - 5}项</div>`;
      } else {
        findingsHtml = '<div style="font-size:12px;color:var(--text-muted);padding:4px 8px;">网站状态良好，无明显问题</div>';
      }

      // 消息序列
      let messagesHtml = '';
      if (m.connection_note || m.first_dm) {
        const msgItem = (label, text) => text ? `<div style="margin-bottom:10px;"><div style="font-size:11px;font-weight:600;color:var(--text-muted);margin-bottom:3px;">${label}</div><div style="padding:10px;background:var(--bg-input);border-radius:6px;font-size:12px;line-height:1.6;white-space:pre-wrap;">${text}</div></div>` : '';
        messagesHtml = `
          ${msgItem('🤝 连接请求', m.connection_note)}
          ${msgItem('💬 首次私信', m.first_dm)}
          ${msgItem('📨 跟进消息', m.followup)}
          ${msgItem('📨 再次跟进', m.followup_2)}
        `;
      }

      return `
        <div class="card" style="margin-bottom:16px;padding:0;overflow:hidden;">
          <!-- 摘要行 -->
          <div style="padding:16px 20px;display:flex;align-items:center;gap:16px;cursor:pointer;border-bottom:1px solid var(--border);" onclick="this.parentElement.querySelector('.pipe-detail').classList.toggle('hidden')">
            <span style="font-size:12px;color:var(--text-muted);width:24px;">#${i + 1}</span>
            <div style="flex:1;min-width:0;">
              <div style="font-weight:600;">${r.company || ''} <span style="font-size:12px;color:var(--text-muted);font-weight:400;">${r.domain || ''}</span></div>
              <div style="font-size:12px;color:var(--text-secondary);margin-top:2px;">${contact.name || '联系人未找到'}${contact.phone ? ' · ' + contact.phone : ''}${contact.email ? ' · ' + contact.email : ''}</div>
            </div>
            <span style="font-weight:700;color:${strokeColor};font-size:18px;">${score}</span>
            <span class="tier-badge ${tierClassMap[q.tier] || 'tier-cold'}" style="font-size:11px;padding:3px 10px;">${tierMap[q.tier] || '-'}</span>
            <i class="ri-arrow-down-s-line" style="color:var(--text-muted);font-size:20px;"></i>
          </div>
          <!-- 详情（默认收起） -->
          <div class="pipe-detail hidden" style="padding:16px 20px;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
              <!-- 联系人 -->
              <div>
                <div style="font-size:13px;font-weight:600;margin-bottom:8px;"><i class="ri-user-3-line" style="color:var(--primary-light);"></i> 联系人信息</div>
                <div style="font-size:13px;line-height:1.8;">${contactHtml}</div>
              </div>
              <!-- 审计发现 -->
              <div>
                <div style="font-size:13px;font-weight:600;margin-bottom:8px;"><i class="ri-bug-line" style="color:var(--warning);"></i> 审计发现 (${findings.length}项)</div>
                <div style="display:flex;flex-direction:column;gap:4px;">${findingsHtml}</div>
              </div>
            </div>
            ${messagesHtml ? `
              <div style="margin-top:16px;border-top:1px solid var(--border);padding-top:16px;">
                <div style="font-size:13px;font-weight:600;margin-bottom:10px;"><i class="ri-mail-send-line" style="color:var(--primary-light);"></i> 生成的外展消息 <span style="font-size:11px;font-weight:400;color:var(--text-muted);">模式 ${m.pattern || '-'}: ${m.pattern_reason || ''}</span></div>
                ${messagesHtml}
              </div>
            ` : ''}
            ${q.recommended_action ? `<div style="margin-top:12px;padding:10px 14px;background:var(--primary-bg);border-radius:8px;font-size:13px;"><strong>推荐操作：</strong>${q.recommended_action}</div>` : ''}
          </div>
        </div>
      `;
    }).join('');

    area.innerHTML = `
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;">
        <div class="card mini-stat"><div class="mini-stat-value">${summary.total || 0}</div><div class="mini-stat-label">总计</div></div>
        <div class="card mini-stat"><div class="mini-stat-value" style="color:var(--danger);">${summary.hot || 0}</div><div class="mini-stat-label">🔥 热门</div></div>
        <div class="card mini-stat"><div class="mini-stat-value" style="color:var(--warning);">${summary.warm || 0}</div><div class="mini-stat-label">🌤 温暖</div></div>
        <div class="card mini-stat"><div class="mini-stat-value" style="color:var(--info);">${summary.cold || 0}</div><div class="mini-stat-label">❄️ 冷淡</div></div>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:12px;">💡 点击每行可展开查看调研详情和生成的消息</div>
      ${cardsHtml}
    `;

    toast(`流水线完成：${summary.hot || 0}热门 / ${summary.warm || 0}温暖 / ${summary.cold || 0}冷淡`, 'success');
  } catch (e) {
    area.innerHTML = `
      <div class="card" style="text-align:center;padding:32px;">
        <i class="ri-error-warning-line" style="font-size:48px;color:var(--danger);display:block;margin-bottom:12px;"></i>
        <h3 style="margin-bottom:8px;">流水线执行失败</h3>
        <p style="color:var(--text-secondary);font-size:14px;">${e.message}</p>
      </div>
    `;
    toast('流水线失败: ' + e.message, 'error');
  } finally {
    enableBtn(btn);
    hideLoading();
  }
}
