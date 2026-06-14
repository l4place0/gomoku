import { useState, useEffect, useRef } from 'react';
import { api } from '../api';

// Loading skeleton component
// 加载骨架屏组件，提供闪烁动画占位符
function DashboardSkeleton() {
  return (
    <>
      <div className="header-row">
        <div className="skeleton" style={{ width: 220, height: 36 }} />
        <div style={{ display: 'flex', gap: 12 }}>
          <div className="skeleton" style={{ width: 120, height: 32 }} />
          <div className="skeleton" style={{ width: 90, height: 32 }} />
        </div>
      </div>
      <div className="grid grid-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="card" style={{ height: 130, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="skeleton skeleton-title" style={{ width: '40%', height: 14 }} />
              <div className="skeleton" style={{ width: '70%', height: 10 }} />
            </div>
            <div className="skeleton" style={{ width: '80%', height: 28, marginTop: 12 }} />
          </div>
        ))}
      </div>
      <div className="grid grid-2" style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="card" style={{ marginBottom: 0, height: 240, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="skeleton skeleton-title" style={{ width: '30%', height: 16 }} />
              <div className="skeleton skeleton-text" style={{ width: '90%', height: 12 }} />
              <div className="skeleton skeleton-text" style={{ width: '80%', height: 12 }} />
              <div className="skeleton skeleton-text" style={{ width: '70%', height: 12 }} />
            </div>
            <div className="skeleton" style={{ width: '40%', height: 14 }} />
          </div>
        </div>
        <div className="card" style={{ height: 240, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div className="skeleton skeleton-title" style={{ width: '35%', height: 16 }} />
            <div className="skeleton skeleton-text" style={{ width: '95%', height: 12 }} />
            <div className="skeleton skeleton-text" style={{ width: '75%', height: 12 }} />
            <div className="skeleton skeleton-text" style={{ width: '60%', height: 12 }} />
          </div>
          <div className="skeleton" style={{ width: '30%', height: 20 }} />
        </div>
      </div>
    </>
  );
}

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(null);
  const [models, setModels] = useState([]);
  const [error, setError] = useState(null);
  const [interval, setInterval_] = useState(10);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef(null);

  // Fetch status, progress, and models concurrently
  // 并发获取管道状态、训练进度以及模型列表
  const refresh = async () => {
    try {
      const [s, p, mList] = await Promise.all([
        api.getStatus(),
        api.getProgress(),
        api.getModels()
      ]);
      setStatus(s);
      setProgress(p);
      setModels(mList.models || []);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    timerRef.current = window.setInterval(refresh, interval * 1000);
    return () => clearInterval(timerRef.current);
  }, [interval]);

  const handleIntervalChange = (e) => {
    const val = parseInt(e.target.value, 10);
    if (val > 0) {
      clearInterval(timerRef.current);
      setInterval_(val);
    }
  };

  if (error) {
    return (
      <div className="card" style={{ borderColor: 'var(--red)', padding: '24px', maxWidth: 600, margin: '40px auto' }}>
        <h2 style={{ color: 'var(--red)', margin: 0, fontSize: '18px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: 'var(--red)' }} />
          连接错误 / Connection Error
        </h2>
        <p style={{ color: 'var(--text-normal)', marginTop: 12, fontSize: 14 }}>{error}</p>
        <button className="btn btn-primary" onClick={refresh} style={{ marginTop: 20 }}>重试 / Retry</button>
      </div>
    );
  }

  // Show loading skeleton during initial load
  // 首次加载时显示骨架屏效果
  if (loading || !status) return <DashboardSkeleton />;

  const m = status.current_model || {};
  const wr = m.winrate || 0;
  const wrColor = wr >= 0.7 ? 'var(--green)' : wr >= 0.55 ? 'var(--yellow)' : 'var(--red)';
  const stateColor = status.pipeline_state === 'running' ? 'var(--green)' : status.pipeline_state === 'crashed' ? 'var(--red)' : 'var(--text-dim)';

  // Find the model from the most recent round (highest round number)
  // 查找轮次最高（最新）的模型作为最近一轮 PK 结果
  const latestModel = models.length > 0 
    ? [...models].sort((a, b) => b.round - a.round)[0]
    : null;

  return (
    <>
      <div className="header-row">
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h1 style={{ margin: 0 }}>Gomoku ML 控制台</h1>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>监控模型自对弈训练与自动演化状态</p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '4px 12px', borderRadius: 10, border: '1px solid var(--border)' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: 13, fontWeight: 500 }}>自动刷新:</span>
            <select 
              value={interval} 
              onChange={handleIntervalChange} 
              style={{ 
                background: 'transparent', 
                border: 'none', 
                color: 'var(--text-bright)', 
                padding: '4px 8px', 
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <option value="5" style={{ background: 'var(--bg-deep)' }}>5 秒 / 5s</option>
              <option value="10" style={{ background: 'var(--bg-deep)' }}>10 秒 / 10s</option>
              <option value="30" style={{ background: 'var(--bg-deep)' }}>30 秒 / 30s</option>
              <option value="60" style={{ background: 'var(--bg-deep)' }}>60 秒 / 60s</option>
            </select>
          </div>
          <button className="btn" onClick={refresh}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transition: 'transform 0.3s' }} className="refresh-icon"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            手动刷新
          </button>
        </div>
      </div>

      {/* 状态统计卡片网格 */}
      <div className="grid grid-4">
        <StatCard title="运行状态" value={status.pipeline_state} color={stateColor} subtitle="Pipeline State" isRunning={status.pipeline_state === 'running'} />
        <StatCard title="当前轮次" value={`Round ${status.current_round || '-'}`} subtitle="Current Round" />
        <StatCard title="最佳胜率" value={`${(wr * 100).toFixed(1)}%`} color={wrColor} subtitle="Best Winrate" />
        <StatCard title="模型总数" value={`${status.model_registry_count} 个`} subtitle="Total Models" />
      </div>

      {/* 进度、模型详情与最近 PK 卡片布局 */}
      <div className="grid grid-2" style={{ marginTop: 24 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {progress && progress.stage && (
            <div className="card" style={{ marginBottom: 0 }}>
              <h2>
                <span className="dot" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', boxShadow: '0 0 8px var(--green)', marginRight: 2 }} />
                训练进度 / Progress
              </h2>
              <div className="stat-row">
                <span className="stat-label">当前阶段 (Stage)</span>
                <span className="stat-value" style={{ color: 'var(--blue)' }}>{progress.stage}</span>
              </div>
              <div style={{ marginTop: 20 }}>
                <div style={{ display: 'flex', justifycontent: 'space-between', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: 'var(--text-dim)', fontSize: 13 }}>完成比例</span>
                  <span style={{ color: 'var(--text-bright)', fontSize: 13, fontWeight: 700 }}>{progress.pct}%</span>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 6, height: 8, overflow: 'hidden', border: '1px solid var(--border)' }}>
                  <div style={{ background: 'linear-gradient(90deg, var(--blue) 0%, #60a5fa 100%)', height: '100%', width: `${progress.pct}%`, borderRadius: 6, transition: 'width 0.4s ease', boxShadow: '0 0 8px var(--blue)' }} />
                </div>
              </div>
              {progress.eta && (
                <div className="stat-row" style={{ marginTop: 16, borderBottom: 'none', paddingBottom: 0 }}>
                  <span className="stat-label">预计剩余时间 (ETA)</span>
                  <span className="stat-value" style={{ fontFamily: 'monospace', color: 'var(--yellow)' }}>{progress.eta}</span>
                </div>
              )}
            </div>
          )}

          <div className="card" style={{ marginBottom: 0 }}>
            <h2>最佳模型 / Best Model</h2>
            <div className="stat-row">
              <span className="stat-label">模型 Hash</span>
              <span className="stat-value"><code style={{ fontSize: '11px', color: '#38bdf8' }}>{m.hash || '-'}</code></span>
            </div>
            <div className="stat-row">
              <span className="stat-label">最佳胜率</span>
              <span className="stat-value" style={{ color: wrColor, fontWeight: 800, fontSize: 15 }}>{(wr * 100).toFixed(2)}%</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">演化账本轮数</span>
              <span className="stat-value" style={{ color: 'var(--text-bright)' }}>{status.ledger_rounds} 轮</span>
            </div>
          </div>
        </div>

        {/* 最近一轮 PK 结果卡片 */}
        <div className="card">
          <h2>最近一轮 PK 结果 / Recent PK Result</h2>
          {latestModel ? (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <div className="stat-row">
                <span className="stat-label">评测轮次</span>
                <span className="stat-value" style={{ color: 'var(--text-bright)', fontWeight: 700 }}>第 {latestModel.round} 轮 / Round {latestModel.round}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">候选模型 Hash</span>
                <span className="stat-value"><code style={{ fontSize: '11px', color: '#38bdf8' }}>{latestModel.hash}</code></span>
              </div>
              <div className="stat-row">
                <span className="stat-label">候选模型胜率 (vs 父模型)</span>
                <span className="stat-value" style={{ 
                  color: latestModel.winrate >= 0.7 ? 'var(--green)' : latestModel.winrate >= 0.55 ? 'var(--yellow)' : 'var(--red)',
                  fontWeight: 800,
                  fontSize: 15
                }}>
                  {(latestModel.winrate * 100).toFixed(2)}%
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">评测结果</span>
                <span className={`badge ${latestModel.promoted ? 'promoted' : 'discarded'}`}>
                  {latestModel.promoted ? '晋升 / PROMOTED' : '淘汰 / DISCARDED'}
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">分支来源</span>
                <span className="stat-value" style={{ fontFamily: 'monospace', fontWeight: 600, color: 'var(--purple)' }}>{latestModel.branch}</span>
              </div>
              <div className="stat-row" style={{ borderBottom: 'none', paddingBottom: 0 }}>
                <span className="stat-label">基准父模型</span>
                <span className="stat-value"><code style={{ fontSize: '11px' }}>{latestModel.parent ? latestModel.parent.slice(0, 8) + '...' : '-'}</code></span>
              </div>
            </div>
          ) : (
            <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '50px 0', fontSize: 13 }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 12, opacity: 0.5 }}><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <div>暂无 PK 记录信息 / No PK results available</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function StatCard({ title, value, color, subtitle, isRunning }) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: 130 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ fontSize: '12px', margin: 0, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px' }}>{title}</h2>
          <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: 2 }}>{subtitle}</span>
        </div>
        {isRunning && (
          <span style={{ display: 'inline-flex', position: 'relative', width: 8, height: 8 }}>
            <span style={{ position: 'absolute', display: 'inline-flex', height: '100%', width: '100%', borderRadius: '50%', background: 'var(--green)', opacity: 0.75, animate: 'ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite' }} className="pulse-dot" />
            <span style={{ position: 'relative', display: 'inline-flex', borderRadius: '50%', height: 8, width: 8, background: 'var(--green)' }} />
          </span>
        )}
      </div>
      <div style={{ fontSize: 26, fontWeight: 800, color: color || 'var(--text-bright)', marginTop: 12, lineHeight: 1.2, display: 'flex', alignItems: 'center', gap: 6 }}>
        {value}
      </div>
    </div>
  );
}
