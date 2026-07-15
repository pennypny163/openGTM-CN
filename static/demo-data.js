/* GitHub Pages static demonstration data. The Flask API remains the default off Pages. */
(function () {
  const leads = [
    { company: '凌云数据', domain: 'lingyun-data.cn', industry: 'B2B SaaS', region: '上海' },
    { company: '智链科技', domain: 'zhilian-ai.cn', industry: '企业服务', region: '深圳' },
    { company: '远帆协同', domain: 'yuanfan-work.cn', industry: '协同办公', region: '杭州' },
    { company: '北辰云服', domain: 'beichen-cloud.cn', industry: '云计算', region: '北京' },
  ];

  const research = {
    company: '凌云数据', domain: 'lingyun-data.cn', title_tag_text: '凌云数据｜企业级数据智能平台',
    meta_description_text: '面向成长型企业的一站式数据分析和经营决策平台。', site_language: 'zh-CN',
    has_blog_or_news: true, has_social_links: true, overall_assessment: '产品成熟、增长信号明显，但 AI 搜索可见性仍有较大提升空间。',
    contact: { name: '陈晓峰', title: '增长负责人', email: 'xiaofeng.chen@lingyun-data.cn', linkedin_url: 'https://linkedin.com/in/demo' },
    findings: [
      { severity: 'high', type: 'AI visibility', detail: '核心产品页缺少 SoftwareApplication 结构化数据，难以被 AI 搜索准确引用。' },
      { severity: 'medium', type: 'SEO', detail: '12 个高价值解决方案页面的 Meta 描述重复。' },
      { severity: 'medium', type: 'Content', detail: '博客更新稳定，但缺少面向 CFO 与数据负责人的场景化内容集群。' },
    ],
  };

  const qualification = {
    company: '凌云数据', domain: 'lingyun-data.cn', score: 86, tier: 'hot',
    recommended_action: '24 小时内联系增长负责人，发送个性化 AEO 审计摘要并预约 20 分钟诊断。',
    breakdown: { industry_fit: 25, company_size: 16, pain_signals: 18, digital_maturity: 12, revenue_signals: 8, contact_quality: 7 },
    reasons: ['B2B SaaS 与目标 ICP 高度匹配', '网站存在明确且可量化的 AI 可见性问题', '内容投入持续，具备采购意愿信号', '已识别增长负责人及有效联系方式'],
  };

  const health = {
    url: 'https://example-saas.cn', score: 72, grade: 'B', band: '良好', checks_passed: 21, checks_failed: 8,
    tier_details: {
      technical_seo: { score: 23, max: 25, checks: [{ name: 'HTTPS 与规范链接', passed: true }, { name: '页面标题唯一', passed: true }, { name: '站点地图可访问', passed: true }] },
      structured_data: { score: 12, max: 25, checks: [{ name: 'Organization Schema', passed: true }, { name: 'SoftwareApplication Schema', passed: false }, { name: 'FAQ Schema', passed: false }] },
      ai_crawler: { score: 19, max: 25, checks: [{ name: 'GPTBot 可访问', passed: true }, { name: 'ClaudeBot 可访问', passed: true }, { name: 'llms.txt', passed: false }] },
      authority: { score: 18, max: 25, checks: [{ name: '作者与更新时间', passed: true }, { name: '客户案例证据', passed: true }, { name: '第三方权威引用', passed: false }] },
    },
  };

  const context = {
    company_name: '凌云数据', description: '为成长型企业提供数据连接、经营分析与 AI 决策能力的一体化 SaaS 平台。',
    industry: '企业级数据智能', primary_region: '中国', primary_language: '中文', tone: '专业、可信、结果导向',
    products: ['经营分析云', 'AI 数据助手', '指标管理平台'], services: ['数据咨询', '实施交付', '客户成功'],
    target_audience: 'CFO、数据负责人、业务运营负责人', target_audiences: ['成长型企业', '连锁零售', '专业服务'],
    competitors: ['观远数据', '神策数据', 'Tableau'], pain_points: ['数据孤岛', '报表交付慢', '经营指标口径不一致'],
    value_propositions: ['两周完成数据接入', '自然语言问数', '统一指标口径'], use_cases: ['经营驾驶舱', '销售预测', '门店分析'],
    content_themes: ['数据驱动增长', 'AI BI', '经营分析方法论'],
  };

  const pipelineResults = [
    { company: '凌云数据', domain: 'lingyun-data.cn', qualification, audit: research, messages: { pattern: 'A', pattern_reason: '发现具体的结构化数据缺口', connection_note: '陈总您好，看到凌云数据在企业数据智能领域的产品体系很完整，想和您交流一个 AI 搜索可见性的发现。', first_dm: '我们检查了贵站的 AI 可见性：核心产品页缺少 SoftwareApplication 结构化数据，导致 ChatGPT 等工具难以准确引用产品能力。我整理了一页修复清单，方便发您看看吗？', followup: '补充一个数据点：同类站点补齐结构化数据后，AI 搜索引用覆盖通常能更快建立。可以免费帮贵站复核一次。' } },
    { company: '智链科技', domain: 'zhilian-ai.cn', qualification: { ...qualification, company: '智链科技', domain: 'zhilian-ai.cn', score: 68, tier: 'warm' }, audit: { ...research, company: '智链科技', domain: 'zhilian-ai.cn', contact: { name: '李然', title: '市场总监', email: 'li.ran@zhilian-ai.cn' } }, messages: { pattern: 'C', pattern_reason: '内容存在但索引信号较弱', connection_note: '李总您好，关注到智链科技近期发布了不少 AI 落地内容。', first_dm: '贵站内容质量不错，但部分文章缺少可被搜索与 AI 引擎识别的索引信号。我整理了三个优先修复点，愿意发您参考。' } },
    { company: '远帆协同', domain: 'yuanfan-work.cn', qualification: { ...qualification, company: '远帆协同', domain: 'yuanfan-work.cn', score: 52, tier: 'warm' }, audit: { ...research, company: '远帆协同', domain: 'yuanfan-work.cn', contact: {} }, messages: { pattern: 'D', pattern_reason: '适合低门槛价值验证', first_dm: '我们做了一个 60 秒 AI 搜索可见性检查，可以看到品牌在 ChatGPT 等渠道中的引用情况。需要我把结果发您吗？' } },
  ];

  const responses = {
    '/api/status': { version: '0.2.0', static_mode: true, llm_configured: true, wecom_configured: true, doc_configured: true, model: 'DeepSeek V3 · 静态演示', language: 'zh', daily_limit: 20 },
    '/api/discover': { leads, count: leads.length }, '/api/research': research, '/api/qualify': qualification,
    '/api/health-check': health, '/api/context': context,
    '/api/outreach/stats': { total_leads: 18, status_breakdown: { pending: 5, in_sequence: 9, completed: 4 }, due_today: 3, daily_capacity_remaining: 17 },
    '/api/outreach/due': { count: 3, due: [{ company: '凌云数据', domain: 'lingyun-data.cn', tier: 'hot', next_touch: 1 }, { company: '智链科技', domain: 'zhilian-ai.cn', tier: 'warm', next_touch: 2 }, { company: '远帆协同', domain: 'yuanfan-work.cn', tier: 'warm', next_touch: 1 }] },
    '/api/outreach/send': { success: true }, '/api/sync': { synced: 1, skipped: 0, errors: [] },
    '/api/pipeline': { results: pipelineResults, summary: { total: 3, hot: 1, warm: 2, cold: 0 } },
  };

  window.OpenGTMDemo = {
    enabled: () => location.hostname.endsWith('github.io') || new URLSearchParams(location.search).has('demo'),
    resolve: async (url) => {
      await new Promise(resolve => setTimeout(resolve, 280));
      const result = responses[url];
      if (!result) throw new Error(`演示模式暂不支持 ${url}`);
      return JSON.parse(JSON.stringify(result));
    },
  };
})();
