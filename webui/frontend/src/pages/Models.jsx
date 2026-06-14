import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';

// Loading skeleton loader for Models page
// 模型列表页面骨架屏
function ModelsSkeleton() {
  return (
    <>
      <div className="header-row">
        <div className="skeleton" style={{ width: 180, height: 36 }} />
      </div>
      
      {/* SVG 图表骨架 */}
      <div className="card" style={{ height: 260 }}>
        <div className="skeleton skeleton-title" style={{ width: '25%', height: 16, marginBottom: 24 }} />
        <div className="skeleton" style={{ width: '100%', height: 140 }} />
      </div>

      {/* 按钮骨架 */}
      <div style={{ marginBottom: 20, display: 'flex', gap: 10 }}>
        <div className="skeleton" style={{ width: 100, height: 38, borderRadius: 10 }} />
        <div className="skeleton" style={{ width: 120, height: 38, borderRadius: 10 }} />
        <div className="skeleton" style={{ width: 110, height: 38, borderRadius: 10 }} />
      </div>

      {/* 表格骨架 */}
      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} style={{ display: 'flex', gap: 24 }}>
              <div className="skeleton" style={{ flex: 1, height: 16 }} />
              <div className="skeleton" style={{ flex: 3, height: 16 }} />
              <div className="skeleton" style={{ flex: 2, height: 16 }} />
              <div className="skeleton" style={{ flex: 1.5, height: 16 }} />
              <div className="skeleton" style={{ flex: 2, height: 16 }} />
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

// Custom SVG Bar Chart Component for winrate visualization
// 自定义 SVG 柱状图组件，用于可视化模型胜率趋势
function WinrateBarChart({ data }) {
  const [hoveredBar, setHoveredBar] = useState(null);

  if (!data || data.length === 0) return null;

  // Sort by round ascending for chronological chart view
  // 按照轮次升序排列以保证时间轴正确
  const chartData = [...data].sort((a, b) => a.round - b.round);
  
  const height = 220;
  const paddingLeft = 45;
  const paddingRight = 30;
  const paddingTop = 30;
  const paddingBottom = 40;
  
  const barWidth = 28;
  const barGap = 18;
  const chartInnerWidth = chartData.length * (barWidth + barGap);
  const width = Math.max(800, chartInnerWidth + paddingLeft + paddingRight);
  const chartHeight = height - paddingTop - paddingBottom;
  
  // Y coordinate for the 55% PK threshold line
  // 55% 晋升阈值所在的 Y 轴坐标
  const thresholdY = height - paddingBottom - (0.55 * chartHeight);

  return (
    <div className="card" style={{ overflowX: 'auto', padding: '24px' }}>
      <h2 style={{ marginBottom: 20 }}>胜率演化走势 / Winrate Trend Chart</h2>
      <div style={{ minWidth: '100%', width: width, height: height, overflowY: 'hidden', position: 'relative' }}>
        <svg width={width} height={height}>
          {/* Gradients for bars */}
          <defs>
            <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#34d399" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
            <linearGradient id="yellowGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fbbf24" />
              <stop offset="100%" stopColor="#d97706" />
            </linearGradient>
            <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f87171" />
              <stop offset="100%" stopColor="#dc2626" />
            </linearGradient>
          </defs>

          {/* Y axis grids & labels */}
          {/* Y 轴背景刻度线与标签 */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((val, idx) => {
            const y = height - paddingBottom - (val * chartHeight);
            return (
              <g key={idx}>
                <line x1={paddingLeft} y1={y} x2={width - paddingRight} y2={y} stroke="rgba(255, 255, 255, 0.05)" strokeWidth={1} />
                <text x={paddingLeft - 10} y={y + 4} fill="var(--text-dim)" fontSize={11} fontWeight={500} textAnchor="end">{(val * 100).toFixed(0)}%</text>
              </g>
            );
          })}
          
          {/* 55% PK promotion threshold reference line */}
          {/* 55% 晋升阈值虚线与文本标注 */}
          <line x1={paddingLeft} y1={thresholdY} x2={width - paddingRight} y2={thresholdY} stroke="var(--yellow)" strokeWidth={1.5} strokeDasharray="4 3" opacity={0.8} />
          <text x={width - paddingRight - 10} y={thresholdY - 6} fill="var(--yellow)" fontSize={10} fontWeight={700} textAnchor="end">晋升门槛 (55% Threshold)</text>

          {/* Bar Chart Rects */}
          {/* 绘制各个模型的胜率柱体 */}
          {chartData.map((m, idx) => {
            const barHeight = m.winrate * chartHeight;
            const x = paddingLeft + idx * (barWidth + barGap);
            const y = height - paddingBottom - barHeight;
            const isHovered = hoveredBar === m.hash;
            
            const gradId = m.promoted ? 'url(#greenGrad)' : m.winrate >= 0.55 ? 'url(#yellowGrad)' : 'url(#redGrad)';
            const color = m.promoted ? 'var(--green)' : m.winrate >= 0.55 ? 'var(--yellow)' : 'var(--red)';

            return (
              <g 
                key={m.hash}
                onMouseEnter={() => setHoveredBar(m.hash)}
                onMouseLeave={() => setHoveredBar(null)}
              >
                {/* Active bar light guide line */}
                {isHovered && (
                  <line x1={x + barWidth / 2} y1={paddingTop} x2={x + barWidth / 2} y2={height - paddingBottom} stroke="rgba(255, 255, 255, 0.04)" strokeWidth={barWidth + 8} />
                )}

                {/* Highlight/glow on hover is styled natively */}
                <rect 
                  x={x} 
                  y={y} 
                  width={barWidth} 
                  height={Math.max(4, barHeight)} 
                  fill={gradId} 
                  rx={5}
                  style={{ 
                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)', 
                    cursor: 'pointer',
                    filter: isHovered ? `drop-shadow(0 0 8px ${color})` : 'none',
                    transform: isHovered ? 'scaleY(1.02)' : 'none',
                    transformOrigin: `${x + barWidth / 2}px ${height - paddingBottom}px`
                  }}
                >
                  <title>{`第 ${m.round} 轮\nHash: ${m.hash}\n分支: ${m.branch}\n胜率: ${(m.winrate * 100).toFixed(2)}%\n结果: ${m.promoted ? '已晋升' : '已淘汰'}`}</title>
                </rect>

                {/* Winrate label above the bar */}
                <text 
                  x={x + barWidth / 2} 
                  y={y - 8} 
                  fill={isHovered ? 'var(--text-bright)' : 'var(--text-normal)'} 
                  fontSize={10} 
                  fontWeight={isHovered ? 800 : 600} 
                  textAnchor="middle"
                  style={{ transition: 'all 0.2s' }}
                >
                  {(m.winrate * 100).toFixed(0)}%
                </text>

                {/* Round labels on X axis */}
                <text 
                  x={x + barWidth / 2} 
                  y={height - paddingBottom + 18} 
                  fill={isHovered ? 'var(--text-bright)' : 'var(--text-dim)'} 
                  fontSize={11} 
                  fontWeight={isHovered ? 700 : 500}
                  textAnchor="middle"
                  style={{ transition: 'all 0.2s' }}
                >
                  R{m.round}
                </text>
              </g>
            );
          })}
          
          {/* X axis base line */}
          {/* X 轴基线 */}
          <line x1={paddingLeft} y1={height - paddingBottom} x2={width - paddingRight} y2={height - paddingBottom} stroke="var(--border)" strokeWidth={1.5} />
        </svg>
      </div>
    </div>
  );
}

export default function Models() {
  const [models, setModels] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [sortKey, setSortKey] = useState('round');
  const [sortDir, setSortDir] = useState('desc');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    api.getModels()
      .then(d => {
        setModels(d.models || []);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const branches = useMemo(() => [...new Set(models.map(m => m.branch))], [models]);

  const filtered = useMemo(() => {
    let list = filter === 'all' ? models : models.filter(m => m.branch === filter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(m => m.hash.toLowerCase().includes(q) || m.branch.toLowerCase().includes(q));
    }
    return [...list].sort((a, b) => {
      let va = a[sortKey], vb = b[sortKey];
      if (typeof va === 'string') { va = va.toLowerCase(); vb = vb?.toLowerCase() || ''; }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [models, filter, sortKey, sortDir, searchQuery]);

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const sortIcon = (key) => {
    if (sortKey !== key) return null;
    return sortDir === 'asc' ? ' ▲' : ' ▼';
  };

  if (error) {
    return (
      <div className="card" style={{ borderColor: 'var(--red)', padding: '24px', maxWidth: 600, margin: '40px auto' }}>
        <h2 style={{ color: 'var(--red)', margin: 0, fontSize: '18px' }}>获取模型列表失败 / Error</h2>
        <p style={{ color: 'var(--text-normal)', marginTop: 12 }}>{error}</p>
      </div>
    );
  }

  if (loading) return <ModelsSkeleton />;

  return (
    <>
      <div className="header-row">
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h1 style={{ margin: 0 }}>模型库管理 / Models</h1>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>对比、筛选和查阅历史版本模型指标</p>
        </div>
        <div>
          <input 
            type="text" 
            placeholder="搜索 Hash 或分支..." 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ 
              width: 240, 
              padding: '10px 16px', 
              background: 'var(--bg-card)', 
              border: '1px solid var(--border)',
              borderRadius: 12
            }}
          />
        </div>
      </div>

      {/* Winrate Bar Chart Visualization */}
      {/* 胜率柱状图可视化区域 */}
      <WinrateBarChart data={filtered} />

      {/* Filter tabs */}
      {/* 分支筛选页签 */}
      <div style={{ marginBottom: 24, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button 
          className={`btn ${filter === 'all' ? 'btn-primary' : ''}`} 
          onClick={() => setFilter('all')}
          style={{ borderRadius: 10 }}
        >
          全部分支 / All ({models.length})
        </button>
        {branches.map(b => (
          <button 
            key={b} 
            className={`btn ${filter === b ? 'btn-primary' : ''}`} 
            onClick={() => setFilter(b)}
            style={{ borderRadius: 10 }}
          >
            {b} ({models.filter(m => m.branch === b).length})
          </button>
        ))}
      </div>

      {/* Responsive table */}
      {/* 响应式表格，支持横向滚动 */}
      <div className="card" style={{ overflowX: 'auto', padding: 0, borderTopLeftRadius: 16, borderTopRightRadius: 16 }}>
        <table style={{ minWidth: 700 }}>
          <thead>
            <tr>
              <th onClick={() => toggleSort('round')} style={{ cursor: 'pointer', userSelect: 'none', transition: 'color 0.2s' }} className="sortable-header">
                轮次 / Round {sortIcon('round')}
              </th>
              <th onClick={() => toggleSort('hash')} style={{ cursor: 'pointer', userSelect: 'none', transition: 'color 0.2s' }} className="sortable-header">
                模型 Hash {sortIcon('hash')}
              </th>
              <th onClick={() => toggleSort('branch')} style={{ cursor: 'pointer', userSelect: 'none', transition: 'color 0.2s' }} className="sortable-header">
                分支 / Branch {sortIcon('branch')}
              </th>
              <th onClick={() => toggleSort('winrate')} style={{ cursor: 'pointer', userSelect: 'none', transition: 'color 0.2s' }} className="sortable-header">
                胜率 / Winrate {sortIcon('winrate')}
              </th>
              <th onClick={() => toggleSort('promoted')} style={{ cursor: 'pointer', userSelect: 'none', transition: 'color 0.2s' }} className="sortable-header">
                状态 / Status {sortIcon('promoted')}
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(m => (
              <tr key={m.hash}>
                <td style={{ fontWeight: 700, color: 'var(--text-bright)', fontSize: 14 }}>{m.round}</td>
                <td><code style={{ color: '#38bdf8' }}>{m.hash}</code></td>
                <td style={{ fontFamily: 'monospace', color: 'var(--purple)', fontWeight: 600 }}>{m.branch}</td>
                <td style={{ fontWeight: 800, fontSize: 14, color: m.winrate >= 0.7 ? 'var(--green)' : m.winrate >= 0.55 ? 'var(--yellow)' : 'var(--red)' }}>
                  {(m.winrate * 100).toFixed(1)}%
                </td>
                <td>
                  <span className={`badge ${m.promoted ? 'promoted' : 'discarded'}`}>
                    {m.promoted ? '已晋升 / PROMOTED' : '已淘汰 / DISCARDED'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div style={{ color: 'var(--text-dim)', padding: 48, textAlign: 'center', fontSize: 14 }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 8, opacity: 0.5 }}><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            <div>未找到符合条件的模型 / No models matched the criteria</div>
          </div>
        )}
      </div>
    </>
  );
}
