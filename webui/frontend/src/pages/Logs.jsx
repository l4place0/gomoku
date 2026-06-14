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

// Single Log Line Component with Syntax Highlighting & Line Numbers
function LogLine({ text, index, theme }) {
  const isError = text.toUpperCase().includes('ERROR') || text.toUpperCase().includes('FAIL') || text.toUpperCase().includes('CRASHED');
  const isWarn = text.toUpperCase().includes('WARN') || text.toUpperCase().includes('WARNING');
  const isSuccess = text.toUpperCase().includes('SUCCESS') || text.toUpperCase().includes('PASS') || text.toUpperCase().includes('PROMOTED');
  
  let cls = 'log-line';
  if (isError) cls += ' error';
  else if (isWarn) cls += ' warn';
  else if (isSuccess) cls += ' success';

  // Highlight tags like [Selfplay], [Train], [PK], [Regression], [Golden] in console logs
  const parseLineContent = (rawText) => {
    const regex = /(\[[A-Za-z0-9\-\s_]+\])/g;
    const parts = rawText.split(regex);
    return parts.map((part, idx) => {
      if (regex.test(part)) {
        const tagName = part.slice(1, -1).toLowerCase();
        let tagColor = '#8b5cf6'; // Default purple
        
        // Dynamic colors for different stages/tags
        if (tagName.includes('selfplay')) tagColor = '#3b82f6'; // blue
        else if (tagName.includes('train')) tagColor = '#f59e0b'; // orange/yellow
        else if (tagName.includes('pk') || tagName.includes('stage-pk')) tagColor = '#10b981'; // green
        else if (tagName.includes('regression')) tagColor = '#f43f5e'; // pink/rose
        else if (tagName.includes('golden')) tagColor = '#eab308'; // gold
        
        return (
          <span key={idx} style={{ color: tagColor, fontWeight: 700, marginRight: 2 }}>
            {part}
          </span>
        );
      }
      return part;
    });
  };

  const getLineNoColor = () => {
    if (theme === 'matrix') return '#1f8b1f';
    if (theme === 'light') return '#94a3b8';
    return 'var(--text-muted)';
  };

  return (
    <div className={cls} style={{ display: 'flex', gap: 14, padding: '3px 8px' }}>
      <span style={{ 
        color: getLineNoColor(), 
        width: 36, 
        textAlign: 'right', 
        userSelect: 'none', 
        display: 'inline-block', 
        flexShrink: 0,
        fontFamily: 'monospace',
        opacity: 0.8
      }}>
        {index + 1}
      </span>
      <span style={{ flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
        {parseLineContent(text)}
      </span>
    </div>
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
  const [theme, setTheme] = useState('default');
  const logRef = useRef(null);

  // Fetch log files
  const refresh = () => {
    setLoading(true);
    const params = round ? { round } : {};
    api.getLogs(params).then(d => {
      const entries = d.logs || d.entries || [];
      setLogs(entries);
      
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
  }, [round]);

  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs, selectedFile, level, autoScroll, loading, searchQuery]);

  const isStructured = logs.length > 0 && typeof logs[0] === 'object' && logs[0].file !== undefined;
  const filesList = isStructured ? logs.map(f => f.file) : [];

  const linesToDisplay = useMemo(() => {
    if (!isStructured) {
      return logs.filter(line => {
        const s = typeof line === 'string' ? line : JSON.stringify(line);
        let matches = true;
        if (level === 'error') matches = s.toUpperCase().includes('ERROR') || s.toUpperCase().includes('FAIL');
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
      if (level === 'error') matches = line.toUpperCase().includes('ERROR') || line.toUpperCase().includes('FAIL');
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

  const downloadLogFile = () => {
    const text = linesToDisplay.join('\n');
    if (!text) return;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile || 'console.log';
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearFilters = () => {
    setRound('');
    setLevel('all');
    setSearchQuery('');
  };

  // Theme styling definitions for Hacker terminal
  const themeStyles = {
    default: { background: '#040711', color: '#cbd5e1', border: '1px solid var(--border)' },
    matrix: { background: '#020502', color: '#39ff14', textShadow: '0 0 4px rgba(57, 255, 20, 0.4)', border: '1px solid rgba(0, 200, 0, 0.2)' },
    monokai: { background: '#272822', color: '#f8f8f2', border: '1px solid #1e1f1c' },
    light: { background: '#f8fafc', color: '#0f172a', border: '1px solid #e2e8f0', boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.05)' }
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
          {/* Terminal Theme Selector */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', fontSize: 13, fontWeight: 500 }}>主题:</span>
            <select 
              value={theme} 
              onChange={e => setTheme(e.target.value)}
              style={{ 
                background: 'var(--bg-card)', 
                border: '1px solid var(--border)', 
                color: 'var(--text-bright)', 
                padding: '6px 10px', 
                borderRadius: 8, 
                fontSize: 12, 
                cursor: 'pointer'
              }}
            >
              <option value="default">Midnight</option>
              <option value="matrix">Matrix</option>
              <option value="monokai">Monokai</option>
              <option value="light">Light</option>
            </select>
          </div>

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

          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" onClick={copyToClipboard} style={{ fontSize: 12, padding: '8px 14px', borderRadius: 10, display: 'flex', gap: 6 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              {copying ? '已复制!' : '复制'}
            </button>
            <button className="btn" onClick={downloadLogFile} style={{ fontSize: 12, padding: '8px 14px', borderRadius: 10, display: 'flex', gap: 6 }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              下载
            </button>
          </div>
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
          padding: '20px',
          borderRadius: '16px',
          boxShadow: theme === 'light' ? 'inset 0 1px 3px rgba(0,0,0,0.05)' : 'inset 0 4px 20px rgba(0, 0, 0, 0.6)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          ...themeStyles[theme]
        }}
      >
        {linesToDisplay.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', padding: 48, textAlign: 'center', fontSize: 14 }}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: 12, opacity: 0.5 }}><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
            <div>未找到匹配的日志内容 / No logs found</div>
          </div>
        ) : (
          linesToDisplay.map((line, i) => (
            <LogLine 
              key={i} 
              text={line} 
              index={i} 
              theme={theme} 
            />
          ))
        )}
      </div>
    </>
  );
}
