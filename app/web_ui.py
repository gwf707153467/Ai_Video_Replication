def render_studio_page() -> str:
    return r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Videos Replication Studio</title>
  <style>
    :root {
      --ink: #162016;
      --muted: #647060;
      --paper: #f5efe3;
      --card: rgba(255, 252, 245, .9);
      --accent: #c65f2b;
      --accent-2: #264f3d;
      --line: rgba(22, 32, 22, .12);
      --shadow: 0 22px 80px rgba(38, 79, 61, .18);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: ui-serif, Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top left, rgba(198, 95, 43, .24), transparent 36rem),
        radial-gradient(circle at bottom right, rgba(38, 79, 61, .22), transparent 38rem),
        linear-gradient(135deg, #fbf4e7, var(--paper));
      min-height: 100vh;
    }
    header {
      padding: 48px min(6vw, 72px) 24px;
      display: grid;
      grid-template-columns: 1.1fr .9fr;
      gap: 28px;
      align-items: end;
    }
    h1 {
      font-size: clamp(40px, 7vw, 92px);
      line-height: .9;
      margin: 0;
      letter-spacing: -0.06em;
    }
    .lede {
      color: var(--muted);
      font: 18px/1.6 ui-sans-serif, system-ui, sans-serif;
      max-width: 720px;
    }
    main {
      padding: 24px min(6vw, 72px) 72px;
      display: grid;
      grid-template-columns: minmax(320px, 520px) 1fr;
      gap: 28px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 28px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }
    form { padding: 28px; display: grid; gap: 16px; }
    label {
      display: grid;
      gap: 7px;
      font: 700 13px/1.2 ui-sans-serif, system-ui, sans-serif;
      letter-spacing: .04em;
      text-transform: uppercase;
      color: var(--accent-2);
    }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 13px 14px;
      background: rgba(255,255,255,.68);
      color: var(--ink);
      font: 15px/1.45 ui-sans-serif, system-ui, sans-serif;
      outline: none;
    }
    textarea { min-height: 116px; resize: vertical; }
    button {
      border: 0;
      border-radius: 999px;
      padding: 15px 20px;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font: 800 15px/1 ui-sans-serif, system-ui, sans-serif;
      box-shadow: 0 14px 28px rgba(198, 95, 43, .28);
    }
    button:disabled { opacity: .55; cursor: wait; }
    .panel { padding: 24px; min-height: 560px; }
    .toolbar { display:flex; align-items:center; justify-content:space-between; gap: 16px; margin-bottom: 18px; }
    .toolbar h2 { margin:0; font-size: 28px; letter-spacing: -.03em; }
    .ghost { background: transparent; color: var(--accent-2); box-shadow: none; border: 1px solid var(--line); }
    .status {
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 16px;
      margin: 12px 0;
      background: rgba(255,255,255,.55);
      font: 14px/1.5 ui-sans-serif, system-ui, sans-serif;
    }
    .pill { display:inline-flex; border-radius:999px; padding:5px 10px; background:#e9dcc8; color:var(--accent-2); font-weight:800; font-size:12px; }
    .jobs { display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-top: 14px; }
    .job { border: 1px solid var(--line); border-radius: 16px; padding: 12px; background: rgba(255,255,255,.48); }
    .job b { display:block; margin-bottom: 4px; }
    a { color: var(--accent); font-weight: 800; }
    pre { white-space: pre-wrap; background: #172019; color:#f5efe3; padding:16px; border-radius:18px; overflow:auto; }
    @media (max-width: 960px) {
      header, main { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Replication<br/>Studio</h1>
      <p class="lede">最小可用前端：填写商品与文案，触发短视频复刻流水线，实时查看 image / video / voice / merge 状态，并下载最终 MP4。</p>
    </div>
    <div class="lede">当前版本面向本地验证，不是最终 SaaS UI。它直接调用本项目 FastAPI 后端和 Celery 生成链路。</div>
  </header>
  <main>
    <section class="card">
      <form id="generateForm">
        <label>项目名称 <input name="project_name" value="bag-studio-run" required /></label>
        <label>目标市场 <input name="target_market" value="US" /></label>
        <label>语言 <input name="target_language" value="en-US" /></label>
        <label>商品名称 <input name="product_name" value="Premium structured handbag" required /></label>
        <label>参考说明 <textarea name="reference_note">Use the uploaded bag reference video skeleton: product reveal, close-up details, handling, and final lifestyle carry moment.</textarea></label>
        <label>视觉提示词 <textarea name="visual_prompt" required>Create a 9:16 TikTok ecommerce product video segment for a premium structured handbag. Use smooth handheld push-in, zipper and stitching close-ups, clean product handling, boutique lighting, realistic leather texture, no captions, no watermark, no fake logos.</textarea></label>
        <label>口播文案 <textarea name="voice_script" required>This is the everyday bag that makes your outfit look instantly polished. Clean structure, practical space, and premium details for workdays, weekends, and everything in between.</textarea></label>
        <label>负面提示词 <textarea name="negative_prompt">blurry, warped bag shape, fake logos, watermark, captions, text overlay, distorted hands</textarea></label>
        <label>时长毫秒 <input name="duration_ms" type="number" value="6000" min="4000" step="1000" /></label>
        <button id="submitBtn" type="submit">生成复刻视频</button>
      </form>
    </section>
    <section class="card panel">
      <div class="toolbar">
        <h2>运行状态</h2>
        <button class="ghost" id="refreshBtn">刷新最近运行</button>
      </div>
      <div id="result"></div>
    </section>
  </main>
  <script>
    const result = document.querySelector('#result');
    const form = document.querySelector('#generateForm');
    const submitBtn = document.querySelector('#submitBtn');
    const refreshBtn = document.querySelector('#refreshBtn');
    let activeRuntime = null;
    let pollTimer = null;

    function formPayload() {
      const data = new FormData(form);
      return Object.fromEntries([...data.entries()].map(([k, v]) => {
        if (k === 'duration_ms') return [k, Number(v)];
        return [k, String(v).trim()];
      }));
    }

    function statusClass(s) {
      if (s === 'succeeded' || s === 'materialized') return '✅';
      if (s === 'failed') return '❌';
      if (s === 'running' || s === 'dispatched' || s === 'queued') return '⏳';
      return '•';
    }

    function renderRuntime(view) {
      const jobs = view.jobs.map(j => `
        <div class="job">
          <b>${statusClass(j.status)} ${j.job_type}</b>
          <span>${j.status}</span>
          ${j.error_message ? `<small><br/>${j.error_message}</small>` : ''}
        </div>`).join('');
      const assets = view.assets.map(a => `
        <div class="job">
          <b>${statusClass(a.status)} ${a.asset_type}</b>
          <span>${a.status}</span>
          ${a.status === 'materialized' ? `<br/><a href="${a.download_url}" target="_blank">下载</a>` : ''}
        </div>`).join('');
      result.innerHTML = `
        <div class="status">
          <span class="pill">${view.compile_status}</span>
          <span class="pill">${view.runtime_version}</span>
          <p><b>runtime_id:</b> ${view.runtime_id}</p>
          ${view.last_error_message ? `<p><b>error:</b> ${view.last_error_message}</p>` : ''}
          ${view.final_export ? `<p><a href="${view.final_export.download_url}" target="_blank">下载最终 MP4</a></p>` : '<p>最终 MP4 生成后会显示下载链接。</p>'}
        </div>
        <h3>Jobs</h3><div class="jobs">${jobs}</div>
        <h3>Assets</h3><div class="jobs">${assets || '<p>暂无资产。</p>'}</div>`;
    }

    async function pollRuntime(runtimeId) {
      const res = await fetch(`/api/v1/studio/runtimes/${runtimeId}`);
      if (!res.ok) throw new Error(await res.text());
      const view = await res.json();
      renderRuntime(view);
      const stillActive = view.jobs.some(j => ['queued', 'dispatched', 'running'].includes(j.status));
      if (!stillActive && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
        submitBtn.disabled = false;
      }
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      submitBtn.disabled = true;
      result.innerHTML = '<div class="status">正在创建任务...</div>';
      try {
        const res = await fetch('/api/v1/studio/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formPayload())
        });
        if (!res.ok) throw new Error(await res.text());
        const created = await res.json();
        activeRuntime = created.runtime_id;
        await pollRuntime(activeRuntime);
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = setInterval(() => pollRuntime(activeRuntime).catch(console.error), 5000);
      } catch (err) {
        submitBtn.disabled = false;
        result.innerHTML = `<pre>${String(err.stack || err)}</pre>`;
      }
    });

    refreshBtn.addEventListener('click', async () => {
      const res = await fetch('/api/v1/studio/runtimes?limit=5');
      const views = await res.json();
      if (views[0]) {
        activeRuntime = views[0].runtime_id;
        renderRuntime(views[0]);
      } else {
        result.innerHTML = '<div class="status">暂无运行记录。</div>';
      }
    });
  </script>
</body>
</html>"""
