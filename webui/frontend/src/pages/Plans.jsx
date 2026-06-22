import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

function PlansSkeleton() {
  return (
    <>
      <div className="header-row">
        <div className="skeleton" style={{ width: 180, height: 36 }} />
      </div>
      <div className="grid grid-3" style={{ marginTop: 24 }}>
        {[1, 2, 3].map(i => (
          <div key={i} className="card" style={{ height: 200, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div className="skeleton skeleton-title" style={{ width: '50%', height: 16 }} />
              <div className="skeleton skeleton-text" style={{ width: '80%', height: 12, marginTop: 12 }} />
              <div className="skeleton skeleton-text" style={{ width: '70%', height: 12 }} />
            </div>
            <div className="skeleton" style={{ width: '35%', height: 28, borderRadius: 8 }} />
          </div>
        ))}
      </div>
    </>
  );
}

export default function Plans() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.getPlans()
      .then(data => {
        setPlans(data.plans || []);
        setError(null);
      })
      .catch(err => {
        setError(err.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleLocate = (bestModel) => {
    if (bestModel) {
      navigate(`/graph?locate=${bestModel}`);
    } else {
      navigate('/graph');
    }
  };

  if (error) {
    return (
      <div className="card" style={{ borderColor: 'var(--red)', padding: '24px', maxWidth: 600, margin: '40px auto' }}>
        <h2 style={{ color: 'var(--red)', margin: 0, fontSize: '18px' }}>获取实验计划失败 / Error</h2>
        <p style={{ color: 'var(--text-normal)', marginTop: 12 }}>{error}</p>
      </div>
    );
  }

  if (loading) return <PlansSkeleton />;

  return (
    <>
      <div className="header-row">
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h1 style={{ margin: 0 }}>演化实验计划库 / Plans Library</h1>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>
            查看活动中或已归档的演化实验计划，并追踪其科学假设与训练指标
          </p>
        </div>
      </div>

      {plans.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px', color: 'var(--text-dim)' }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 16, opacity: 0.5 }}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          <p style={{ fontSize: 15, margin: 0 }}>暂无演化实验计划 / No Plans Available</p>
        </div>
      ) : (
        <div className="grid grid-3" style={{ marginTop: 24, gap: '20px' }}>
          {plans.map(p => {
            const isArchived = p.status === 'archived';
            const badgeClass = isArchived ? 'badge discarded' : 'badge promoted';
            const roundsPct = p.rounds_total > 0 ? Math.round((p.rounds_completed / p.rounds_total) * 100) : 0;

            return (
              <div key={p.plan} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: 250, position: 'relative', overflow: 'hidden' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                    <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-bright)' }}>{p.plan}</h3>
                    <span className={badgeClass} style={{ fontSize: 10, padding: '2px 8px', borderRadius: 6 }}>
                      {isArchived ? '已归档' : '进行中'}
                    </span>
                  </div>

                  {p.hypothesis && (
                    <p style={{ fontSize: 13, color: 'var(--text-normal)', background: 'rgba(255, 255, 255, 0.02)', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--border)', margin: '0 0 16px 0', lineHeight: 1.5 }}>
                      <strong style={{ color: 'var(--text-dim)', fontSize: 11, display: 'block', marginBottom: 2 }}>科学假设 / Hypothesis</strong>
                      {p.hypothesis}
                    </p>
                  )}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-dim)' }}>训练进度 / Progress</span>
                      <span style={{ color: 'var(--text-bright)', fontWeight: 600 }}>{p.rounds_completed} / {p.rounds_total} 轮 (Rounds)</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 4, height: 6, overflow: 'hidden', border: '1px solid var(--border)' }}>
                      <div style={{ background: 'var(--blue)', height: '100%', width: `${roundsPct}%`, borderRadius: 4, transition: 'width 0.4s' }} />
                    </div>

                    {p.best_model && (
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                        <span style={{ color: 'var(--text-dim)' }}>最佳模型 / Best Model</span>
                        <code style={{ color: '#38bdf8', fontSize: 11 }}>{p.best_model.slice(0, 8)}</code>
                      </div>
                    )}
                    {p.best_winrate !== null && p.best_winrate !== undefined && (
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-dim)' }}>最佳胜率 / Best Winrate</span>
                        <span style={{ color: 'var(--green)', fontWeight: 800 }}>{(p.best_winrate * 100).toFixed(1)}%</span>
                      </div>
                    )}
                  </div>
                </div>

                <div style={{ marginTop: 20, display: 'flex', gap: 10 }}>
                  <button 
                    className="btn btn-primary" 
                    onClick={() => handleLocate(p.best_model || p.initial_model)}
                    style={{ flex: 1, fontSize: 12, padding: '8px 12px', justifyContent: 'center' }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
                    图谱定位 / Locate
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
