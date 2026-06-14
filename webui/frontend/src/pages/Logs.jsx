import { useState, useEffect, useRef, useMemo } from 'react';
import { api } from '../api';

// Loading skeleton loader for Logs page
// 日志页面加载骨架屏
function LogsSkeleton() {
  return (
    <>
      <div className="header-row">
        <div className="skeleton" style={{ width: 150, height: 36 }} />
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div className="skeleton" style={{ width: 180, height: 32, borderRadius: 10 }} />
          <div className="skeleton" style={{ width: 80, height: 32, borderRadius: 10 }} />
          <div className="skeleton" style={{ width: 110, height: 32, borderRadius: 10 }} />
        </div>
      </div>
      <div className="card" style={{ height: 'calc(100vh - 220px)', display: 'flex', flexDirection: 'column', gap: 14, padding: '24px' }}>
        {[90, 75, 85, 40, 65, 80, 50, 95, 70, 60, 85, 45, 75].map((w, idx) => (
          <div key={idx} className="skeleton skeleton-text" style={{ width: `${w}%`, height: 13 }} />
        ))}
      </div>
    </>
  );
}

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [selectedFile, setSelectedFile] = useState('');
  const [error, setError] = useState(null);
  const [round, setRound] = useState('');
  const [level, setLevel] = useState('all');
  const [autoScroll, setAutoScroll] = useState(true);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [fontSize, setFontSize] = useState(12);
  const [copying, setCopying] = useState(false);
  const logRef = useRef(null);

  // Fetch log files
  // 从后端 API 拉取最新的日志数据
  const refresh = () => {
    setLoading(true);
    const params = round ? { round } : {};
    api.getLogs(params).then(d => {
      const entries = d.logs || d.entries || [];
      setLogs(entries);
      
      // Auto-select first log file if none selected or the previous selected one is gone
      // 如果未选中日志，或者之前选中的日志不存在了，默认选中首个日志文件
      if (entries.length > 0 && typeof entries[0] === 'object') {
        const fileNames = entries.map(f => f.file);
        if (!fileNames.includes(selectedFile)) {
          setSelectedFile(entries[0].file);
        }
      }
      setError(null);
    }).catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { 
    refresh(); 
  }, [round]); // Re-fetch only when round filter changes

  // Auto-scroll to bottom of logs if enabled
  // 如果开启了自动滚动，每次日志内容更新时滚动到最底部
  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs, selectedFile, level, autoScroll, loading, searchQuery]);

  // Check if response contains structured file items
  // 判断拉取到的日志数据是否为结构化的文件对象格式
  const isStructured = logs.length > 0 && typeof logs[0] === 'object' && logs[0].file !== undefined;
  const filesList = isStructured ? logs.map(f => f.file) : [];

  // Parse lines to display based on selected file, level, and search filters
  // 结合当前选择的日志文件、级别过滤及搜索关键词，计算实际要展示的日志行列表
  const linesToDisplay = useMemo(() => {
    if (!isStructured) {
      return logs.filter(line => {
        const s = typeof line === 'string' ? line : JSON.stringify(line);
        let matches = true;
        if (level === 'error') matches = s.toUpperCase().includes('ERROR');
        else if (level === 'warn') matches = s.toUpperCase().includes('WARN') || s.toUpperCase().includes('WARNING');
        
        if (matches && searchQuery.trim()) {
          matches = s.toLowerCase().includes(searchQuery.toLowerCase());
        }
        return matches;
      });
    }

    const activeFile = logs.find(f => f.file === selectedFile) || logs[0];
    if (!activeFile) return [];

    const lines = activeFile.content.split('\n');
    return lines.filter(line => {
      let matches = true;
      if (level === 'error') matches = line.toUpperCase().includes('ERROR');
      else if (level === 'warn') matches = line.toUpperCase().includes('WARN') || line.toUpperCase().includes('WARNING');
      
      if (matches && searchQuery.trim()) {
        matches = line.toLowerCase().includes(searchQuery.toLowerCase());
      }
      return matches;
    });
  }, [logs, selectedFile, level, isStructured, searchQuery]);

  const copyToClipboard = () => {
    const text = linesToDisplay.join('\n');
    if (!text) return;
    setCopying(true);
    navigator.clipboard.writeText(text).then(() => {
      setTimeout(() => setCopying(false), 2000);
    });
  };

  const clearFilters = () => {
    setRound('');
    setLevel('all');
    setSearchQuery('');
  };

  if (error) {
    return (
      <div className="card" style={{ borderColor: 'var(--red)', padding: '24px', maxWidth: 600, margin: '40px auto' }}>
        <h2 style={{ color: 'var(--red)', margin: 0, fontSize: '18px' }}>获取日志列表失败 / Error</h2>
        <p style={{ color: 'var(--text-normal)', marginTop: 12 }}>{error}</p>
        <button className="btn btn-primary" onClick={refresh} style={{ marginTop: 20 }}>重试 / Retry</button>
      </div>
    );
  }

  if (loading) return <LogsSkeleton />;

  return (
    <>
      <div className="header-row">
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h1 style={{ margin: 0 }}>控制台日志 / Logs</h1>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>查阅、检索和下载模型训练产生的终端控制台日志</p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* File selector for structured logs */}
          {/* 当有多份日志文件时，显示文件选择下拉框 */}
          {isStructured && filesList.length > 0 && (
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ color: 'var(--text-dim)', fontSize: 13, fontWeight: 500 }}>日志文件:</span>
              <select 
                value={selectedFile} 
                onChange={e => setSelectedFile(e.target.value)}
                style={{ 
                  background: 'var(--bg-card)', 
                  border: '1px solid var(--border)', 
                  color: 'var(--text-bright)', 
                  padding: '8px 12px', 
                  borderRadius: 10, 
                  fontSize: 13, 
                  cursor: 'pointer',
                  maxWidth: 190 
                }}
              >
                {filesList.map(f => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          )}
          
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: 13, fontWeight: 500 }}>轮次:</span>
            <input 
              type="text" 
              value={round} 
              onChange={e => setRound(e.target.value)} 
              placeholder="例如 11"
              style={{ 
                background: 'var(--bg-card)', 
                border: '1px solid var(--border)', 
                color: 'var(--text-bright)', 
                padding: '8px 12px', 
                borderRadius: 10, 
                width: 80, 
                fontSize: 13 
              }} 
            />
          </div>

          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: 13, fontWeight: 500 }}>级别:</span>
            <select 
              value={level} 
              onChange={e => setLevel(e.target.value)}
              style={{ 
                background: 'var(--bg-card)', 
                border: '1px solid var(--border)', 
                color: 'var(--text-bright)', 
                padding: '8px 12px', 
                borderRadius: 10, 
                fontSize: 13, 
                cursor: 'pointer' 
              }}
            >
              <option value="all">全部 / All</option>
              <option value="error">错误 / Errors</option>
              <option value="warn">警告 / Warnings</option>
            </select>
          </div>
          
          <button className="btn" onClick={refresh} style={{ padding: '8px 16px', borderRadius: 10 }}>刷新</button>
        </div>
      </div>

      {/* Terminal Tools Bar */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input 
            type="text" 
            placeholder="在日志中搜索关键词..." 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ 
              width: 260, 
              padding: '8px 14px', 
              background: 'var(--bg-card)', 
              border: '1px solid var(--border)',
              borderRadius: 10,
              fontSize: 13
            }}
          />
          {(round || level !== 'all' || searchQuery) && (
            <button className="btn" onClick={clearFilters} style={{ fontSize: 12, padding: '6px 12px', borderColor: 'var(--red-glow)', color: 'var(--red)' }}>
              清除过滤
            </button>
          )}
        </div>
        
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '4px 8px', borderRadius: 8, border: '1px solid var(--border)' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: 11, fontWeight: 600 }}>字号:</span>
            <button onClick={() => setFontSize(Math.max(10, fontSize - 1))} style={{ background: 'none', border: 'none', color: 'var(--text-normal)', cursor: 'pointer', padding: '2px 6px', fontWeight: 'bold' }}>A-</button>
            <span style={{ fontSize: 12, fontWeight: 'bold', color: 'var(--text-bright)', padding: '0 4px' }}>{fontSize}px</span>
            <button onClick={() => setFontSize(Math.min(18, fontSize + 1))} style={{ background: 'none', border: 'none', color: 'var(--text-normal)', cursor: 'pointer', padding: '2px 6px', fontWeight: 'bold' }}>A+</button>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-dim)', cursor: 'pointer', userSelect: 'none' }}>
            <input 
              type="checkbox" 
              checked={autoScroll} 
              onChange={e => setAutoScroll(e.target.checked)} 
              style={{ cursor: 'pointer', borderRadius: 4 }}
            />
            自动滚动
          </label>

          <button className="btn" onClick={copyToClipboard} style={{ fontSize: 12, padding: '8px 14px', borderRadius: 10, display: 'flex', gap: 6 }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            {copying ? '已复制!' : '复制日志'}
          </button>
        </div>
      </div>

      {/* Terminal log panel */}
      {/* 终端日志展示面板 */}
      <div 
        className="card" 
        ref={logRef} 
        style={{ 
          height: 'calc(100vh - 230px)', 
          overflowY: 'auto', 
          fontFamily: "'JetBrains Mono', monospace", 
          fontSize: `${fontSize}px`,
          background: '#040711',
          border: '1px solid var(--border)',
          padding: '20px',
          borderRadius: '16px',
          boxShadow: 'inset 0 4px 20px rgba(0, 0, 0, 0.6)'
        }}
      >
        {linesToDisplay.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', padding: 48, textAlign: 'center', fontSize: 14 }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 12, opacity: 0.5 }}><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            <div>未找到匹配的日志内容 / No logs found</div>
          </div>
        ) : (
          linesToDisplay.map((line, i) => {
            const isError = line.toUpperCase().includes('ERROR');
            const isWarn = line.toUpperCase().includes('WARN') || line.toUpperCase().includes('WARNING');
            const cls = isError ? 'error' : isWarn ? 'warn' : '';
            return (
              <div key={i} className={`log-line ${cls}`} style={{ padding: '3px 8px' }}>
                {line}
              </div>
            );
          })
        )}
      </div>
    </>
  );
}
