def render_studio_page() -> str:
    return r'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Videos Replication Studio</title>
  <style>
    :root {
      --bg: #0d1117;
      --bg-2: #121924;
      --paper: rgba(14, 20, 31, 0.78);
      --paper-strong: rgba(10, 15, 24, 0.92);
      --line: rgba(194, 167, 120, 0.18);
      --line-strong: rgba(194, 167, 120, 0.38);
      --text: #f5efe4;
      --muted: #a7afbe;
      --gold: #d5ae63;
      --gold-2: #f0d7a2;
      --teal: #67d3c0;
      --rose: #f18f78;
      --ok: #7fdb8f;
      --warn: #e8bd72;
      --bad: #f18c7a;
      --shadow: 0 30px 90px rgba(0, 0, 0, 0.38);
      --radius-xl: 30px;
      --radius-lg: 22px;
      --radius-md: 16px;
      --radius-sm: 12px;
      --mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      --sans: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      --serif: Georgia, "Times New Roman", serif;
    }

    * { box-sizing: border-box; }

    html { scroll-behavior: smooth; }

    body {
      margin: 0;
      color: var(--text);
      font-family: var(--sans);
      background:
        radial-gradient(circle at 15% 20%, rgba(103, 211, 192, 0.12), transparent 28rem),
        radial-gradient(circle at 85% 15%, rgba(241, 143, 120, 0.14), transparent 24rem),
        radial-gradient(circle at 55% 80%, rgba(213, 174, 99, 0.14), transparent 32rem),
        linear-gradient(135deg, var(--bg), #090d13 42%, var(--bg-2));
      min-height: 100vh;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255,255,255,0.028) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.028) 1px, transparent 1px);
      background-size: 28px 28px;
      mask-image: radial-gradient(circle at center, black 45%, transparent 100%);
      opacity: 0.45;
    }

    a { color: inherit; }

    .shell {
      width: min(1480px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 22px 0 40px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .brand-mark {
      width: 48px;
      height: 48px;
      border-radius: 15px;
      display: grid;
      place-items: center;
      font: 700 18px/1 var(--serif);
      color: var(--gold-2);
      border: 1px solid var(--line-strong);
      background:
        linear-gradient(145deg, rgba(213, 174, 99, 0.18), rgba(103, 211, 192, 0.08)),
        rgba(255,255,255,0.02);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 18px 35px rgba(0,0,0,0.22);
    }

    .brand-copy h1 {
      margin: 0;
      font: 700 clamp(26px, 4vw, 42px)/0.95 var(--serif);
      letter-spacing: -0.04em;
    }

    .brand-copy p {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .top-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: flex-end;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 10px 14px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }

    .chip strong {
      color: var(--text);
      letter-spacing: normal;
      text-transform: none;
      font-size: 13px;
    }

    .hero {
      position: relative;
      overflow: hidden;
      border-radius: calc(var(--radius-xl) + 8px);
      border: 1px solid var(--line);
      background:
        linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01)),
        linear-gradient(160deg, rgba(213, 174, 99, 0.08), rgba(103, 211, 192, 0.05), rgba(241, 143, 120, 0.05));
      box-shadow: var(--shadow);
      margin-bottom: 20px;
      isolation: isolate;
    }

    .hero::before,
    .hero::after {
      content: "";
      position: absolute;
      border-radius: 999px;
      filter: blur(12px);
      opacity: 0.7;
      pointer-events: none;
    }

    .hero::before {
      width: 26rem;
      height: 26rem;
      background: rgba(213, 174, 99, 0.09);
      right: -8rem;
      top: -10rem;
    }

    .hero::after {
      width: 24rem;
      height: 24rem;
      background: rgba(103, 211, 192, 0.08);
      left: -8rem;
      bottom: -11rem;
    }

    .hero-grid {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 20px;
      padding: 30px;
      align-items: end;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid var(--line-strong);
      background: rgba(7, 11, 17, 0.4);
      color: var(--gold-2);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 16px;
    }

    .hero h2 {
      margin: 0;
      max-width: 11ch;
      font: 700 clamp(42px, 8vw, 88px)/0.9 var(--serif);
      letter-spacing: -0.06em;
    }

    .hero .lede {
      margin: 18px 0 0;
      max-width: 64ch;
      color: #d6dbea;
      font-size: 16px;
      line-height: 1.72;
    }

    .hero-metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 26px;
    }

    .metric {
      padding: 16px 16px 14px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(6, 10, 16, 0.4);
    }

    .metric b {
      display: block;
      font: 700 28px/1 var(--serif);
      color: var(--gold-2);
      margin-bottom: 8px;
    }

    .metric span {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .hero-note {
      display: grid;
      gap: 12px;
      justify-items: stretch;
    }

    .note-card {
      border-radius: 22px;
      padding: 18px;
      border: 1px solid var(--line);
      background: rgba(7, 11, 17, 0.56);
      backdrop-filter: blur(18px);
    }

    .note-card h3,
    .section-head h3,
    .panel-head h3,
    .side-head h3 {
      margin: 0 0 10px;
      font: 700 18px/1.1 var(--serif);
      letter-spacing: -0.02em;
    }

    .note-card p,
    .side-card p,
    .hint,
    .empty,
    .runtime-meta,
    .segment-meta,
    .result-note {
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
      font-size: 14px;
    }

    .page {
      display: grid;
      grid-template-columns: minmax(480px, 720px) minmax(360px, 1fr);
      gap: 20px;
      align-items: start;
    }

    .panel,
    .side-card {
      border-radius: var(--radius-xl);
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(16, 22, 33, 0.9), rgba(9, 14, 22, 0.92));
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .panel {
      position: sticky;
      top: 18px;
    }

    .panel-head,
    .side-head,
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .panel-head {
      padding: 24px 24px 18px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      background: linear-gradient(180deg, rgba(255,255,255,0.03), transparent);
    }

    .panel-head p,
    .side-head p,
    .section-head p {
      margin: 8px 0 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }

    .panel-body {
      padding: 22px 24px 26px;
      display: grid;
      gap: 22px;
    }

    .section {
      display: grid;
      gap: 14px;
      padding-bottom: 4px;
    }

    .section + .section {
      border-top: 1px dashed rgba(255,255,255,0.08);
      padding-top: 20px;
    }

    .grid-2,
    .grid-3 {
      display: grid;
      gap: 14px;
    }

    .grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .grid-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }

    label {
      display: grid;
      gap: 8px;
      color: var(--gold-2);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    input,
    textarea,
    select {
      width: 100%;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px;
      padding: 14px 15px;
      background: rgba(255,255,255,0.04);
      color: var(--text);
      font: 14px/1.5 var(--sans);
      outline: none;
      transition: border-color .2s ease, transform .2s ease, background .2s ease, box-shadow .2s ease;
    }

    input::placeholder,
    textarea::placeholder { color: rgba(213, 219, 234, 0.34); }

    input:focus,
    textarea:focus,
    select:focus {
      border-color: rgba(213, 174, 99, 0.45);
      background: rgba(255,255,255,0.07);
      box-shadow: 0 0 0 4px rgba(213, 174, 99, 0.08);
      transform: translateY(-1px);
    }

    textarea {
      resize: vertical;
      min-height: 108px;
    }

    .field-note {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
      text-transform: none;
      letter-spacing: normal;
    }

    .mode-switch {
      display: inline-grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      padding: 5px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.03);
      gap: 6px;
    }

    .mode-btn {
      border: 0;
      border-radius: 999px;
      padding: 11px 16px;
      color: var(--muted);
      background: transparent;
      font-weight: 700;
      letter-spacing: 0.02em;
      cursor: pointer;
      transition: background .18s ease, color .18s ease, transform .18s ease;
    }

    .mode-btn.active {
      color: #091019;
      background: linear-gradient(135deg, var(--gold-2), var(--gold));
      box-shadow: 0 10px 26px rgba(213, 174, 99, 0.18);
    }

    .mode-btn:hover { transform: translateY(-1px); }

    .hidden { display: none !important; }

    .segment-list {
      display: grid;
      gap: 14px;
    }

    .segment-card {
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
      overflow: hidden;
    }

    .segment-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      background: rgba(255,255,255,0.02);
    }

    .segment-title {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .segment-index {
      width: 34px;
      height: 34px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      background: rgba(213, 174, 99, 0.12);
      color: var(--gold-2);
      font-weight: 800;
      font-family: var(--serif);
    }

    .segment-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .segment-body {
      padding: 16px;
      display: grid;
      gap: 14px;
    }

    .btn,
    button[type="submit"] {
      appearance: none;
      border: 0;
      border-radius: 999px;
      cursor: pointer;
      padding: 14px 18px;
      color: #0d1016;
      background: linear-gradient(135deg, var(--gold-2), var(--gold));
      font: 800 14px/1 var(--sans);
      letter-spacing: 0.02em;
      box-shadow: 0 16px 30px rgba(213, 174, 99, 0.2);
      transition: transform .18s ease, box-shadow .18s ease, opacity .2s ease;
    }

    .btn:hover,
    button[type="submit"]:hover { transform: translateY(-1px); box-shadow: 0 18px 34px rgba(213, 174, 99, 0.24); }
    .btn:disabled,
    button[type="submit"]:disabled { opacity: 0.58; cursor: wait; transform: none; }

    .btn-ghost {
      background: rgba(255,255,255,0.04);
      color: var(--text);
      border: 1px solid rgba(255,255,255,0.08);
      box-shadow: none;
    }

    .btn-danger {
      background: rgba(241, 143, 120, 0.12);
      color: #ffd4c8;
      border: 1px solid rgba(241, 143, 120, 0.24);
      box-shadow: none;
    }

    .btn-small {
      padding: 10px 14px;
      font-size: 12px;
    }

    .actions-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }

    .summary-tile {
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      padding: 14px;
      background: rgba(255,255,255,0.03);
    }

    .summary-tile strong {
      display: block;
      font-size: 20px;
      color: var(--text);
      margin-bottom: 6px;
      font-family: var(--serif);
    }

    .summary-tile span {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .side-stack {
      display: grid;
      gap: 20px;
    }

    .side-card { padding: 22px; }

    .side-head { margin-bottom: 14px; }

    .pill-row,
    .runtime-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .pill,
    .runtime-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      color: #dce2ee;
      font-size: 12px;
    }

    .pill strong,
    .runtime-pill strong { color: var(--gold-2); }

    .status-shell {
      display: grid;
      gap: 18px;
    }

    .runtime-card {
      display: grid;
      gap: 14px;
      padding: 18px;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.08);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02)),
        rgba(8, 13, 20, 0.65);
    }

    .runtime-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }

    .runtime-id {
      color: var(--text);
      font: 700 18px/1.2 var(--serif);
      letter-spacing: -0.02em;
      margin-bottom: 8px;
      word-break: break-all;
    }

    .runtime-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .link-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      padding: 11px 14px;
      border: 1px solid rgba(213, 174, 99, 0.26);
      background: rgba(213, 174, 99, 0.08);
      color: var(--gold-2);
      text-decoration: none;
      font-weight: 700;
      font-size: 13px;
    }

    .progress {
      position: relative;
      height: 12px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.08);
    }

    .progress > span {
      display: block;
      height: 100%;
      width: 0%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--teal), var(--gold));
      transition: width .35s ease;
      box-shadow: 0 0 26px rgba(103, 211, 192, 0.24);
    }

    .runtime-overview-grid,
    .stage-grid,
    .stat-grid,
    .asset-grid,
    .timeline,
    .job-summary-grid {
      display: grid;
      gap: 10px;
    }

    .runtime-overview-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .stage-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .asset-grid { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); }
    .job-summary-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }

    .overview-card,
    .stage-card,
    .mini-card,
    .asset-card,
    .timeline-item,
    .runtime-list-item {
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
    }

    .overview-card,
    .stage-card,
    .mini-card {
      padding: 14px;
      display: grid;
      gap: 8px;
    }

    .overview-card {
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
      min-height: 100%;
    }

    .overview-card span,
    .stage-kicker,
    .mini-card span,
    .asset-card small,
    .runtime-list-item small { color: var(--muted); }

    .overview-card strong,
    .mini-card strong {
      font-size: 15px;
      word-break: break-all;
    }

    .overview-card b,
    .stage-value {
      font: 700 24px/1 var(--serif);
      color: var(--text);
      letter-spacing: -0.03em;
    }

    .overview-card small,
    .stage-copy,
    .progress-meta {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.55;
    }

    .stage-card {
      position: relative;
      overflow: hidden;
      background: linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02));
    }

    .stage-card::before {
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 3px;
      background: rgba(255,255,255,0.12);
    }

    .stage-card.ok::before { background: var(--ok); }
    .stage-card.warn::before { background: var(--warn); }
    .stage-card.bad::before { background: var(--bad); }
    .stage-card.neutral::before { background: var(--gold); }

    .stage-kicker {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 11px;
    }

    .timeline-item {
      padding: 14px;
      display: flex;
      align-items: start;
      gap: 12px;
      transition: border-color .16s ease, background .16s ease, transform .16s ease;
    }

    .job-line {
      display: grid;
      gap: 8px;
    }

    .job-line .runtime-meta {
      padding-left: 2px;
    }

    .timeline-item.is-live {
      border-color: rgba(232, 189, 114, 0.22);
      background: rgba(232, 189, 114, 0.08);
    }

    .timeline-item.is-done {
      border-color: rgba(127, 219, 143, 0.14);
      background: rgba(127, 219, 143, 0.06);
    }

    .timeline-item.is-error {
      border-color: rgba(241, 140, 122, 0.2);
      background: rgba(241, 140, 122, 0.08);
    }

    .timeline-mark {
      width: 36px;
      height: 36px;
      border-radius: 12px;
      display: grid;
      place-items: center;
      font-size: 17px;
      flex: 0 0 auto;
      background: rgba(255,255,255,0.05);
    }

    .timeline-copy b,
    .asset-card b,
    .runtime-list-item b {
      display: block;
      margin-bottom: 4px;
      font-size: 14px;
      color: var(--text);
    }

    .progress-meta,
    .runtime-list-statusline,
    .timeline-topline {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .runtime-list-title {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    .runtime-list-statusline {
      color: var(--muted);
      font-size: 12px;
    }

    .runtime-list-indicator {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.22);
      box-shadow: 0 0 0 4px rgba(255,255,255,0.04);
      flex: 0 0 auto;
    }

    .runtime-list-indicator.ok { background: var(--ok); box-shadow: 0 0 0 4px rgba(127, 219, 143, 0.10); }
    .runtime-list-indicator.warn { background: var(--warn); box-shadow: 0 0 0 4px rgba(232, 189, 114, 0.10); }
    .runtime-list-indicator.bad { background: var(--bad); box-shadow: 0 0 0 4px rgba(241, 140, 122, 0.10); }
    .runtime-list-indicator.neutral { background: var(--gold); box-shadow: 0 0 0 4px rgba(213, 174, 99, 0.10); }

    .timeline-topline small {
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 11px;
    }

    .asset-card {
      padding: 14px;
      display: grid;
      gap: 8px;
      align-content: start;
    }

    .download-link {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--gold-2);
      font-weight: 700;
      text-decoration: none;
      font-size: 13px;
    }

    .runtime-list {
      display: grid;
      gap: 10px;
    }

    .runtime-list-item {
      padding: 14px;
      display: grid;
      gap: 10px;
      cursor: pointer;
      transition: transform .16s ease, border-color .16s ease, background .16s ease;
    }

    .runtime-list-item:hover {
      transform: translateY(-1px);
      border-color: rgba(213, 174, 99, 0.24);
      background: rgba(255,255,255,0.05);
    }

    .runtime-list-item.active {
      border-color: rgba(213, 174, 99, 0.38);
      background: rgba(213, 174, 99, 0.08);
      box-shadow: inset 0 0 0 1px rgba(213, 174, 99, 0.12);
    }

    .runtime-list-meta {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }

    .badge-ok,
    .badge-warn,
    .badge-bad,
    .badge-neutral {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 11px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border: 1px solid transparent;
    }

    .badge-ok { color: var(--ok); background: rgba(127, 219, 143, 0.12); border-color: rgba(127, 219, 143, 0.18); }
    .badge-warn { color: var(--warn); background: rgba(232, 189, 114, 0.12); border-color: rgba(232, 189, 114, 0.18); }
    .badge-bad { color: var(--bad); background: rgba(241, 140, 122, 0.12); border-color: rgba(241, 140, 122, 0.18); }
    .badge-neutral { color: #dce2ee; background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.09); }

    .result-consumption-grid,
    .asset-group-grid {
      display: grid;
      gap: 12px;
    }

    .result-consumption-grid {
      grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
      align-items: start;
    }

    .preview-shell,
    .result-panel,
    .asset-group {
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
      padding: 16px;
    }

    .preview-shell,
    .result-panel {
      display: grid;
      gap: 14px;
      min-height: 100%;
    }

    .preview-head,
    .asset-group-head,
    .result-panel-head {
      display: flex;
      justify-content: space-between;
      align-items: start;
      gap: 10px;
      flex-wrap: wrap;
    }

    .preview-head h3,
    .asset-group-head h4,
    .result-panel-head h3 {
      margin: 0 0 4px;
      color: var(--text);
    }

    .preview-head p,
    .asset-group-head p,
    .result-panel-head p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }

    .preview-frame {
      position: relative;
      border-radius: 20px;
      overflow: hidden;
      border: 1px solid rgba(255,255,255,0.08);
      background:
        radial-gradient(circle at top, rgba(103, 211, 192, 0.10), transparent 46%),
        radial-gradient(circle at bottom, rgba(213, 174, 99, 0.10), transparent 45%),
        #040910;
      min-height: 420px;
      display: grid;
      place-items: center;
    }

    .preview-video {
      width: 100%;
      max-height: 560px;
      aspect-ratio: 9 / 16;
      object-fit: contain;
      background: #040910;
    }

    .preview-image {
      width: 100%;
      max-height: 560px;
      aspect-ratio: 9 / 16;
      object-fit: contain;
      display: block;
      background: #040910;
    }

    .preview-audio-shell {
      width: 100%;
      min-height: 420px;
      display: grid;
      place-items: center;
      padding: 26px;
    }

    .preview-audio-card {
      width: min(100%, 480px);
      display: grid;
      gap: 18px;
      border-radius: 24px;
      border: 1px solid rgba(255,255,255,0.08);
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
      box-shadow: 0 18px 48px rgba(0,0,0,0.28);
      padding: 22px;
    }

    .preview-audio-copy {
      display: grid;
      gap: 8px;
    }

    .preview-audio-copy b {
      color: var(--text);
      font-size: 16px;
    }

    .preview-audio-copy small {
      color: var(--muted);
      line-height: 1.6;
    }

    .preview-audio {
      width: 100%;
      filter: saturate(0.9);
    }

    .preview-empty {
      width: 100%;
      min-height: 420px;
      display: grid;
      place-items: center;
      padding: 26px;
      text-align: center;
      color: var(--muted);
    }

    .preview-empty-inner {
      max-width: 320px;
      display: grid;
      gap: 10px;
    }

    .preview-empty-mark {
      width: 58px;
      height: 58px;
      margin: 0 auto;
      border-radius: 18px;
      display: grid;
      place-items: center;
      font-size: 24px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
    }

    .preview-empty.ok .preview-empty-mark {
      color: var(--ok);
      background: rgba(127, 219, 143, 0.10);
      border-color: rgba(127, 219, 143, 0.18);
    }

    .preview-empty.warn .preview-empty-mark {
      color: var(--warn);
      background: rgba(232, 189, 114, 0.10);
      border-color: rgba(232, 189, 114, 0.18);
    }

    .preview-empty.bad .preview-empty-mark {
      color: var(--bad);
      background: rgba(241, 140, 122, 0.10);
      border-color: rgba(241, 140, 122, 0.18);
    }

    .preview-empty b,
    .result-state-copy b {
      color: var(--text);
      font-size: 15px;
    }

    .result-state {
      display: flex;
      gap: 12px;
      align-items: start;
      border-radius: 16px;
      padding: 14px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
    }

    .result-state-mark {
      width: 40px;
      height: 40px;
      border-radius: 14px;
      display: grid;
      place-items: center;
      flex: 0 0 auto;
      background: rgba(255,255,255,0.05);
      font-size: 18px;
    }

    .result-state-copy {
      display: grid;
      gap: 4px;
    }

    .result-state-copy small,
    .asset-meta,
    .asset-path,
    .runtime-list-copy {
      color: var(--muted);
    }

    .result-state-ok {
      border-color: rgba(127, 219, 143, 0.18);
      background: rgba(127, 219, 143, 0.08);
    }

    .result-state-ok .result-state-mark { color: var(--ok); }

    .result-state-warn {
      border-color: rgba(232, 189, 114, 0.18);
      background: rgba(232, 189, 114, 0.08);
    }

    .result-state-warn .result-state-mark { color: var(--warn); }

    .result-state-bad {
      border-color: rgba(241, 140, 122, 0.18);
      background: rgba(241, 140, 122, 0.08);
    }

    .result-state-bad .result-state-mark { color: var(--bad); }

    .result-state-neutral .result-state-mark { color: var(--gold-2); }

    .export-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .asset-group {
      display: grid;
      gap: 12px;
    }

    .asset-group-head h4 {
      font-size: 15px;
      font-family: var(--serif);
      letter-spacing: -0.01em;
    }

    .asset-card-top {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      align-items: start;
      flex-wrap: wrap;
    }

    .asset-card-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      justify-content: space-between;
    }

    .preview-caption {
      margin-top: -4px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }

    .preview-meta-strip,
    .inspection-grid,
    .inspection-tier-grid,
    .error-cluster-grid {
      display: grid;
      gap: 10px;
    }

    .preview-meta-strip {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .inspection-grid {
      gap: 14px;
    }

    .inspection-tier-grid,
    .error-cluster-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .preview-meta-card,
    .inspection-card,
    .error-cluster-item {
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
      padding: 14px;
    }

    .preview-meta-card {
      display: grid;
      gap: 4px;
    }

    .preview-meta-card span,
    .inspection-card-head small,
    .error-cluster-item small,
    .asset-card-eyebrow,
    .asset-card-hints {
      color: var(--muted);
    }

    .preview-meta-card b,
    .inspection-card-head b,
    .error-cluster-item b {
      color: var(--text);
      font-size: 15px;
    }

    .preview-meta-card small,
    .inspection-card-head small,
    .inspection-item-main small,
    .error-cluster-item small,
    .asset-card-hints {
      line-height: 1.55;
    }

    .inspection-stack {
      display: grid;
      gap: 12px;
    }

    .inspection-section {
      display: grid;
      gap: 12px;
      padding: 16px;
      border-radius: 22px;
      border: 1px solid rgba(255,255,255,0.08);
      background:
        linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.02)),
        radial-gradient(circle at top right, rgba(213, 174, 99, 0.10), transparent 42%);
    }

    .inspection-section .section-head,
    #jobs-timeline .section-head {
      margin-bottom: 0 !important;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
    }

    .inspection-section .section-head p,
    #jobs-timeline .section-head p {
      max-width: 72ch;
    }

    .inspection-tier {
      display: grid;
      gap: 10px;
      padding: 14px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.025);
    }

    .queue-shape {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .inspection-tier-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }

    .inspection-tier-head h4 {
      margin: 0 0 4px;
      color: var(--text);
      font-size: 15px;
    }

    .inspection-tier-head p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }

    .inspection-card {
      display: grid;
      gap: 12px;
    }

    .inspection-card.ok {
      border-color: rgba(127, 219, 143, 0.18);
      background: rgba(127, 219, 143, 0.07);
    }

    .inspection-card.warn {
      border-color: rgba(232, 189, 114, 0.18);
      background: rgba(232, 189, 114, 0.07);
    }

    .inspection-card.neutral {
      border-color: rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
    }

    .inspection-card.bad,
    .error-cluster-item.bad {
      border-color: rgba(241, 140, 122, 0.22);
      background: rgba(241, 140, 122, 0.08);
    }

    .inspection-card.linked-issue {
      box-shadow: inset 0 0 0 1px rgba(241, 140, 122, 0.14);
    }

    .inspection-card-head,
    .inspection-item,
    .error-cluster-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }

    .inspection-item {
      border-radius: 14px;
      padding: 12px;
      border: 1px solid rgba(255,255,255,0.06);
      background: rgba(255,255,255,0.02);
    }

    .inspection-item-main {
      display: grid;
      gap: 4px;
      min-width: 0;
    }

    .inspection-item-main b {
      color: var(--text);
      font-size: 14px;
    }

    .inspection-item-side {
      display: grid;
      gap: 8px;
      justify-items: end;
      text-align: right;
      min-width: 120px;
    }

    .inspection-chip-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }

    .inspection-chip {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    .error-cluster {
      display: grid;
      gap: 12px;
      margin-bottom: 18px;
    }

    .error-cluster-head h3 {
      margin: 0 0 4px;
      color: var(--text);
    }

    .error-cluster-head p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }

    .error-cluster-item {
      display: grid;
      gap: 6px;
    }

    .error-cluster-item.warn {
      border-color: rgba(232, 189, 114, 0.18);
      background: rgba(232, 189, 114, 0.07);
    }

    .asset-card-eyebrow {
      display: block;
      margin-bottom: 6px;
      font-size: 12px;
    }

    .asset-card-hints {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    pre {
      margin: 0;
      border-radius: 18px;
      padding: 16px;
      background: #091018;
      border: 1px solid rgba(255,255,255,0.08);
      color: #f2f5fb;
      overflow: auto;
      font: 12px/1.6 var(--mono);
    }

    .toast {
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      font-size: 14px;
      line-height: 1.6;
    }

    .toast.error {
      border-color: rgba(241, 140, 122, 0.24);
      background: rgba(241, 140, 122, 0.08);
      color: #ffd7ce;
    }

    .preset-grid {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .preset {
      padding: 14px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
      cursor: pointer;
      transition: border-color .16s ease, transform .16s ease, background .16s ease;
    }

    .preset:hover {
      transform: translateY(-1px);
      border-color: rgba(213, 174, 99, 0.28);
      background: rgba(213, 174, 99, 0.06);
    }

    .preset b {
      display: block;
      margin-bottom: 5px;
      font-size: 14px;
    }

    .deerflow-signature {
      position: fixed;
      right: 18px;
      bottom: 18px;
      z-index: 20;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(8, 12, 18, 0.66);
      backdrop-filter: blur(12px);
      color: rgba(245, 239, 228, 0.72);
      text-decoration: none;
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      transition: transform .18s ease, background .18s ease, color .18s ease;
    }

    .deerflow-signature:hover {
      transform: translateY(-1px);
      color: var(--gold-2);
      background: rgba(14, 19, 29, 0.9);
    }

    @media (max-width: 1180px) {
      .hero-grid,
      .page { grid-template-columns: 1fr; }
      .panel { position: static; }
      .preview-meta-strip,
      .inspection-grid,
      .error-cluster-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }

    @media (max-width: 820px) {
      .shell { width: min(100vw - 20px, 1480px); padding-top: 14px; }
      .topbar { flex-direction: column; align-items: stretch; }
      .hero-grid,
      .panel-body,
      .side-card { padding-left: 18px; padding-right: 18px; }
      .panel-head { padding: 20px 18px 16px; }
      .hero { border-radius: 28px; }
      .hero-metrics,
      .summary-grid,
      .preset-grid,
      .grid-2,
      .grid-3,
      .runtime-overview-grid,
      .stage-grid,
      .stat-grid,
      .job-summary-grid,
      .result-consumption-grid,
      .asset-group-grid,
      .preview-meta-strip,
      .inspection-grid,
      .error-cluster-grid { grid-template-columns: 1fr; }
      .runtime-top,
      .segment-top,
      .panel-head,
      .side-head,
      .section-head { flex-direction: column; align-items: stretch; }
      .runtime-actions,
      .actions-row,
      .segment-actions,
      .top-actions { justify-content: flex-start; }
      .hero h2 { max-width: none; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <div class="topbar">
      <div class="brand">
        <div class="brand-mark">AV</div>
        <div class="brand-copy">
          <h1>Replication Studio</h1>
          <p>FastAPI-native console for TikTok ecommerce video regeneration</p>
        </div>
      </div>
      <div class="top-actions">
        <div class="chip">Current surface <strong>/studio</strong></div>
        <div class="chip">Pipeline <strong>image / video / voice / merge</strong></div>
        <div class="chip">Mode <strong>local validation</strong></div>
      </div>
    </div>

    <section class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">30s+ TikTok 带货视频复刻工作台</div>
          <h2>从 reference 到 final MP4 的最小产品化界面</h2>
          <p class="lede">
            当前页面保持后端流水线不变，只把触发、监控、最近运行和最终导出整理成更适合内部交付与演示的 Studio。
            支持 Quick Run 单段输入，也支持 Storyboard 多段输入，便于逐步贴近真实带货视频结构。
          </p>
          <div class="hero-metrics">
            <div class="metric"><b>2</b><span>输入模式：Quick / Storyboard</span></div>
            <div class="metric"><b>5</b><span>Job stages：compile → image → video → voice → merge</span></div>
            <div class="metric"><b>1</b><span>目标交付：downloadable MP4</span></div>
          </div>
        </div>
        <div class="hero-note">
          <div class="note-card">
            <h3>操作边界</h3>
            <p>本轮只升级 `/studio` 页面，不改后端核心编译 / 调度 / worker 写回逻辑。现有 Studio API 保持原样。</p>
          </div>
          <div class="note-card">
            <h3>适用场景</h3>
            <p>内部验证、演示、跑样片、查看 runtime 和资产状态。不是最终多租户 SaaS 控制台，但已经更接近真实产品表面。</p>
          </div>
          <div class="note-card">
            <h3>推荐用法</h3>
            <p>先用 Quick Run 快速压测单条链路；需要更完整销售结构时切到 Storyboard，按 hook / body / close 分段生成。</p>
          </div>
        </div>
      </div>
    </section>

    <div class="page">
      <section class="panel">
        <div class="panel-head">
          <div>
            <h3>Generate Runtime</h3>
            <p>保持现有 API，不改编译器与 worker。你只需要填写素材语义和销售脚本。</p>
          </div>
          <div class="mode-switch" role="tablist" aria-label="输入模式切换">
            <button class="mode-btn active" type="button" id="quickModeBtn">Quick Run</button>
            <button class="mode-btn" type="button" id="storyModeBtn">Storyboard</button>
          </div>
        </div>

        <form id="generateForm" class="panel-body">
          <section class="section">
            <div class="section-head">
              <div>
                <h3>Project Basics</h3>
                <p>最少只需要项目、市场、语言和商品名。参考说明会直接写入 compile options。</p>
              </div>
            </div>
            <div class="grid-2">
              <label>
                项目名称
                <input name="project_name" value="studio-run" required />
              </label>
              <label>
                商品名称
                <input name="product_name" value="Premium structured handbag" required />
              </label>
            </div>
            <div class="grid-3">
              <label>
                目标市场
                <input name="target_market" value="US" />
              </label>
              <label>
                输出语言
                <input name="target_language" value="en-US" />
              </label>
              <label>
                默认时长（ms）
                <input name="duration_ms" type="number" value="6000" min="1000" step="1000" />
              </label>
            </div>
            <label>
              参考说明
              <textarea name="reference_note">Use the reference video skeleton: bold product reveal, tactile detail close-ups, handling demo, and a clean final carry moment. Preserve sales pacing and short-form commerce rhythm.</textarea>
            </label>
          </section>

          <section class="section">
            <div class="section-head">
              <div>
                <h3>Quick Run</h3>
                <p>兼容现有单段 legacy 输入，适合先验证整条链路是否能跑通。</p>
              </div>
            </div>
            <div id="quickModeSection">
              <div class="grid-2">
                <label>
                  视觉提示词
                  <textarea name="visual_prompt" required>Create a 9:16 TikTok ecommerce product video segment for a premium structured handbag. Use handheld reveal, zipper and stitching close-ups, product handling, boutique lighting, realistic material texture, no subtitles, no watermark.</textarea>
                </label>
                <label>
                  口播文案
                  <textarea name="voice_script">This is the everyday bag that makes your outfit look instantly polished. Clean structure, practical space, and premium details for workdays, weekends, and everything in between.</textarea>
                </label>
              </div>
              <label>
                负面提示词
                <textarea name="negative_prompt">blurry, warped bag shape, fake logos, watermark, captions, text overlay, low quality, distorted hands</textarea>
              </label>
              <p class="hint">Quick Run 提交时使用 `visual_prompt / voice_script / negative_prompt / duration_ms` 这一组字段，不带 `segments`。</p>
            </div>
          </section>

          <section class="section hidden" id="storyModeSection">
            <div class="section-head">
              <div>
                <h3>Storyboard</h3>
                <p>多段结构会直接映射到后端 `segments[]`，更适合 hook → proof → CTA 这种带货逻辑。</p>
              </div>
              <button type="button" class="btn btn-ghost btn-small" id="addSegmentBtn">新增一段</button>
            </div>
            <div class="segment-list" id="segmentList"></div>
            <p class="hint">Storyboard 提交时发送 `segments`，后端会走 multi-segment compile。</p>
          </section>

          <section class="section">
            <div class="section-head">
              <div>
                <h3>Useful Presets</h3>
                <p>只是快速填充，不改你的后端能力边界。</p>
              </div>
            </div>
            <div class="preset-grid">
              <button type="button" class="preset" data-preset="handbag">
                <b>Luxury Handbag</b>
                <span>精致材质、拉链细节、通勤使用感</span>
              </button>
              <button type="button" class="preset" data-preset="beauty">
                <b>Beauty Demo</b>
                <span>肤感 close-up、质地展示、前后对比</span>
              </button>
              <button type="button" class="preset" data-preset="accessory">
                <b>Accessory Hook</b>
                <span>快速开场、上手展示、生活方式结尾</span>
              </button>
            </div>
          </section>

          <section class="section">
            <div class="section-head">
              <div>
                <h3>Submission Summary</h3>
                <p>提交前先看当前输入会如何映射到 runtime。</p>
              </div>
            </div>
            <div class="summary-grid">
              <div class="summary-tile"><strong id="summaryMode">Quick Run</strong><span>Current mode</span></div>
              <div class="summary-tile"><strong id="summarySegments">1</strong><span>Segments</span></div>
              <div class="summary-tile"><strong id="summaryDuration">6000 ms</strong><span>Total target duration</span></div>
            </div>
            <div class="actions-row">
              <button id="submitBtn" type="submit">生成复刻视频</button>
              <button type="button" class="btn btn-ghost" id="fillSampleBtn">填充推荐示例</button>
              <button type="button" class="btn btn-ghost" id="resetBtn">重置表单</button>
            </div>
          </section>
        </form>
      </section>

      <aside class="side-stack">
        <section class="side-card">
          <div class="side-head">
            <div>
              <h3>Runtime Monitor</h3>
              <p>查看 compile / dispatch / asset materialization 的最新状态。</p>
            </div>
            <div class="actions-row">
              <button class="btn btn-ghost btn-small" id="refreshBtn" type="button">刷新最近运行</button>
            </div>
          </div>
          <div id="result" class="status-shell">
            <div class="toast">还没有选中 runtime。提交一个新任务，或点击“刷新最近运行”。</div>
          </div>
        </section>

        <section class="side-card">
          <div class="side-head">
            <div>
              <h3>Recent Runtimes</h3>
              <p>显示最近 5 条运行，点击任一条即可切换监控视图。</p>
            </div>
            <div class="pill-row">
              <span class="pill"><strong id="recentCount">0</strong> recent items</span>
            </div>
          </div>
          <div id="runtimeList" class="runtime-list">
            <div class="empty">暂无运行记录。</div>
          </div>
        </section>

        <section class="side-card">
          <div class="side-head">
            <div>
              <h3>Pipeline Notes</h3>
              <p>当前 Studio 的产品定位与边界。</p>
            </div>
          </div>
          <div class="pill-row" style="margin-bottom: 14px;">
            <span class="pill"><strong>FastAPI</strong> mounted UI</span>
            <span class="pill"><strong>Celery</strong> worker chain</span>
            <span class="pill"><strong>MinIO</strong> asset download</span>
          </div>
          <p class="result-note">它不是独立前端工程，而是内嵌的产品化 Studio 页面。优点是部署简单、和现有 API 一致；缺点是交互层仍较轻，但已足够做内部验证与客户演示。</p>
        </section>
      </aside>
    </div>
  </div>

  <a class="deerflow-signature" href="https://deerflow.tech" target="_blank" rel="noreferrer">Created By Deerflow</a>

  <script>
    const form = document.querySelector('#generateForm');
    const result = document.querySelector('#result');
    const submitBtn = document.querySelector('#submitBtn');
    const refreshBtn = document.querySelector('#refreshBtn');
    const resetBtn = document.querySelector('#resetBtn');
    const fillSampleBtn = document.querySelector('#fillSampleBtn');
    const quickModeBtn = document.querySelector('#quickModeBtn');
    const storyModeBtn = document.querySelector('#storyModeBtn');
    const quickModeSection = document.querySelector('#quickModeSection');
    const storyModeSection = document.querySelector('#storyModeSection');
    const segmentList = document.querySelector('#segmentList');
    const addSegmentBtn = document.querySelector('#addSegmentBtn');
    const runtimeList = document.querySelector('#runtimeList');
    const recentCount = document.querySelector('#recentCount');
    const summaryMode = document.querySelector('#summaryMode');
    const summarySegments = document.querySelector('#summarySegments');
    const summaryDuration = document.querySelector('#summaryDuration');

    let mode = 'quick';
    let segmentCounter = 0;
    let activeRuntime = null;
    let pollTimer = null;
    let lastRuntimeViews = [];

    const defaultNegative = 'blurry, warped product shape, fake logos, watermark, captions, text overlay, low quality, distorted hands';

    const presets = {
      handbag: {
        project_name: 'handbag-studio-run',
        product_name: 'Premium structured handbag',
        reference_note: 'Preserve the reference pacing: hook reveal, material detail pass, handling proof, and final carry shot with confident ecommerce rhythm.',
        visual_prompt: 'Create a 9:16 ecommerce video for a premium structured handbag. Start with a bold hook, then zipper and stitching close-ups, hand-held try-on, practical interior glimpse, and a confident final walk-away frame. No subtitles, no watermark.',
        voice_script: 'This is the handbag that makes every outfit feel more intentional. Structured, practical, and polished enough to carry from weekday meetings to weekend dinners.',
        negative_prompt: defaultNegative,
        duration_ms: 6000,
      },
      beauty: {
        project_name: 'beauty-demo-run',
        product_name: 'Glow serum stick',
        reference_note: 'Focus on tactile texture, payoff proof, and a conversion-friendly before/after rhythm.',
        visual_prompt: 'Create a vertical short-form beauty demo. Use macro texture close-ups, one-pass application, skin finish reveal, natural lighting, premium beauty ad pacing, no subtitles or watermark.',
        voice_script: 'One swipe, instant glow. Lightweight texture, clean payoff, and the kind of finish that makes skin look expensive in seconds.',
        negative_prompt: 'blurry skin, extra fingers, warped face, captions, text overlay, watermark, low quality',
        duration_ms: 7000,
      },
      accessory: {
        project_name: 'accessory-hook-run',
        product_name: 'Daily carry accessory',
        reference_note: 'Keep the opening aggressive and short-form. Show problem-solution logic with tactile close-ups.',
        visual_prompt: 'Generate a 9:16 product hook for an everyday accessory. Start with a thumb-stopping reveal, show material details, practical use case, and a simple lifestyle ending. No captions, no fake logos.',
        voice_script: 'If your everyday carry still feels messy, this is the small upgrade that changes everything. Clean design, easy access, and made to move with you.',
        negative_prompt: defaultNegative,
        duration_ms: 5000,
      },
    };

    function escapeHtml(value) {
      return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function statusEmoji(status) {
      if (['succeeded', 'materialized', 'completed'].includes(status)) return '✅';
      if (['failed', 'stale'].includes(status)) return '❌';
      if (['waiting_retry', 'queued', 'dispatched', 'running'].includes(status)) return '⏳';
      return '•';
    }

    function badgeClass(status) {
      if (['succeeded', 'materialized', 'completed'].includes(status)) return 'badge-ok';
      if (['failed', 'stale'].includes(status)) return 'badge-bad';
      if (['queued', 'dispatched', 'running', 'waiting_retry'].includes(status)) return 'badge-warn';
      return 'badge-neutral';
    }

    function statusCopy(status) {
      return String(status || 'unknown').replaceAll('_', ' ');
    }

    function toneFromStatus(status) {
      if (['succeeded', 'materialized', 'completed'].includes(status)) return 'ok';
      if (['failed', 'stale'].includes(status)) return 'bad';
      if (['queued', 'dispatched', 'running', 'waiting_retry', 'pending'].includes(status)) return 'warn';
      return 'neutral';
    }

    function badgeClassForTone(tone) {
      if (tone === 'ok') return 'badge-ok';
      if (tone === 'bad') return 'badge-bad';
      if (tone === 'warn') return 'badge-warn';
      return 'badge-neutral';
    }

    function runtimeHasActiveJobs(view) {
      const jobs = Array.isArray(view?.jobs) ? view.jobs : [];
      return jobs.some(job => ['queued', 'dispatched', 'running', 'waiting_retry'].includes(job.status));
    }

    function runtimeJobSnapshot(view) {
      const jobs = Array.isArray(view?.jobs) ? view.jobs : [];
      const assets = Array.isArray(view?.assets) ? view.assets : [];
      return {
        totalJobs: jobs.length,
        activeJobs: jobs.filter(job => ['queued', 'dispatched', 'running', 'waiting_retry'].includes(job.status)).length,
        doneJobs: jobs.filter(job => ['succeeded', 'completed'].includes(job.status)).length,
        failedJobs: jobs.filter(job => ['failed', 'stale'].includes(job.status)).length,
        materializedAssets: assets.filter(asset => asset.status === 'materialized').length,
        totalAssets: assets.length,
      };
    }

    function segmentTemplate(data = {}) {
      segmentCounter += 1;
      const id = `segment-${segmentCounter}`;
      const sequenceType = data.sequence_type || 'body';
      const durationMs = Number(data.duration_ms || 6000);
      return `
        <article class="segment-card" data-segment-id="${id}">
          <div class="segment-top">
            <div class="segment-title">
              <div class="segment-index"></div>
              <div>
                <strong>Sequence Segment</strong>
                <p class="segment-meta">Hook / body / close 均可，用于组装 Storyboard。</p>
              </div>
            </div>
            <div class="segment-actions">
              <button type="button" class="btn btn-ghost btn-small move-up-btn">上移</button>
              <button type="button" class="btn btn-ghost btn-small move-down-btn">下移</button>
              <button type="button" class="btn btn-danger btn-small remove-segment-btn">删除</button>
            </div>
          </div>
          <div class="segment-body">
            <div class="grid-3">
              <label>
                段落序号
                <input class="segment-sequence-index" type="number" min="1" value="${escapeHtml(data.sequence_index || '')}" placeholder="自动按顺序填充" />
              </label>
              <label>
                段落类型
                <select class="segment-sequence-type">
                  <option value="hook" ${sequenceType === 'hook' ? 'selected' : ''}>hook</option>
                  <option value="body" ${sequenceType === 'body' ? 'selected' : ''}>body</option>
                  <option value="close" ${sequenceType === 'close' ? 'selected' : ''}>close</option>
                  <option value="cta" ${sequenceType === 'cta' ? 'selected' : ''}>cta</option>
                </select>
              </label>
              <label>
                时长（ms）
                <input class="segment-duration-ms" type="number" min="1000" step="1000" value="${escapeHtml(durationMs)}" />
              </label>
            </div>
            <label>
              说服目标
              <input class="segment-persuasive-goal" value="${escapeHtml(data.persuasive_goal || '')}" placeholder="例如：Stop the scroll / Show utility / Final conversion push" />
            </label>
            <label>
              视觉提示词
              <textarea class="segment-visual-prompt" required>${escapeHtml(data.visual_prompt || '')}</textarea>
            </label>
            <div class="grid-2">
              <label>
                口播文案
                <textarea class="segment-voice-script">${escapeHtml(data.voice_script || '')}</textarea>
              </label>
              <label>
                负面提示词
                <textarea class="segment-negative-prompt">${escapeHtml(data.negative_prompt || defaultNegative)}</textarea>
              </label>
            </div>
          </div>
        </article>`;
    }

    function defaultStoryboard() {
      segmentList.innerHTML = [
        segmentTemplate({
          sequence_type: 'hook',
          duration_ms: 5000,
          persuasive_goal: 'Stop the scroll with a premium first reveal.',
          visual_prompt: 'Start with a fast, thumb-stopping reveal of the handbag silhouette. Use confident handheld movement, dramatic lighting, and premium fashion ecommerce pacing.',
          voice_script: 'This is the bag that makes your entire outfit feel more expensive.',
          negative_prompt: defaultNegative,
        }),
        segmentTemplate({
          sequence_type: 'body',
          duration_ms: 7000,
          persuasive_goal: 'Prove texture, structure, and utility.',
          visual_prompt: 'Show zipper, stitching, interior capacity, and clean hand-held carrying shots. Keep the visuals realistic and tactile.',
          voice_script: 'Structured shape, smooth hardware, and enough space for the essentials you actually carry every day.',
          negative_prompt: defaultNegative,
        }),
        segmentTemplate({
          sequence_type: 'close',
          duration_ms: 6000,
          persuasive_goal: 'Land a polished final carry moment and CTA energy.',
          visual_prompt: 'End with an elegant lifestyle carry moment, subtle motion, and a polished final frame that feels premium and conversion-ready.',
          voice_script: 'If you want one bag that works harder without looking basic, this is the one to reach for.',
          negative_prompt: defaultNegative,
        })
      ].join('');
      refreshSegmentIndexes();
      refreshSummary();
    }

    function refreshSegmentIndexes() {
      [...segmentList.querySelectorAll('.segment-card')].forEach((card, index) => {
        const badge = card.querySelector('.segment-index');
        if (badge) badge.textContent = index + 1;
      });
    }

    function setMode(nextMode) {
      mode = nextMode;
      const quick = nextMode === 'quick';
      quickModeBtn.classList.toggle('active', quick);
      storyModeBtn.classList.toggle('active', !quick);
      quickModeSection.classList.toggle('hidden', !quick);
      storyModeSection.classList.toggle('hidden', quick);
      summaryMode.textContent = quick ? 'Quick Run' : 'Storyboard';
      refreshSummary();
    }

    function currentFormData() {
      const data = new FormData(form);
      return Object.fromEntries([...data.entries()].map(([key, value]) => [key, String(value).trim()]));
    }

    function collectSegments() {
      return [...segmentList.querySelectorAll('.segment-card')].map((card, index) => {
        const sequenceIndexRaw = card.querySelector('.segment-sequence-index')?.value?.trim();
        const durationMs = Number(card.querySelector('.segment-duration-ms')?.value || 0);
        return {
          sequence_index: sequenceIndexRaw ? Number(sequenceIndexRaw) : index + 1,
          sequence_type: String(card.querySelector('.segment-sequence-type')?.value || 'body').trim() || 'body',
          persuasive_goal: String(card.querySelector('.segment-persuasive-goal')?.value || '').trim() || undefined,
          visual_prompt: String(card.querySelector('.segment-visual-prompt')?.value || '').trim(),
          voice_script: String(card.querySelector('.segment-voice-script')?.value || '').trim() || undefined,
          negative_prompt: String(card.querySelector('.segment-negative-prompt')?.value || '').trim() || undefined,
          duration_ms: durationMs || 6000,
        };
      }).filter(segment => segment.visual_prompt);
    }

    function payloadForSubmit() {
      const data = currentFormData();
      const payload = {
        project_name: data.project_name,
        target_market: data.target_market || 'US',
        target_language: data.target_language || 'en-US',
        product_name: data.product_name,
        reference_note: data.reference_note || null,
      };

      if (mode === 'story') {
        payload.segments = collectSegments();
      } else {
        payload.visual_prompt = data.visual_prompt || '';
        payload.voice_script = data.voice_script || null;
        payload.negative_prompt = data.negative_prompt || null;
        payload.duration_ms = Number(data.duration_ms || 6000);
      }
      return payload;
    }

    function refreshSummary() {
      if (mode === 'story') {
        const segments = collectSegments();
        summarySegments.textContent = String(segments.length || 0);
        summaryDuration.textContent = `${segments.reduce((sum, item) => sum + Number(item.duration_ms || 0), 0)} ms`;
      } else {
        const data = currentFormData();
        summarySegments.textContent = '1';
        summaryDuration.textContent = `${Number(data.duration_ms || 6000)} ms`;
      }
    }

    function runtimeProgress(view) {
      const jobs = Array.isArray(view.jobs) ? view.jobs : [];
      if (!jobs.length) return 0;
      const finished = jobs.filter(job => ['succeeded', 'failed', 'stale', 'completed'].includes(job.status)).length;
      return Math.max(8, Math.min(100, Math.round((finished / jobs.length) * 100)));
    }

    function formatBytes(value) {
      const size = Number(value || 0);
      if (!Number.isFinite(size) || size <= 0) return 'size unavailable';
      const units = ['B', 'KB', 'MB', 'GB'];
      let current = size;
      let unitIndex = 0;
      while (current >= 1024 && unitIndex < units.length - 1) {
        current /= 1024;
        unitIndex += 1;
      }
      const digits = current >= 100 || unitIndex === 0 ? 0 : 1;
      return `${current.toFixed(digits)} ${units[unitIndex]}`;
    }

    function assetGroupFor(asset) {
      if (asset.asset_type === 'export') return 'merged export';
      if (asset.asset_type === 'audio') return 'voice';
      if (asset.asset_type === 'generated_image') return 'image';
      if (asset.asset_type === 'generated_video') return 'video';
      return 'other';
    }

    function groupedAssets(assets) {
      const groups = {
        'merged export': [],
        video: [],
        voice: [],
        image: [],
        other: [],
      };
      (assets || []).forEach(asset => {
        groups[assetGroupFor(asset)].push(asset);
      });
      return groups;
    }

    function assetInspectionHint(asset) {
      const group = assetGroupFor(asset || {});
      if (group === 'merged export') return asset?.status === 'materialized' ? 'delivery candidate' : 'awaiting export';
      if (group === 'video') return asset?.status === 'materialized' ? 'ready for motion spot-check' : 'waiting for render output';
      if (group === 'voice') return asset?.status === 'materialized' ? 'ready for voice review' : 'waiting for audio render';
      if (group === 'image') return asset?.status === 'materialized' ? 'ready for frame inspection' : 'waiting for image output';
      return asset?.status === 'materialized' ? 'ready for inspection' : 'pending materialization';
    }

    function primaryAssetForInspection(assets) {
      const materialized = (assets || []).filter(asset => asset.status === 'materialized');
      const groups = groupedAssets(materialized);
      const priorities = ['merged export', 'video', 'voice', 'image', 'other'];
      for (const groupName of priorities) {
        const items = groups[groupName] || [];
        const candidate = items.find(asset => asset.download_url) || items[0];
        if (candidate) return candidate;
      }
      return null;
    }

    function previewKindForAsset(asset) {
      const contentType = (asset?.content_type || '').toLowerCase();
      const assetType = (asset?.asset_type || '').toLowerCase();
      if (contentType.startsWith('video/') || ['generated_video', 'export'].includes(assetType)) return 'video';
      if (contentType.startsWith('audio/') || assetType === 'audio') return 'audio';
      if (contentType.startsWith('image/') || assetType === 'generated_image') return 'image';
      return 'file';
    }

    function runtimePreviewSource(view, assets) {
      if (view?.final_export?.download_url) {
        return {
          mode: 'final_export',
          kind: 'video',
          tone: 'ok',
          title: 'Final Export Preview',
          copy: '直接在 Studio 内检查最终 MP4 的节奏、画幅与口播对齐。',
          badge: 'ready to review',
          url: view.final_export.download_url,
          asset: {
            asset_type: 'export',
            asset_role: 'final_export',
            download_url: view.final_export.download_url,
          },
          caption: 'Final merged export · 站内预览用于快速总审，交付请走右侧下载链接。',
          metaValue: 'Final MP4',
          metaCopy: '最终导出已 ready，可直接预览与交付。',
        };
      }
      const asset = primaryAssetForInspection(assets);
      if (!asset?.download_url) return null;
      const group = assetGroupFor(asset);
      const role = asset.asset_role || group;
      const kind = previewKindForAsset(asset);
      const shared = {
        mode: 'intermediate_asset',
        kind,
        tone: 'neutral',
        url: asset.download_url,
        asset,
        caption: `${group} · ${role} · ${assetInspectionHint(asset)}`,
      };
      if (kind === 'video') {
        return {
          ...shared,
          title: 'Intermediate Video Preview',
          copy: 'final export 未完成，先在这里抽检已落盘的视频片段。',
          badge: 'inspection ready',
          metaValue: 'Video Asset',
          metaCopy: '优先核对节奏、构图与镜头衔接。',
        };
      }
      if (kind === 'audio') {
        return {
          ...shared,
          title: 'Voice / Audio Preview',
          copy: '先检查口播与音质，再等待最终合成完成。',
          badge: 'audio ready',
          metaValue: 'Audio Asset',
          metaCopy: '优先核对口播内容、停顿与混音状态。',
        };
      }
      if (kind === 'image') {
        return {
          ...shared,
          title: 'Image / Frame Preview',
          copy: '先检查关键帧与主体一致性，再等待视频链路合成完成。',
          badge: 'frame ready',
          metaValue: 'Image Asset',
          metaCopy: '优先核对主体一致性、文案可读性与画面布局。',
        };
      }
      return {
        ...shared,
        title: 'Inspectable File',
        copy: '该资产可在新标签继续检查。',
        badge: 'open file',
        metaValue: 'Direct File Link',
        metaCopy: '先打开已落盘文件做 spot-check，等待更完整的导出结果。',
      };
    }

    function runtimeFailureCluster(view) {
      const jobs = Array.isArray(view?.jobs) ? view.jobs : [];
      const items = [];
      if (['failed', 'stale'].includes(view?.compile_status)) {
        items.push({
          label: 'Compile',
          tone: 'bad',
          detail: view?.last_error_message || `status ${statusCopy(view?.compile_status)}`,
        });
      }
      if (['failed', 'stale'].includes(view?.dispatch_status)) {
        items.push({
          label: 'Dispatch',
          tone: 'bad',
          detail: `status ${statusCopy(view?.dispatch_status)}`,
        });
      }
      jobs.filter(job => ['failed', 'stale'].includes(job.status)).slice(0, 4).forEach(job => {
        items.push({
          label: `Job · ${job.job_type || 'unknown'}`,
          tone: 'bad',
          detail: job.error_message || `status ${statusCopy(job.status)}`,
        });
      });
      if (view?.last_error_code) {
        items.push({
          label: 'Last Error Code',
          tone: items.length ? 'warn' : 'bad',
          detail: statusCopy(view.last_error_code),
        });
      } else if (view?.last_error_message) {
        items.push({
          label: 'Runtime Error',
          tone: items.length ? 'warn' : 'bad',
          detail: view.last_error_message,
        });
      }
      const deduped = items.filter((item, index, arr) => arr.findIndex(other => other.label == item.label && other.detail == item.detail) === index);
      return {
        hasIssues: deduped.length > 0,
        issueCount: deduped.length,
        headline: deduped.length
          ? `${deduped.length} issue${deduped.length > 1 ? 's' : ''} blocking clean delivery`
          : 'No issues detected',
        items: deduped,
      };
    }

    function runtimeInspectionCards(view, assets) {
      const snapshot = runtimeJobSnapshot({ jobs: view?.jobs, assets });
      const failures = runtimeFailureCluster(view);
      const materializedGroups = groupedAssets((assets || []).filter(asset => asset.status === 'materialized'));
      const cards = [];

      const pushCard = ({ tier, title, copy, reason, tone = 'neutral', count = 0, sampleLabel = '', ctaHref = '', ctaLabel = '', linkedIssue = false, availability = '' }) => {
        cards.push({
          tier,
          title,
          copy,
          reason,
          tone,
          count,
          sampleLabel,
          ctaHref,
          ctaLabel,
          linkedIssue,
          availability,
        });
      };

      const addGroupCard = (groupName, title, copy, reason) => {
        const items = materializedGroups[groupName] || [];
        if (!items.length) return;
        const sample = items.find(asset => asset.download_url) || items[0];
        pushCard({
          tier: 'ready',
          title,
          tone: groupName === 'merged export' ? 'ok' : 'neutral',
          copy,
          reason,
          count: items.length,
          sampleLabel: sample ? `${sample.asset_type}${sample.asset_role ? ` · ${sample.asset_role}` : ''} · ${assetInspectionHint(sample)}` : '',
          ctaHref: sample?.download_url || '',
          ctaLabel: groupName === 'merged export' ? '打开候选导出' : '打开样本',
          linkedIssue: failures.hasIssues,
          availability: failures.hasIssues ? 'inspectable now, but still below the active blocker' : 'inspectable now',
        });
      };

      if (failures.hasIssues) {
        pushCard({
          tier: 'blocked',
          title: 'Blocked by failures',
          tone: 'bad',
          copy: '先处理 Failure Cluster 中的 compile / dispatch / job 异常；它们会压过任何结果抽检。',
          reason: '当前 inspection queue 被失败项抢占，继续看 ready 结果也不能代表可安全交付。',
          count: failures.issueCount,
          sampleLabel: failures.headline,
          ctaHref: '#failure-cluster',
          ctaLabel: '打开 Failure Cluster',
          linkedIssue: true,
          availability: 'blocked until the failure queue is cleared',
        });
      }

      if (view?.final_export?.download_url) {
        pushCard({
          tier: 'ready',
          title: 'Final export',
          tone: 'ok',
          copy: failures.hasIssues
            ? '最终 MP4 已可打开，但当前只适合作为受阻样本；交付前仍建议先清空 Failure Cluster。'
            : '最终 MP4 已 ready，可直接完成站内预览与交付前总审。',
          reason: failures.hasIssues
            ? '文件本身可检查，但交付优先级仍被失败队列压住。'
            : 'final export 已 materialized，是当前最完整的检查入口。',
          count: 1,
          sampleLabel: 'delivery candidate',
          ctaHref: view.final_export.download_url,
          ctaLabel: '打开 final export',
          linkedIssue: failures.hasIssues,
          availability: failures.hasIssues ? 'inspectable file exists, but delivery is still blocked' : 'ready for final review',
        });
      } else {
        addGroupCard('merged export', 'Merged export candidate', '如果这个合并资产已 materialized，可先做交付前抽检。', failures.hasIssues
          ? '已有可抽检导出候选，但仍建议先扫清失败项。'
          : '这是最接近最终交付的中间结果，可优先 spot-check。');
      }
      addGroupCard('video', 'Video intermediates', '先检查产品形态、镜头节奏与转场是否稳定。', failures.hasIssues
        ? '视频资产可看，但当前优先级低于失败排障。'
        : '已有视频结果 materialized，可立即做 motion spot-check。');
      addGroupCard('voice', 'Voice outputs', '抽检口播语速、情绪与内容完整性。', failures.hasIssues
        ? '音频样本已出现，但仍应先确认失败原因不会污染后续结果。'
        : '已有音频输出，可先确认口播与配音链路。');
      addGroupCard('image', 'Image outputs', '快速 spot-check 静帧构图与商品细节。', failures.hasIssues
        ? '静帧可检查，但当前仍属于次级消费入口。'
        : '静帧已落盘，适合先做主体一致性与文案可读性检查。');

      if (snapshot.activeJobs) {
        pushCard({
          tier: 'waiting',
          title: snapshot.materializedAssets ? 'More renders still running' : 'Waiting for first inspectable output',
          tone: 'warn',
          copy: snapshot.materializedAssets
            ? '已有部分结果可看，但 inspection queue 还会继续扩展；先抽检 ready 项，同时等待新资产补齐。'
            : '当前没有可消费文件，不是结果缺失，而是上游仍在产出首批 asset。',
          reason: snapshot.materializedAssets
            ? `${snapshot.activeJobs} 个 active job 仍在推进，说明 ready 队列后面还会继续长出新样本。`
            : '尚未出现任何 materialized 资产，因此这里只能先等待上游把首个文件落盘。',
          count: snapshot.activeJobs,
          sampleLabel: `${snapshot.activeJobs} active job${snapshot.activeJobs > 1 ? 's' : ''}`,
          ctaHref: '#jobs-timeline',
          ctaLabel: '查看 Jobs Timeline',
          availability: snapshot.materializedAssets ? 'partial inventory; upstream still rendering' : 'not inspectable yet; waiting for first materialized file',
        });
      }

      if (!snapshot.materializedAssets && !snapshot.activeJobs && !failures.hasIssues) {
        pushCard({
          tier: 'waiting',
          title: 'Awaiting upstream kickoff',
          tone: 'neutral',
          copy: '当前还没有可检查资产，也没有 active job；通常表示 compile / dispatch 尚未真正产出结果。',
          reason: 'inspection queue 为空是因为上游还没开始 materialize 输出，而不是因为结果被隐藏。',
          count: 0,
          sampleLabel: 'polling will continue',
          ctaHref: '#jobs-timeline',
          ctaLabel: '查看 Jobs Timeline',
          availability: 'waiting for upstream kickoff',
        });
      }

      if (!cards.length) {
        pushCard({
          tier: 'waiting',
          title: 'No consumable outputs yet',
          tone: 'neutral',
          copy: '当前还没有可检查资产。等待 compile / dispatch / render 推进。',
          reason: '一旦出现可下载 asset 或 final export，这里会自动升到 Ready to inspect now。',
          count: 0,
          sampleLabel: 'polling will continue',
          ctaHref: '#jobs-timeline',
          ctaLabel: '查看 Jobs Timeline',
          availability: 'waiting for first inspectable output',
        });
      }
      return cards;
    }

    function runtimeActionHints(view, assets) {
      const snapshot = runtimeJobSnapshot({ jobs: view?.jobs, assets });
      const failures = runtimeFailureCluster(view);
      const hints = [];
      if (view?.final_export?.download_url) {
        hints.push('先站内预览最终 MP4，确认节奏、画幅与口播对齐。');
        hints.push('确认无误后，使用下载链接交付最终文件。');
      }
      if (failures.hasIssues) {
        hints.push('先查看下方 Failure Cluster，定位 compile / dispatch / job 级错误。');
      }
      if (!view?.final_export?.download_url && snapshot.materializedAssets) {
        hints.push('final export 未就绪时，可先检查已 materialized 的 video / voice / image 资产。');
      }
      if (snapshot.activeJobs) {
        hints.push('当前 runtime 仍在轮询，状态卡、预览区与时间线会继续自动刷新。');
      }
      if (!snapshot.materializedAssets && !snapshot.activeJobs && !failures.hasIssues && !view?.final_export?.download_url) {
        hints.push('等待首批资产出现，或切换到最近成功 runtime 查看结果。');
      }
      return hints.slice(0, 4);
    }

    function recentRuntimeCopy(view, assets) {
      const snapshot = runtimeJobSnapshot({ jobs: view?.jobs, assets });
      const failures = runtimeFailureCluster(view);
      if (view?.final_export?.download_url) {
        return `Final export ready · ${snapshot.materializedAssets}/${assets.length} assets ready`;
      }
      if (failures.hasIssues) {
        return `Needs attention · ${failures.issueCount} issue${failures.issueCount > 1 ? 's' : ''} detected`;
      }
      if (snapshot.activeJobs) {
        return `Rendering now · ${snapshot.activeJobs} active job${snapshot.activeJobs > 1 ? 's' : ''}`;
      }
      if (snapshot.materializedAssets) {
        return `Intermediate outputs available · ${snapshot.materializedAssets}/${assets.length} assets ready`;
      }
      return 'Awaiting output · no consumable asset yet';
    }

    function runtimeResultState(view, assets) {
      const finalExport = view.final_export;
      const jobs = Array.isArray(view.jobs) ? view.jobs : [];
      const hasFailure = ['failed', 'stale'].includes(view.compile_status)
        || ['failed', 'stale'].includes(view.dispatch_status)
        || jobs.some(job => ['failed', 'stale'].includes(job.status));
      const hasActive = jobs.some(job => ['queued', 'dispatched', 'running', 'waiting_retry'].includes(job.status));
      const materializedAssets = (assets || []).filter(asset => asset.status === 'materialized');

      if (finalExport?.download_url) {
        return {
          tone: 'ok',
          title: 'Final export ready',
          copy: '最终 MP4 已可站内预览，也可直接下载交付。',
          preview: 'video',
        };
      }
      if (hasFailure) {
        return {
          tone: 'bad',
          title: 'Run needs attention',
          copy: view.last_error_message || '当前 runtime 存在失败或 stale job，请先检查下方时间线与错误信息。',
          preview: 'empty',
        };
      }
      if (hasActive) {
        return {
          tone: 'warn',
          title: 'Pipeline still rendering',
          copy: materializedAssets.length
            ? '已有部分中间资产产出，最终导出仍在处理中。'
            : '任务已提交，正在等待中间资产与最终导出完成。',
          preview: 'empty',
        };
      }
      if (materializedAssets.length) {
        return {
          tone: 'neutral',
          title: 'Intermediate outputs available',
          copy: '当前已有中间资产，但还没有 merged export，可先检查下方分组结果。',
          preview: 'empty',
        };
      }
      return {
        tone: 'neutral',
        title: 'No result yet',
        copy: '这个 runtime 还没有可消费结果。提交新任务或切换到最近成功运行查看预览。',
        preview: 'empty',
      };
    }

    function runtimeActivityState(view, assets) {
      const snapshot = runtimeJobSnapshot({ jobs: view.jobs, assets });
      if (view.final_export?.download_url) return { tone: 'ok', label: 'Ready to review' };
      if (['failed', 'stale'].includes(view.compile_status) || ['failed', 'stale'].includes(view.dispatch_status) || snapshot.failedJobs) {
        return { tone: 'bad', label: 'Needs attention' };
      }
      if (snapshot.activeJobs) return { tone: 'warn', label: 'Rendering now' };
      if (snapshot.materializedAssets) return { tone: 'neutral', label: 'Intermediate outputs' };
      return { tone: 'neutral', label: 'Awaiting output' };
    }

    function runtimeStageSummary(view, assets) {
      const snapshot = runtimeJobSnapshot({ jobs: view.jobs, assets });
      const resultState = runtimeResultState(view, assets);
      const compileTone = toneFromStatus(view.compile_status);
      const dispatchTone = toneFromStatus(view.dispatch_status);
      const compileCopy = compileTone === 'ok'
        ? '输入编译已完成，runtime 结构已经冻结。'
        : compileTone === 'bad'
          ? (view.last_error_code ? `compile error · ${statusCopy(view.last_error_code)}` : '编译阶段失败，需要先处理错误。')
          : compileTone === 'warn'
            ? '正在创建或推进 compile 阶段。'
            : '等待 compile 状态更新。';
      const dispatchCopy = dispatchTone === 'ok'
        ? '下游任务已完成分发或执行收束。'
        : dispatchTone === 'bad'
          ? '任务分发链路存在失败或 stale 状态。'
          : dispatchTone === 'warn'
            ? 'worker 任务仍在排队、分发或重试中。'
            : '尚未看到明确的 dispatch 进展。';

      let renderTone = 'neutral';
      let renderValue = snapshot.totalJobs ? `${snapshot.doneJobs}/${snapshot.totalJobs}` : 'No jobs';
      let renderCopy = '还没有足够的渲染信号。';
      if (snapshot.failedJobs) {
        renderTone = 'bad';
        renderValue = `${snapshot.failedJobs} issue${snapshot.failedJobs > 1 ? 's' : ''}`;
        renderCopy = '至少有一个渲染相关 job 失败或 stale。';
      } else if (snapshot.activeJobs) {
        renderTone = 'warn';
        renderValue = `${snapshot.activeJobs} active`;
        renderCopy = snapshot.materializedAssets
          ? '已有部分资产落盘，剩余 job 仍在继续。'
          : '渲染任务正在运行，等待首批资产出现。';
      } else if (snapshot.materializedAssets) {
        renderTone = 'ok';
        renderValue = `${snapshot.materializedAssets}/${snapshot.totalAssets || snapshot.materializedAssets} assets`;
        renderCopy = '中间资产已可检查，说明渲染链路已经产出结果。';
      }

      let exportTone = resultState.tone;
      let exportValue = view.final_export?.download_url ? 'Ready' : 'Pending';
      let exportCopy = resultState.copy;
      if (!view.final_export?.download_url && snapshot.failedJobs) {
        exportTone = 'bad';
        exportValue = 'Blocked';
      } else if (!view.final_export?.download_url && snapshot.activeJobs) {
        exportTone = 'warn';
        exportValue = 'Rendering';
      } else if (!view.final_export?.download_url && snapshot.materializedAssets) {
        exportTone = 'neutral';
        exportValue = 'Awaiting merge';
      }

      return [
        { label: 'Compile', tone: compileTone, value: statusCopy(view.compile_status), copy: compileCopy },
        { label: 'Dispatch', tone: dispatchTone, value: statusCopy(view.dispatch_status), copy: dispatchCopy },
        { label: 'Render', tone: renderTone, value: renderValue, copy: renderCopy },
        { label: 'Export', tone: exportTone, value: exportValue, copy: exportCopy },
      ];
    }

    function preferredRuntimeView(views, preferredRuntimeId = null) {
      const list = Array.isArray(views) ? views : [];
      if (!list.length) return null;
      if (preferredRuntimeId) {
        const exact = list.find(view => view.runtime_id === preferredRuntimeId);
        if (exact) return exact;
      }
      const exportReady = list.find(view => view.final_export?.download_url);
      if (exportReady) return exportReady;
      const successful = list.find(view => {
        const jobs = Array.isArray(view.jobs) ? view.jobs : [];
        return view.compile_status === 'completed'
          && !jobs.some(job => ['failed', 'stale'].includes(job.status));
      });
      return successful || list[0];
    }

    function renderRuntime(view) {
      const jobs = Array.isArray(view.jobs) ? view.jobs : [];
      const assets = Array.isArray(view.assets) ? view.assets : [];
      const grouped = groupedAssets(assets);
      const progress = runtimeProgress(view);
      const resultState = runtimeResultState(view, assets);
      const activityState = runtimeActivityState(view, assets);
      const snapshot = runtimeJobSnapshot({ jobs, assets });
      const stages = runtimeStageSummary(view, assets);
      const finalExport = view.final_export;
      const failureCluster = runtimeFailureCluster(view);
      const inspectionCards = runtimeInspectionCards(view, assets);
      const actionHints = runtimeActionHints(view, assets);
      const primaryInspectionAsset = primaryAssetForInspection(assets);
      const previewSource = runtimePreviewSource(view, assets);
      const exportActions = finalExport?.download_url
        ? `<div class="export-actions">
            <a class="link-btn" href="${finalExport.download_url}" target="_blank">下载最终 MP4</a>
            <a class="download-link" href="${finalExport.download_url}" target="_blank">在新标签打开</a>
          </div>`
        : previewSource?.url
          ? `<div class="export-actions">
              <a class="link-btn" href="${previewSource.url}" target="_blank">${previewSource.kind === 'file' ? '打开可检查文件' : '打开当前预览源'}</a>
              <small class="runtime-list-copy">final export 未完成，可先抽检 ${escapeHtml(assetGroupFor(previewSource.asset || primaryInspectionAsset || {}))} 结果。</small>
            </div>`
          : '<small class="runtime-list-copy">最终导出生成后，这里会自动切换为站内预览。</small>';
      const previewBlock = previewSource?.kind === 'video'
        ? `<video class="preview-video" controls playsinline preload="metadata" src="${previewSource.url}"></video>`
        : previewSource?.kind === 'image'
          ? `<img class="preview-image" alt="${escapeHtml(previewSource.title || 'Preview image')}" src="${previewSource.url}" />`
          : previewSource?.kind === 'audio'
            ? `<div class="preview-audio-shell">
                <div class="preview-audio-card">
                  <div class="preview-audio-copy">
                    <b>${escapeHtml(previewSource.title || 'Audio Preview')}</b>
                    <small>${escapeHtml(previewSource.copy || '先在这里检查音频结果。')}</small>
                  </div>
                  <audio class="preview-audio" controls preload="metadata" src="${previewSource.url}"></audio>
                </div>
              </div>`
            : previewSource?.kind === 'file'
              ? `<div class="preview-empty ${escapeHtml(previewSource.tone || 'neutral')}">
                  <div class="preview-empty-inner">
                    <div class="preview-empty-mark">↗</div>
                    <b>${escapeHtml(previewSource.title || 'Inspectable File')}</b>
                    <span>${escapeHtml(previewSource.copy || '该资产可直接在新标签打开继续检查。')}</span>
                    <a class="download-link" target="_blank" href="${previewSource.url}">打开文件</a>
                  </div>
                </div>`
              : `<div class="preview-empty ${escapeHtml(resultState.tone)}">
                  <div class="preview-empty-inner">
                    <div class="preview-empty-mark">${resultState.tone === 'bad' ? '✕' : resultState.tone === 'warn' ? '◌' : resultState.tone === 'ok' ? '✓' : '•'}</div>
                    <b>${escapeHtml(resultState.title)}</b>
                    <span>${escapeHtml(resultState.copy)}</span>
                  </div>
                </div>`;
      const previewCaption = previewSource?.caption
        ? previewSource.caption
        : failureCluster.hasIssues
          ? '当前导出被错误阻塞，请先处理失败项。'
          : snapshot.materializedAssets
            ? 'final export 未完成，可先转到右侧 inspection queue 抽检中间结果。'
            : snapshot.activeJobs
              ? '轮询会继续刷新该区域。'
              : '等待首批资产 materialized 后，这里会出现更明确的消费入口。';
      const previewMeta = [
        {
          label: 'Preview Source',
          value: previewSource?.metaValue || 'Awaiting Output',
          copy: previewSource?.metaCopy || '等待首个可检查输出出现。',
        },
        {
          label: 'Delivery',
          value: finalExport?.download_url ? 'MP4 Ready' : 'Pending',
          copy: finalExport?.download_url ? '可直接下载交付。' : '等待 merge/export 完成。',
        },
        {
          label: 'Render Jobs',
          value: snapshot.totalJobs ? `${snapshot.doneJobs}/${snapshot.totalJobs}` : '0/0',
          copy: snapshot.activeJobs ? `${snapshot.activeJobs} active` : 'all settled',
        },
        {
          label: 'Assets Ready',
          value: `${snapshot.materializedAssets}/${snapshot.totalAssets || 0}`,
          copy: snapshot.materializedAssets ? '已有可下载资产。' : '等待首批输出。',
        },
      ].map(item => `
        <div class="preview-meta-card">
          <span>${escapeHtml(item.label)}</span>
          <b>${escapeHtml(item.value)}</b>
          <small>${escapeHtml(item.copy)}</small>
        </div>
      `).join('');
      const errorBlock = failureCluster.hasIssues
        ? `<section id="failure-cluster" class="error-cluster">
            <div class="error-cluster-head">
              <div>
                <h3>Failure Cluster</h3>
                <p>把 compile / dispatch / job 级问题收束到一处，先排障再看结果。</p>
              </div>
              <span class="${badgeClass('failed')}">${failureCluster.issueCount} issue${failureCluster.issueCount > 1 ? 's' : ''}</span>
            </div>
            <div class="error-cluster-grid">
              ${failureCluster.items.map(item => `
                <div class="error-cluster-item ${escapeHtml(item.tone)}">
                  <b>${escapeHtml(item.label)}</b>
                  <small>${escapeHtml(item.detail)}</small>
                </div>
              `).join('')}
            </div>
          </section>`
        : view.last_error_message
          ? `<div class="toast error">${escapeHtml(view.last_error_message)}</div>`
          : '';
      const actionHintsMarkup = actionHints.length
        ? actionHints.map((hint, index) => `
            <div class="inspection-item">
              <div class="inspection-item-main">
                <b>Next Step ${index + 1}</b>
                <small>${escapeHtml(hint)}</small>
              </div>
              <div class="inspection-item-side">
                <span class="inspection-chip">step ${index + 1}</span>
              </div>
            </div>
          `).join('')
        : '<div class="inspection-item"><div class="inspection-item-main"><b>Next Step</b><small>当前没有额外动作，继续观察 runtime 变化即可。</small></div></div>';
      const inspectionTierLabels = {
        blocked: 'Blocked / Needs attention',
        ready: 'Ready to inspect now',
        waiting: 'Waiting on upstream',
      };
      const inspectionTierCounts = {
        blocked: inspectionCards.filter(card => card.tier === 'blocked').length,
        ready: inspectionCards.filter(card => card.tier === 'ready').length,
        waiting: inspectionCards.filter(card => card.tier === 'waiting').length,
      };
      const priorityCard = inspectionCards[0] || null;
      const inspectionPriorityMarkup = priorityCard
        ? `
            <div class="inspection-item">
              <div class="inspection-item-main">
                <b>${escapeHtml(priorityCard.title)}</b>
                <small>${escapeHtml(priorityCard.linkedIssue
                  ? '当前最高优先级与 failure cluster 相连，先清障，再决定是否继续扩展抽检。'
                  : priorityCard.tier === 'ready'
                    ? '这里只保留当前最先打开的 inspection 入口；完整原因、样本与后续队列都在下方 tier cards。'
                    : '当前没有可直接消费的输出，先看下方 waiting tier 判断结果还卡在上游哪一段。')}</small>
                <div class="inspection-chip-row">
                  <span class="inspection-chip">${escapeHtml(inspectionTierLabels[priorityCard.tier] || 'Inspection queue')}</span>
                  <span class="inspection-chip">${escapeHtml(priorityCard.availability || (priorityCard.count ? `${priorityCard.count} item${priorityCard.count > 1 ? 's' : ''} behind this queue` : 'watch this lane'))}</span>
                  ${priorityCard.linkedIssue ? '<span class="inspection-chip">resolve blocker first</span>' : ''}
                </div>
              </div>
              <div class="inspection-item-side">
                <span class="${badgeClassForTone(priorityCard.tone)}">top priority</span>
                ${priorityCard.ctaHref ? `<a class="download-link" ${priorityCard.ctaHref.startsWith('#') ? '' : 'target="_blank"'} href="${priorityCard.ctaHref}">${escapeHtml(priorityCard.ctaLabel || '打开样本')}</a>` : '<a class="download-link" href="#output-inspection">查看下方队列</a>'}
              </div>
            </div>
            <div class="inspection-item">
              <div class="inspection-item-main">
                <b>Queue Shape</b>
                <small>这里只做导航摘要；下方 Output Inspection 才是完整的 tier、why-here、availability 与 sample 细节来源。</small>
                <div class="inspection-chip-row queue-shape">
                  <span class="inspection-chip">Blocked ${inspectionTierCounts.blocked || 0}</span>
                  <span class="inspection-chip">Ready ${inspectionTierCounts.ready || 0}</span>
                  <span class="inspection-chip">Waiting ${inspectionTierCounts.waiting || 0}</span>
                </div>
              </div>
              <div class="inspection-item-side">
                <span class="${badgeClassForTone(inspectionTierCounts.blocked ? 'bad' : inspectionTierCounts.ready ? 'ok' : 'warn')}">${inspectionCards.length} card${inspectionCards.length > 1 ? 's' : ''}</span>
                <a class="download-link" href="#output-inspection">Open tiered queue</a>
              </div>
            </div>
          `
        : `<div class="inspection-item"><div class="inspection-item-main"><b>Inspection Queue</b><small>当前没有可导航的 inspection card；下方队列出现内容后会自动同步。</small></div><div class="inspection-item-side"><span class="${badgeClassForTone('neutral')}">clear</span></div></div>`;
      const groupOrder = ['merged export', 'video', 'voice', 'image', 'other'];
      const groupDescriptions = {
        'merged export': '最终交付入口；若已 materialized，优先直接打开或下载。',
        video: '运动与节奏抽检入口，用于 spot-check render 结果。',
        voice: '口播 / 配音库存，用于听感与内容核对。',
        image: '关键帧与静帧库存，用于构图与主体一致性复查。',
        other: '补充或调试文件，仅在需要时再展开。',
      };
      const assetInventoryEmptyCopy = failureCluster.hasIssues
        ? '还没有可盘点资产；先处理上方 Failure Cluster，再回来看 output inventory。'
        : snapshot.activeJobs
          ? '资产清单仍为空；首批 output materialized 后，这里会按类型自动归档。'
          : '当前没有可盘点资产；若状态长期不变，回看 Output Inspection 与 Jobs Timeline 判断卡点。';
      const assetGroupsMarkup = groupOrder.map(groupName => {
        const items = grouped[groupName] || [];
        if (!items.length) return '';
        const readyCount = items.filter(asset => asset.status === 'materialized').length;
        const groupSummary = readyCount
          ? readyCount === items.length
            ? `${groupDescriptions[groupName] || 'Assets'} ${readyCount} 个结果都已可打开或下载。`
            : `${groupDescriptions[groupName] || 'Assets'} ${readyCount}/${items.length} 已可打开，其余仍在等待 materialized。`
          : `${groupDescriptions[groupName] || 'Assets'} 该组仍在等待首个可消费文件。`;
        const groupBadgeLabel = readyCount
          ? readyCount === items.length
            ? `${readyCount} ready`
            : `${readyCount}/${items.length} ready`
          : `${items.length} waiting`;
        return `
          <section class="asset-group">
            <div class="asset-group-head">
              <div>
                <h4>${escapeHtml(groupName)}</h4>
                <p>${escapeHtml(groupSummary)}</p>
              </div>
              <span class="${badgeClass(items.some(item => item.status === 'materialized') ? 'materialized' : items[0]?.status)}">${escapeHtml(groupBadgeLabel)}</span>
            </div>
            <div class="asset-grid">
              ${items.map(asset => `
                <div class="asset-card">
                  <div class="asset-card-top">
                    <b>${statusEmoji(asset.status)} ${escapeHtml(asset.asset_type)}</b>
                    <span class="${badgeClass(asset.status)}">${escapeHtml(statusCopy(asset.status))}</span>
                  </div>
                  <small class="asset-card-eyebrow">${escapeHtml(asset.asset_role || groupName)} · ${escapeHtml(asset.content_type || 'content type unavailable')} · ${escapeHtml(assetInspectionHint(asset))}</small>
                  <small class="asset-path">${escapeHtml(asset.bucket_name || '—')}/${escapeHtml(asset.object_key || '—')}</small>
                  <div class="asset-card-actions">
                    <div class="asset-card-hints">${escapeHtml(`${formatBytes(asset.file_size)} · ${asset.download_url ? 'ready to open' : 'awaiting file'}`)}</div>
                    ${asset.download_url ? `<a class="download-link" target="_blank" href="${asset.download_url}">${assetGroupFor(asset) === 'merged export' ? '打开 / 下载' : '打开检查'}</a>` : '<small class="runtime-list-copy">等待 materialized</small>'}
                  </div>
                </div>
              `).join('')}
            </div>
          </section>`;
      }).filter(Boolean).join('');
      const inspectionTierMeta = {
        blocked: {
          title: 'Blocked / Needs attention',
          copy: '这些项会直接压过 preview 与 inspection；先清障，再决定是否继续消费下方 ready 结果。',
          emptyTitle: 'No active blockers',
          emptyCopy: '当前没有 failure-linked inspection blocker，可直接转向 ready 队列。',
        },
        ready: {
          title: 'Ready to inspect now',
          copy: '已经有可消费结果；按这里的顺序抽检，不必先翻完整 asset 列表。',
          emptyTitle: 'Nothing ready yet',
          emptyCopy: '当前还没有 materialized 输出进入 inspection queue；继续看 waiting tier 判断卡在哪一段上游。',
        },
        waiting: {
          title: 'Waiting on upstream',
          copy: '这些项不是缺失，而是明确还在等待上游 compile / dispatch / render 继续产出。',
          emptyTitle: 'No waiting items',
          emptyCopy: '上游等待项已清空；若仍未看到结果，刷新 runtime 或回 Jobs Timeline 核对执行轨迹。',
        },
      };
      const outputInspectionMarkup = ['blocked', 'ready', 'waiting'].map(tier => {
        const meta = inspectionTierMeta[tier];
        const tierCards = inspectionCards.filter(card => card.tier === tier);
        const tierCount = tierCards.reduce((sum, card) => sum + (card.count || 0), 0);
        return `
          <section class="inspection-tier">
            <div class="inspection-tier-head">
              <div>
                <h4>${escapeHtml(meta.title)}</h4>
                <p>${escapeHtml(meta.copy)}</p>
              </div>
              <span class="${badgeClassForTone(tier === 'blocked' ? 'bad' : tier === 'ready' ? 'ok' : 'warn')}">${tierCards.length ? `${tierCards.length} card${tierCards.length > 1 ? 's' : ''}` : 'empty'}</span>
            </div>
            <div class="inspection-tier-grid">
              ${tierCards.length ? tierCards.map(card => `
                <section class="inspection-card ${escapeHtml(card.tone)} ${card.linkedIssue ? 'linked-issue' : ''}">
                  <div class="inspection-card-head">
                    <div>
                      <b>${escapeHtml(card.title)}</b>
                      <small>${escapeHtml(card.copy)}</small>
                    </div>
                    <span class="${badgeClassForTone(card.tone)}">${card.count ? `${card.count} item${card.count > 1 ? 's' : ''}` : 'watch'}</span>
                  </div>
                  <div class="inspection-item-main">
                    <small>Why here: ${escapeHtml(card.reason || '按当前 runtime 状态自动归类。')}</small>
                    ${card.availability ? `<small>Availability: ${escapeHtml(card.availability)}</small>` : ''}
                  </div>
                  <div class="inspection-chip-row">
                    ${card.linkedIssue ? '<span class="inspection-chip">failure outranks inspection</span>' : ''}
                    ${card.sampleLabel ? `<span class="inspection-chip">${escapeHtml(card.sampleLabel)}</span>` : ''}
                    ${tierCount && tierCards.length > 1 ? `<span class="inspection-chip">tier volume ${tierCount}</span>` : ''}
                    ${card.ctaHref ? `<a class="download-link" ${card.ctaHref.startsWith('#') ? '' : 'target="_blank"'} href="${card.ctaHref}">${escapeHtml(card.ctaLabel || '打开样本')}</a>` : ''}
                  </div>
                </section>
              `).join('') : `
                <section class="inspection-card neutral">
                  <div class="inspection-card-head">
                    <div>
                      <b>${escapeHtml(meta.emptyTitle)}</b>
                      <small>${escapeHtml(meta.emptyCopy)}</small>
                    </div>
                    <span class="${badgeClassForTone('neutral')}">clear</span>
                  </div>
                </section>
              `}
            </div>
          </section>
        `;
      }).join('');

      result.innerHTML = `
        <article class="runtime-card">
          <div class="runtime-top">
            <div>
              <div class="runtime-id">runtime_id · ${escapeHtml(view.runtime_id)}</div>
              <div class="runtime-pills">
                <span class="runtime-pill"><strong>${escapeHtml(statusCopy(view.compile_status))}</strong> compile</span>
                <span class="runtime-pill"><strong>${escapeHtml(statusCopy(view.dispatch_status))}</strong> dispatch</span>
                <span class="runtime-pill"><strong>${escapeHtml(view.runtime_version)}</strong> version</span>
              </div>
            </div>
            <div class="runtime-actions">
              <span class="${badgeClass(activityState.tone === 'ok' ? 'materialized' : activityState.tone === 'bad' ? 'failed' : activityState.tone === 'warn' ? 'running' : view.dispatch_status)}">${escapeHtml(activityState.label)}</span>
            </div>
          </div>
          <div class="progress"><span style="width:${progress}%"></span></div>
          <div class="progress-meta">
            <span>${snapshot.totalJobs ? `${snapshot.doneJobs}/${snapshot.totalJobs} jobs terminal` : 'No jobs yet'}</span>
            <span>${snapshot.totalAssets ? `${snapshot.materializedAssets}/${snapshot.totalAssets} assets materialized` : 'No assets yet'}</span>
          </div>
          <div class="runtime-overview-grid">
            <div class="overview-card">
              <span>Current Focus</span>
              <b>${escapeHtml(resultState.title)}</b>
              <small>${escapeHtml(resultState.copy)}</small>
            </div>
            <div class="overview-card">
              <span>Active Jobs</span>
              <b>${snapshot.activeJobs}</b>
              <small>${snapshot.totalJobs ? `${snapshot.totalJobs} total jobs in this runtime` : '等待 jobs 被编译或派发。'}</small>
            </div>
            <div class="overview-card">
              <span>Materialized Assets</span>
              <b>${snapshot.materializedAssets}/${snapshot.totalAssets || 0}</b>
              <small>${snapshot.materializedAssets ? '已有可下载中间件，可先做局部检查。' : '还没有可消费资产。'}</small>
            </div>
            <div class="overview-card">
              <span>Delivery State</span>
              <b>${finalExport?.download_url ? 'MP4 Ready' : 'Pending Export'}</b>
              <small>${finalExport?.download_url ? '可以直接预览、下载、用于交付。' : '等待 merge/export 完成后进入交付态。'}</small>
            </div>
          </div>
          <div class="stage-grid">
            ${stages.map(stage => `
              <div class="stage-card ${escapeHtml(stage.tone)}">
                <span class="stage-kicker">${escapeHtml(stage.label)}</span>
                <div class="stage-value">${escapeHtml(stage.value)}</div>
                <div class="stage-copy">${escapeHtml(stage.copy)}</div>
              </div>
            `).join('')}
          </div>
          <div class="stat-grid">
            <div class="mini-card">
              <span>Project ID</span>
              <strong>${escapeHtml(view.project_id)}</strong>
            </div>
            <div class="mini-card">
              <span>Last Error Code</span>
              <strong>${escapeHtml(view.last_error_code || '—')}</strong>
            </div>
          </div>
          ${errorBlock}
          <div>
            <div class="section-head" style="margin-bottom: 10px;">
              <div>
                <h3>Result Consumption</h3>
                <p>优先消费最终导出；未完成时，改看当前最适合检查的 runtime 结果。</p>
              </div>
            </div>
            <div class="result-consumption-grid">
              <section class="preview-shell">
                <div class="preview-head">
                  <div>
                    <h3>${escapeHtml(previewSource?.title || 'Final Export Preview')}</h3>
                    <p>${escapeHtml(previewSource?.copy || '直接在 Studio 内总审最终 MP4 的节奏、画幅与口播对齐。')}</p>
                  </div>
                  ${previewSource?.badge
                    ? `<span class="${badgeClassForTone(previewSource.tone || 'neutral')}">${escapeHtml(previewSource.badge)}</span>`
                    : finalExport?.download_url
                      ? `<span class="${badgeClass('materialized')}">ready to review</span>`
                      : `<span class="${badgeClass(view.compile_status)}">${escapeHtml(statusCopy(view.compile_status))}</span>`}
                </div>
                <div class="preview-frame">
                  ${previewBlock}
                </div>
                <div class="preview-caption">${escapeHtml(previewCaption)}</div>
                <div class="preview-meta-strip">${previewMeta}</div>
              </section>
              <section class="result-panel">
                <div class="result-panel-head">
                  <div>
                    <h3>Export State</h3>
                    <p>把运行态、失败态与可交付态收束到一处，便于快速判断下一步。</p>
                  </div>
                </div>
                <div class="result-state result-state-${escapeHtml(resultState.tone)}">
                  <div class="result-state-mark">${resultState.tone === 'bad' ? '✕' : resultState.tone === 'warn' ? '◌' : resultState.tone === 'ok' ? '✓' : '•'}</div>
                  <div class="result-state-copy">
                    <b>${escapeHtml(resultState.title)}</b>
                    <small>${escapeHtml(resultState.copy)}</small>
                  </div>
                </div>
                <div class="inspection-stack">
                  <section class="inspection-card ${escapeHtml(failureCluster.hasIssues ? 'bad' : resultState.tone)}">
                    <div class="inspection-card-head">
                      <div>
                        <b>Next Actions</b>
                        <small>把当前最值得执行的下一步收束成短路径。</small>
                      </div>
                    </div>
                    ${actionHintsMarkup}
                  </section>
                  <section class="inspection-card neutral">
                    <div class="inspection-card-head">
                      <div>
                        <b>Inspection Priority</b>
                        <small>这里只保留右侧导航摘要；完整原因、样本与分层细节在下方 Output Inspection。</small>
                      </div>
                    </div>
                    ${inspectionPriorityMarkup}
                  </section>
                </div>
                <div class="job-summary-grid">
                  <div class="mini-card">
                    <span>Available Assets</span>
                    <strong>${assets.length}</strong>
                  </div>
                  <div class="mini-card">
                    <span>Materialized Assets</span>
                    <strong>${snapshot.materializedAssets}</strong>
                  </div>
                  <div class="mini-card">
                    <span>Final Export</span>
                    <strong>${finalExport?.download_url ? 'Ready' : 'Pending'}</strong>
                  </div>
                </div>
                ${exportActions}
              </section>
            </div>
          </div>
          <section id="output-inspection" class="inspection-section">
            <div class="section-head" style="margin-bottom: 10px;">
              <div>
                <h3>Output Inspection</h3>
                <p>按当前最值得检查的顺序收敛输出，不必先翻完整 asset 列表。</p>
              </div>
            </div>
            <div class="inspection-grid">
              ${outputInspectionMarkup}
            </div>
          </section>
          <div id="jobs-timeline" class="inspection-section">
            <div class="section-head" style="margin-bottom: 10px;">
              <div>
                <h3>Jobs Timeline</h3>
                <p>这里主要看执行推进、轮询中的 active job，以及是否出现异常卡点；失败摘要仍以上方 Failure Cluster 为准。</p>
              </div>
            </div>
            <div class="timeline">
              ${jobs.length ? jobs.map(job => {
                const isActiveJob = ['queued', 'dispatched', 'running', 'waiting_retry'].includes(job.status);
                const isErroredJob = ['failed', 'stale'].includes(job.status);
                const isDoneJob = ['succeeded', 'completed'].includes(job.status);
                const jobTone = isErroredJob ? 'is-error' : isActiveJob ? 'is-live' : isDoneJob ? 'is-done' : '';
                const jobHint = isActiveJob
                  ? 'polling'
                  : isErroredJob
                    ? 'exception'
                    : 'settled';
                const jobMeta = isErroredJob
                  ? (job.error_message || '异常已汇总到 Failure Cluster，可回上方优先排障。')
                  : isActiveJob
                    ? '该 job 仍在轮询推进，状态变化会自动刷新。'
                    : '该 job 已经收束，可转向下方资产清单继续消费。';
                return `
                  <div class="timeline-item ${jobTone}">
                    <div class="timeline-mark">${statusEmoji(job.status)}</div>
                    <div class="timeline-copy job-line">
                      <div class="timeline-topline">
                        <b>${escapeHtml(job.job_type)} · ${escapeHtml(statusCopy(job.status))}</b>
                        <span class="${badgeClass(job.status)}"><small>${escapeHtml(jobHint)}</small></span>
                      </div>
                      <div class="runtime-meta">${escapeHtml(jobMeta)}</div>
                    </div>
                  </div>`;
              }).join('') : `<div class="empty">${escapeHtml(snapshot.activeJobs || snapshot.materializedAssets || failureCluster.hasIssues ? '当前 runtime 还没有可展示的 job 时间线；先结合上方状态卡与结果区判断进度。' : '暂无 jobs；提交后这里会开始展示轮询中的执行轨迹与异常提示。')}</div>`}
            </div>
          </div>
          <section class="inspection-section">
            <div class="section-head" style="margin-bottom: 10px;">
              <div>
                <h3>Assets by Output Type</h3>
                <p>这里主要做 output inventory 与跳转消费；优先顺序和阻塞原因请看上方 Output Inspection。</p>
              </div>
            </div>
            <div class="asset-group-grid">
              ${assetGroupsMarkup || `<div class="empty">${escapeHtml(assetInventoryEmptyCopy)}</div>`}
            </div>
          </section>
        </article>`;
    }

    function renderRecentRuntimes(views) {
      lastRuntimeViews = views || [];
      recentCount.textContent = String(lastRuntimeViews.length);
      if (!lastRuntimeViews.length) {
        runtimeList.innerHTML = '<div class="empty">暂无运行记录。</div>';
        return;
      }
      runtimeList.innerHTML = lastRuntimeViews.map(view => {
        const assets = Array.isArray(view.assets) ? view.assets : [];
        const activity = runtimeActivityState(view, assets);
        const snapshot = runtimeJobSnapshot({ jobs: view.jobs, assets });
        const exportReady = Boolean(view.final_export?.download_url);
        return `
          <article class="runtime-list-item ${view.runtime_id === activeRuntime ? 'active' : ''}" data-runtime-id="${view.runtime_id}">
            <div class="runtime-list-meta">
              <div class="runtime-list-title">
                <span class="runtime-list-indicator ${escapeHtml(activity.tone)}"></span>
                <b>${escapeHtml(view.runtime_version)}</b>
              </div>
              <span class="${badgeClass(exportReady ? 'materialized' : activity.tone === 'bad' ? 'failed' : activity.tone === 'warn' ? 'running' : view.compile_status)}">${exportReady ? 'export ready' : escapeHtml(activity.label)}</span>
            </div>
            <small>${escapeHtml(view.runtime_id)}</small>
            <div class="runtime-list-statusline">
              <small>compile ${escapeHtml(statusCopy(view.compile_status))}</small>
              <small>dispatch ${escapeHtml(statusCopy(view.dispatch_status))}</small>
              <small>${snapshot.activeJobs ? `${snapshot.activeJobs} active job${snapshot.activeJobs > 1 ? 's' : ''}` : `${snapshot.totalJobs} jobs`}</small>
            </div>
            <small class="runtime-list-copy">${escapeHtml(recentRuntimeCopy(view, assets))}</small>
          </article>`;
      }).join('');
    }

    function selectedRuntimeView(views, { forcePreferred = false } = {}) {
      const list = Array.isArray(views) ? views : [];
      if (!list.length) return null;
      if (!forcePreferred && activeRuntime) {
        const exact = list.find(view => view.runtime_id === activeRuntime);
        if (exact) return exact;
      }
      return preferredRuntimeView(list);
    }

    function syncRuntimeConsumption(views, options = {}) {
      const selected = selectedRuntimeView(views, options);
      activeRuntime = selected?.runtime_id || null;
      renderRecentRuntimes(views);
      if (selected) {
        renderRuntime(selected);
      }
      return selected;
    }

    async function pollRuntime(runtimeId) {
      const res = await fetch(`/api/v1/studio/runtimes/${runtimeId}`);
      if (!res.ok) throw new Error(await res.text());
      const view = await res.json();
      const jobs = Array.isArray(view.jobs) ? view.jobs : [];
      activeRuntime = view.runtime_id;
      renderRuntime(view);
      if (lastRuntimeViews.length) {
        const existingIndex = lastRuntimeViews.findIndex(item => item.runtime_id === view.runtime_id);
        const merged = existingIndex >= 0
          ? lastRuntimeViews.map(item => item.runtime_id === view.runtime_id ? view : item)
          : [view, ...lastRuntimeViews].slice(0, 5);
        renderRecentRuntimes(merged);
      }
      const stillActive = jobs.some(job => ['queued', 'dispatched', 'running', 'waiting_retry'].includes(job.status));
      if (!stillActive && pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
        submitBtn.disabled = false;
      }
      return view;
    }

    async function refreshRecentRuntimes(options = {}) {
      const res = await fetch('/api/v1/studio/runtimes?limit=5');
      if (!res.ok) throw new Error(await res.text());
      const views = await res.json();
      const selected = syncRuntimeConsumption(views, options);
      if (!selected && !views.length) {
        result.innerHTML = '<div class="toast">暂无运行记录。</div>';
      }
      if (!selected || !runtimeHasActiveJobs(selected)) {
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = null;
        submitBtn.disabled = false;
      }
      return views;
    }

    function applyPreset(name) {
      const preset = presets[name];
      if (!preset) return;
      form.project_name.value = preset.project_name;
      form.product_name.value = preset.product_name;
      form.reference_note.value = preset.reference_note;
      form.visual_prompt.value = preset.visual_prompt;
      form.voice_script.value = preset.voice_script;
      form.negative_prompt.value = preset.negative_prompt;
      form.duration_ms.value = String(preset.duration_ms);
      defaultStoryboard();
      refreshSummary();
    }

    function showError(err) {
      result.innerHTML = `<pre>${escapeHtml(String(err?.stack || err))}</pre>`;
    }

    form.addEventListener('input', refreshSummary);
    segmentList.addEventListener('input', refreshSummary);

    quickModeBtn.addEventListener('click', () => setMode('quick'));
    storyModeBtn.addEventListener('click', () => {
      setMode('story');
      if (!segmentList.children.length) defaultStoryboard();
    });

    addSegmentBtn.addEventListener('click', () => {
      segmentList.insertAdjacentHTML('beforeend', segmentTemplate({
        sequence_type: 'body',
        duration_ms: 6000,
        visual_prompt: '',
        negative_prompt: defaultNegative,
      }));
      refreshSegmentIndexes();
      refreshSummary();
    });

    segmentList.addEventListener('click', (event) => {
      const button = event.target.closest('button');
      if (!button) return;
      const card = event.target.closest('.segment-card');
      if (!card) return;

      if (button.classList.contains('remove-segment-btn')) {
        card.remove();
      } else if (button.classList.contains('move-up-btn') && card.previousElementSibling) {
        card.parentNode.insertBefore(card, card.previousElementSibling);
      } else if (button.classList.contains('move-down-btn') && card.nextElementSibling) {
        card.parentNode.insertBefore(card.nextElementSibling, card);
      }

      refreshSegmentIndexes();
      refreshSummary();
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      submitBtn.disabled = true;
      result.innerHTML = '<div class="toast">正在创建 runtime，并触发 compile / render / merge 链路...</div>';
      try {
        const payload = payloadForSubmit();
        const res = await fetch('/api/v1/studio/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(await res.text());
        const created = await res.json();
        activeRuntime = created.runtime_id;
        const latestView = await pollRuntime(activeRuntime);
        await refreshRecentRuntimes();
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = null;
        if (runtimeHasActiveJobs(latestView)) {
          pollTimer = setInterval(() => pollRuntime(activeRuntime).catch(showError), 5000);
        } else {
          submitBtn.disabled = false;
        }
      } catch (err) {
        submitBtn.disabled = false;
        showError(err);
      }
    });

    refreshBtn.addEventListener('click', async () => {
      try {
        await refreshRecentRuntimes({ forcePreferred: true });
      } catch (err) {
        showError(err);
      }
    });

    runtimeList.addEventListener('click', async (event) => {
      const card = event.target.closest('[data-runtime-id]');
      if (!card) return;
      activeRuntime = card.getAttribute('data-runtime-id');
      renderRecentRuntimes(lastRuntimeViews);
      try {
        const latestView = await pollRuntime(activeRuntime);
        if (pollTimer) clearInterval(pollTimer);
        pollTimer = null;
        if (runtimeHasActiveJobs(latestView)) {
          pollTimer = setInterval(() => pollRuntime(activeRuntime).catch(showError), 5000);
        }
      } catch (err) {
        showError(err);
      }
    });

    document.querySelectorAll('[data-preset]').forEach(button => {
      button.addEventListener('click', () => applyPreset(button.dataset.preset));
    });

    fillSampleBtn.addEventListener('click', () => applyPreset('handbag'));

    resetBtn.addEventListener('click', () => {
      form.reset();
      form.project_name.value = 'studio-run';
      form.target_market.value = 'US';
      form.target_language.value = 'en-US';
      form.product_name.value = 'Premium structured handbag';
      form.reference_note.value = 'Use the reference video skeleton: bold product reveal, tactile detail close-ups, handling demo, and a clean final carry moment. Preserve sales pacing and short-form commerce rhythm.';
      form.visual_prompt.value = 'Create a 9:16 TikTok ecommerce product video segment for a premium structured handbag. Use handheld reveal, zipper and stitching close-ups, product handling, boutique lighting, realistic material texture, no subtitles, no watermark.';
      form.voice_script.value = 'This is the everyday bag that makes your outfit look instantly polished. Clean structure, practical space, and premium details for workdays, weekends, and everything in between.';
      form.negative_prompt.value = defaultNegative;
      form.duration_ms.value = '6000';
      segmentCounter = 0;
      segmentList.innerHTML = '';
      setMode('quick');
      refreshSummary();
    });

    defaultStoryboard();
    setMode('quick');
    refreshRecentRuntimes().catch(() => null);
    refreshSummary();
  </script>
</body>
</html>'''
