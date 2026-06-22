import { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import ReactFlow, { Background, Controls, MarkerType, useNodesState, useEdgesState, Handle, Position, ReactFlowProvider, useReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import { api } from '../api';

// Custom Node Component to display model status in DAG
// 自定义模型节点，在演化图中展示模型详细状态
function ModelNode({ data, selected }) {
  const branchColor = data.branchColor || 'var(--blue)';
  const winrate = data.winrate || 0.5;
  
  // 胶囊形状的尺寸根据 winrate 动态调整 (winrate 越大，节点胶囊越宽)
  const width = 110 + winrate * 45;
  const height = 55 + winrate * 15;

  // 根据当前节点的选中、高亮、暗淡状态，拼接 CSS 类名
  let nodeClass = 'model-node';
  if (data.promoted) nodeClass += ' promoted';
  if (selected) nodeClass += ' selected';
  if (data.isDimmed) nodeClass += ' dimmed';
  if (data.isHighlighted) nodeClass += ' highlighted';

  return (
    <div 
      className={nodeClass}
      style={{
        width,
        height,
        borderColor: branchColor,
        color: branchColor, // 用于 CSS currentColor 机制动态改变阴影及边框颜色
      }}
    >
      {/* 输入连接点 (左侧) */}
      <Handle 
        type="target" 
        position={Position.Left} 
        style={{ background: branchColor, width: 6, height: 6, border: 'none' }} 
      />
      
      {/* 轮次标签 */}
      <div style={{ fontWeight: 800, color: 'var(--text-bright)', fontSize: 11, marginBottom: 1 }}>R{data.round}</div>
      {/* 缩略 Hash */}
      <div style={{ fontFamily: 'monospace', fontSize: 9, color: 'var(--text-dim)', marginBottom: 2 }}>
        {data.hash?.slice(0, 8)}
      </div>
      {/* 胜率显示 */}
      <div style={{ color: branchColor, fontWeight: 800, fontSize: 11 }}>
        {(winrate * 100).toFixed(1)}%
      </div>
      {/* 状态标签 */}
      {data.promoted ? (
        <div style={{ color: 'var(--green)', fontSize: 8, fontWeight: 800, marginTop: 1, letterSpacing: 0.5 }}>
          PROMOTED
        </div>
      ) : (
        <div style={{ color: 'var(--text-dim)', fontSize: 8, marginTop: 1 }}>
          discarded
        </div>
      )}

      {/* 输出连接点 (右侧) */}
      <Handle 
        type="source" 
        position={Position.Right} 
        style={{ background: branchColor, width: 6, height: 6, border: 'none' }} 
      />
    </div>
  );
}

// Custom Group Node Component for visual plan boundaries
// 自定义组节点，用于在演化图中展示 Plan 的视觉边界
function PlanGroupNode({ data }) {
  return (
    <div style={{
      width: '100%',
      height: '100%',
      border: '2px dashed rgba(56, 189, 248, 0.3)',
      backgroundColor: 'rgba(56, 189, 248, 0.015)',
      borderRadius: 16,
      pointerEvents: 'none',
      position: 'relative'
    }}>
      <div style={{
        position: 'absolute',
        top: -10,
        left: 14,
        fontSize: 10,
        fontWeight: 800,
        color: '#38bdf8',
        textTransform: 'uppercase',
        letterSpacing: 0.8,
        backgroundColor: '#0f172a',
        padding: '0 6px',
        border: '1px solid rgba(56, 189, 248, 0.3)',
        borderRadius: 4
      }}>
        Plan: {data.label}
      </div>
    </div>
  );
}

const nodeTypes = { model: ModelNode, planGroup: PlanGroupNode };

// Skeleton loading component for Graph page
// 演化图页面骨架屏
function GraphSkeleton() {
  return (
    <>
      <div className="skeleton" style={{ width: 280, height: 36, marginBottom: 24 }} />
      <div className="graph-container">
        <div className="skeleton" style={{ flex: 1, height: 'calc(100vh - 160px)' }} />
      </div>
    </>
  );
}

const CONSTRAINT_SWEET_SPOTS = {
  sf_games: { min: 100, recommended: 500 },
  pk_games: { min: 20 },
  tr_lr: { min: 0.0005 },
  sh_samples: { min: 50000, recommended: 150000 },
  tr_batch: { min: 16 }
};

function checkParamWarning(key, val) {
  if (val === undefined || val === null) return null;
  const numVal = parseFloat(val);
  const rule = CONSTRAINT_SWEET_SPOTS[key];
  if (!rule) return null;
  
  if (rule.min !== undefined && numVal < rule.min) {
    if (key === 'tr_lr') {
      return { level: 'critical', message: `低于极限下限 ${rule.min}，有 FP16 gradient underflow / NaN 风险` };
    }
    return { level: 'critical', message: `低于极限下限 ${rule.min}` };
  }
  if (rule.recommended !== undefined && numVal < rule.recommended) {
    return { level: 'warning', message: `低于推荐值 ${rule.recommended}` };
  }
  return null;
}

// Markdown Document Viewer Component
// Markdown 文档查看器组件，基于简易正则渲染标题、加粗、行内代码、代码块和列表
function MarkdownDocViewer({ planName }) {
  const [file, setFile] = useState('proposal.md');
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!planName) return;
    setLoading(true);
    setErr(null);
    api.getChangeMarkdown(planName, file)
      .then(res => {
        setContent(res.content || '');
      })
      .catch(e => {
        setErr(e.message || '加载失败');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [planName, file]);

  const renderMarkdown = (text) => {
    if (!text) return <p style={{ color: 'var(--text-dim)', fontSize: 12 }}>该文档内容为空 / Empty Document</p>;
    
    const lines = text.split('\n');
    let inCodeBlock = false;
    let codeContent = [];
    const elements = [];

    lines.forEach((line, idx) => {
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          inCodeBlock = false;
          elements.push(
            <pre key={`code-${idx}`} style={{ background: 'rgba(0,0,0,0.3)', padding: 10, borderRadius: 8, overflowX: 'auto', fontFamily: 'monospace', fontSize: 11, border: '1px solid var(--border)', color: '#38bdf8', margin: '8px 0' }}>
              {codeContent.join('\n')}
            </pre>
          );
          codeContent = [];
        } else {
          inCodeBlock = true;
        }
        return;
      }

      if (inCodeBlock) {
        codeContent.push(line);
        return;
      }

      const trimmed = line.trim();
      if (trimmed.startsWith('# ')) {
        elements.push(<h1 key={idx} style={{ fontSize: 15, color: 'var(--text-bright)', marginTop: 14, marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 4 }}>{trimmed.slice(2)}</h1>);
      } else if (trimmed.startsWith('## ')) {
        elements.push(<h2 key={idx} style={{ fontSize: 13, color: 'var(--text-bright)', marginTop: 12, marginBottom: 6 }}>{trimmed.slice(3)}</h2>);
      } else if (trimmed.startsWith('### ')) {
        elements.push(<h3 key={idx} style={{ fontSize: 11.5, color: 'var(--text-bright)', marginTop: 10, marginBottom: 4 }}>{trimmed.slice(4)}</h3>);
      } else if (trimmed.startsWith('- ')) {
        elements.push(<li key={idx} style={{ marginLeft: 12, fontSize: 11.5, color: 'var(--text-normal)', marginBottom: 4 }}>{trimmed.slice(2)}</li>);
      } else if (trimmed.startsWith('* ')) {
        elements.push(<li key={idx} style={{ marginLeft: 12, fontSize: 11.5, color: 'var(--text-normal)', marginBottom: 4 }}>{trimmed.slice(2)}</li>);
      } else if (trimmed) {
        let contentHtml = trimmed
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.06);padding:2px 4px;border-radius:4px;font-family:monospace;font-size:11px;color:#f43f5e">$1</code>');
        elements.push(<p key={idx} style={{ fontSize: 12, color: 'var(--text-normal)', lineHeight: 1.5, margin: '4px 0' }} dangerouslySetInnerHTML={{ __html: contentHtml }} />);
      } else {
        elements.push(<div key={idx} style={{ height: 4 }} />);
      }
    });

    return <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>{elements}</div>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {[
          { id: 'proposal.md', label: '提案' },
          { id: 'design.md', label: '设计' },
          { id: 'conclusion.md', label: '结论' },
          { id: 'tasks.md', label: '任务' }
        ].map(f => (
          <button 
            key={f.id} 
            className={`btn ${file === f.id ? 'btn-primary' : ''}`}
            onClick={() => setFile(f.id)}
            style={{ fontSize: 10, padding: '4px 6px', height: 'auto', flex: 1, minWidth: 60 }}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="markdown-body" style={{ flex: 1, overflowY: 'auto', background: 'rgba(0,0,0,0.15)', padding: 12, borderRadius: 10, border: '1px solid var(--border)', minHeight: 180, maxHeight: 350 }}>
        {loading && <div style={{ color: 'var(--text-dim)', fontSize: 11, textAlign: 'center', marginTop: 40 }}>加载中...</div>}
        {err && <div style={{ color: 'var(--text-dim)', fontSize: 10, textAlign: 'center', marginTop: 40 }}>该计划暂无此文档 / Unavailable</div>}
        {!loading && !err && renderMarkdown(content)}
      </div>
    </div>
  );
}

// Wrapper component to provide ReactFlowProvider context
// 包装组件，提供 ReactFlowProvider 上下文以使 useReactFlow 能够正常工作
export default function Graph() {
  return (
    <ReactFlowProvider>
      <GraphContent />
    </ReactFlowProvider>
  );
}

function GraphContent() {
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [branches, setBranches] = useState([]);
  const [searchParams] = useSearchParams();
  const locateHash = searchParams.get('locate');
  const { fitView } = useReactFlow();

  const [nodeTab, setNodeTab] = useState('details');
  const [edgeTab, setEdgeTab] = useState('details');

  useEffect(() => {
    api.getGraph().then(g => {
      setGraph(g);
      
      const nodesData = g.nodes || [];
      const rounds = nodesData.map(n => n.round);
      const minRound = rounds.length > 0 ? Math.min(...rounds) : 0;

      // Extract unique branches and sort them with 'mainline' first
      // 提取所有唯一分支，并将 mainline 主干排在最前
      const sortedBranches = Array.from(new Set(nodesData.map(n => n.branch)));
      sortedBranches.sort((a, b) => {
        if (a === 'mainline') return -1;
        if (b === 'mainline') return 1;
        return a.localeCompare(b);
      });

      // Define a premium color palette
      const BRANCH_PALETTE = [
        'var(--blue)',    // mainline
        'var(--purple)',
        'var(--green)',
        'var(--yellow)',
        '#f43f5e',        // Rose/Pink
        '#06b6d4',        // Cyan
        '#f97316',        // Orange
        '#ec4899',        // Magenta
      ];

      // Assign colors dynamically to branches
      const branchColorsMap = {};
      const branchesData = sortedBranches.map((br, index) => {
        let color = 'var(--blue)';
        if (br !== 'mainline') {
          const colorIndex = 1 + ((index - 1) % (BRANCH_PALETTE.length - 1));
          color = BRANCH_PALETTE[colorIndex];
        }
        branchColorsMap[br] = color;
        return { name: br, color };
      });
      setBranches(branchesData);

      // Map branches to specific vertical positions (Y axis)
      // 将不同分支映射到特定的垂直偏移量
      const branchYMap = {};
      sortedBranches.forEach((br, index) => {
        branchYMap[br] = index * 160;
      });

      // 建立哈希到分支的快速查找，用于连线获取源分支颜色
      const nodeBranchMap = {};
      nodesData.forEach(n => {
        nodeBranchMap[n.hash] = n.branch;
      });

      // Stack nodes at the same (round, branch) vertical coordinates to resolve overlaps
      // 针对在相同轮次和分支的节点，进行垂直堆叠排列，完全避免重叠
      const countPerRoundBranch = {};

      const nodesByPlan = {};
      const planList = [];

      // Map model nodes first to calculate parent group boxes
      const mappedModels = nodesData.map(n => {
        const round = n.round;
        const branch = n.branch;
        const key = `${round}-${branch}`;
        
        const stackIndex = countPerRoundBranch[key] || 0;
        countPerRoundBranch[key] = stackIndex + 1;
        
        const absX = (round - minRound) * 200;
        const absY = (branchYMap[branch] || 0) + stackIndex * 90;
        const branchColor = branchColorsMap[branch] || 'var(--yellow)';
        const planName = n.change;

        const node = {
          id: n.hash,
          type: 'model',
          absX,
          absY,
          data: { 
            ...n,
            branchColor,
            planName
          },
        };

        if (planName && planName !== 'init' && planName !== '') {
          if (!nodesByPlan[planName]) {
            nodesByPlan[planName] = [];
            planList.push(planName);
          }
          nodesByPlan[planName].push(node);
        }

        return node;
      });

      // Generate group nodes for each unique plan
      const groupNodes = planList.map(planName => {
        const groupModels = nodesByPlan[planName];
        const absXs = groupModels.map(m => m.absX);
        const absYs = groupModels.map(m => m.absY);

        const minX = Math.min(...absXs);
        const maxX = Math.max(...absXs.map(x => x + 155));
        const minY = Math.min(...absYs);
        const maxY = Math.max(...absYs.map(y => y + 70));

        const padX = 25;
        const padY = 40;

        const gX = minX - padX;
        const gY = minY - padY;
        const gWidth = (maxX - minX) + padX * 2;
        const gHeight = (maxY - minY) + padY * 2;

        // Reposition child models relative to parent group node
        groupModels.forEach(m => {
          m.parentId = `plan-group-${planName}`;
          m.position = {
            x: m.absX - gX,
            y: m.absY - gY
          };
        });

        return {
          id: `plan-group-${planName}`,
          type: 'planGroup',
          position: { x: gX, y: gY },
          style: { width: gWidth, height: gHeight },
          data: { label: planName }
        };
      });

      // For models that are not nested, set coordinates directly
      mappedModels.forEach(m => {
        if (!m.parentId) {
          m.position = { x: m.absX, y: m.absY };
        }
        delete m.absX;
        delete m.absY;
      });

      // Group nodes must render before model nodes so they sit underneath
      setNodes([...groupNodes, ...mappedModels]);

      // Map parent-child connections to smooth bezier or smoothstep edges
      // 路由连接线条，使用默认 of bezier (贝塞尔曲线) 并应用分支颜色
      setEdges((g.edges || []).map((e, i) => {
        const sourceBranch = nodeBranchMap[e.from] || 'mainline';
        const edgeColor = branchColorsMap[sourceBranch] || 'var(--yellow)';
        
        return {
          id: `e-${i}`,
          source: e.from,
          target: e.to,
          label: e.change || '',
          labelStyle: { fontSize: 10, fill: 'var(--text-dim)', fontWeight: 600 },
          style: { stroke: edgeColor, strokeWidth: 2, opacity: 0.8 },
          markerEnd: { type: MarkerType.ArrowClosed, color: edgeColor },
          type: 'default', // 用贝塞尔曲线 (bezier) 代替 smoothstep
          data: {
            branch: sourceBranch,
            color: edgeColor,
            change: e.change || '',
            hypothesis: e.hypothesis || '',
            param_diff: e.param_diff || {},
          }
        };
      }));

      // Focus on locating node if passed via url query
      if (locateHash) {
        const foundNode = nodesData.find(n => n.hash === locateHash);
        if (foundNode) {
          setSelectedNode(foundNode);
          setTimeout(() => {
            try {
              fitView({ nodes: [{ id: locateHash }], duration: 800 });
            } catch (err) {
              console.warn('fitView not ready', err);
            }
          }, 250);
        }
      }

    }).catch(e => setError(e.message));
  }, [setNodes, setEdges, locateHash, fitView]);

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node.data);
    setSelectedEdge(null);
    setNodeTab('details');
  }, []);

  const onEdgeClick = useCallback((_, edge) => {
    setSelectedEdge(edge.data ? { ...edge.data, source: edge.source, target: edge.target } : null);
    setSelectedNode(null);
    setEdgeTab('details');
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
  }, []);

  const selectedNodeId = selectedNode?.hash;

  // 选中节点时，计算所有相连节点 and 相连边的集合
  const { connectedNodeIds, connectedEdgeIds } = useMemo(() => {
    if (!selectedNodeId || !graph) {
      return { connectedNodeIds: new Set(), connectedEdgeIds: new Set() };
    }
    const nodeIds = new Set([selectedNodeId]);
    const edgeIds = new Set();
    
    (graph.edges || []).forEach((e, idx) => {
      if (e.from === selectedNodeId) {
        nodeIds.add(e.to);
        edgeIds.add(`e-${idx}`);
      } else if (e.to === selectedNodeId) {
        nodeIds.add(e.from);
        edgeIds.add(`e-${idx}`);
      }
    });
    
    return { connectedNodeIds: nodeIds, connectedEdgeIds: edgeIds };
  }, [selectedNodeId, graph]);

  // 当选中状态变化时，动态更新 ReactFlow nodes 和 edges 的高亮/暗淡状态
  useEffect(() => {
    setNodes((prevNodes) =>
      prevNodes.map((n) => {
        if (n.type === 'planGroup') return n;
        const isSelected = n.id === selectedNodeId;
        const isConnected = connectedNodeIds.has(n.id);
        const hasSelection = !!selectedNodeId;
        
        return {
          ...n,
          data: {
            ...n.data,
            isSelected,
            isHighlighted: hasSelection ? isConnected : false,
            isDimmed: hasSelection ? !isConnected : false,
          },
        };
      })
    );

    setEdges((prevEdges) =>
      prevEdges.map((e) => {
        const isConnected = connectedEdgeIds.has(e.id);
        const hasSelection = !!selectedNodeId;
        const edgeColor = e.data?.color || 'var(--border)';
        
        return {
          ...e,
          animated: hasSelection ? isConnected : false,
          style: {
            ...e.style,
            stroke: hasSelection 
              ? (isConnected ? edgeColor : 'rgba(45, 55, 72, 0.15)') 
              : edgeColor,
            strokeWidth: hasSelection ? (isConnected ? 3 : 2) : 2,
            opacity: hasSelection ? (isConnected ? 1 : 0.15) : 0.8,
          },
          markerEnd: {
            ...e.markerEnd,
            color: hasSelection 
              ? (isConnected ? edgeColor : 'rgba(45, 55, 72, 0.15)') 
              : edgeColor,
          },
        };
      })
    );
  }, [selectedNodeId, connectedNodeIds, connectedEdgeIds, setNodes, setEdges]);

  if (error) {
    return (
      <div className="card" style={{ borderColor: 'var(--red)', padding: '24px', maxWidth: 600, margin: '40px auto' }}>
        <h2 style={{ color: 'var(--red)', margin: 0, fontSize: '18px' }}>获取图谱数据失败 / Error</h2>
        <p style={{ color: 'var(--text-normal)', marginTop: 12 }}>{error}</p>
      </div>
    );
  }
  
  if (!graph) return <GraphSkeleton />;

  return (
    <>
      <div className="header-row">
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <h1 style={{ margin: 0 }}>模型演化图谱 / Evolution Graph</h1>
          <p style={{ fontSize: 13, color: 'var(--text-dim)', marginTop: 4 }}>点击模型节点或连接边线，可查看演化提案设计及胜率数据</p>
        </div>
      </div>
      
      <div className="graph-container">
        {/* Canvas box */}
        <div className="graph-canvas" style={{ flex: 1, background: 'rgba(11, 15, 25, 0.4)', borderRadius: 16, border: '1px solid var(--border)', overflow: 'hidden', position: 'relative' }}>
          
          {/* 分支图例面板 */}
          {branches.length > 0 && (
            <div className="graph-legend-container">
              <div className="graph-legend-title">分支图例 / Branches</div>
              {branches.map(br => (
                <div key={br.name} className="graph-legend-item">
                  <span className="graph-legend-color" style={{ background: br.color, boxShadow: `0 0 6px ${br.color}` }} />
                  <span>{br.name === 'mainline' ? 'mainline (主干)' : br.name}</span>
                </div>
              ))}
            </div>
          )}

          <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick} 
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
          >
            <Background color="rgba(255,255,255,0.03)" gap={20} />
            <Controls />
          </ReactFlow>
        </div>

        {/* Selected model details side card */}
        {selectedNode && (
          <div className="card graph-details" style={{ width: 340, overflow: 'auto', flexShrink: 0, marginBottom: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', paddingBottom: 8, gap: 12 }}>
              <button 
                className={`btn ${nodeTab === 'details' ? 'btn-primary' : ''}`}
                onClick={() => setNodeTab('details')}
                style={{ fontSize: 12, padding: '6px 12px', height: 'auto', flex: 1 }}
              >
                模型详情
              </button>
              <button 
                className={`btn ${nodeTab === 'docs' ? 'btn-primary' : ''}`}
                onClick={() => setNodeTab('docs')}
                style={{ fontSize: 12, padding: '6px 12px', height: 'auto', flex: 1 }}
                disabled={!selectedNode.change}
              >
                实验文档
              </button>
            </div>

            {nodeTab === 'details' ? (
              <>
                <h2>模型详情 / Model Details</h2>
                <div className="stat-row">
                  <span className="stat-label">模型 Hash</span>
                  <span className="stat-value"><code style={{ fontSize: '11px', color: '#38bdf8' }}>{selectedNode.hash}</code></span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">评测轮次</span>
                  <span className="stat-value">第 {selectedNode.round} 轮</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">所属分支</span>
                  <span className="stat-value" style={{ fontFamily: 'monospace', color: 'var(--purple)', fontWeight: 600 }}>{selectedNode.branch}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">PK 胜率</span>
                  <span className="stat-value" style={{ 
                    color: selectedNode.winrate >= 0.7 ? 'var(--green)' : selectedNode.winrate >= 0.55 ? 'var(--yellow)' : 'var(--red)', 
                    fontWeight: 800,
                    fontSize: 15
                  }}>
                    {(selectedNode.winrate * 100).toFixed(2)}%
                  </span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">晋升状态</span>
                  <span className={`badge ${selectedNode.promoted ? 'promoted' : 'discarded'}`}>
                    {selectedNode.promoted ? '已晋升 / PROMOTED' : '已淘汰 / DISCARDED'}
                  </span>
                </div>
                {selectedNode.change && (
                  <div className="stat-row">
                    <span className="stat-label">提案变更</span>
                    <span className="stat-value" style={{ color: 'var(--text-bright)', fontWeight: 600 }}>{selectedNode.change}</span>
                  </div>
                )}
                {selectedNode.hypothesis && (
                  <div className="stat-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 8 }}>
                    <span className="stat-label">科学假设 / Hypothesis</span>
                    <span className="stat-value" style={{ fontSize: 13, color: 'var(--text-normal)', whiteSpace: 'pre-wrap', lineHeight: 1.5, alignSelf: 'stretch', background: 'rgba(255, 255, 255, 0.02)', padding: 12, borderRadius: 10, border: '1px solid var(--border)' }}>
                      {selectedNode.hypothesis}
                    </span>
                  </div>
                )}
                {selectedNode.timestamp && (
                  <div className="stat-row" style={{ borderBottom: 'none', paddingBottom: 0 }}>
                    <span className="stat-label">创建时间</span>
                    <span className="stat-value" style={{ fontSize: 12, color: 'var(--text-dim)' }}>{selectedNode.timestamp}</span>
                  </div>
                )}
              </>
            ) : (
              <MarkdownDocViewer planName={selectedNode.change} />
            )}
          </div>
        )}

        {/* Selected edge details side card */}
        {selectedEdge && (
          <div className="card graph-details" style={{ width: 340, overflow: 'auto', flexShrink: 0, marginBottom: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', paddingBottom: 8, gap: 12 }}>
              <button 
                className={`btn ${edgeTab === 'details' ? 'btn-primary' : ''}`}
                onClick={() => setEdgeTab('details')}
                style={{ fontSize: 12, padding: '6px 12px', height: 'auto', flex: 1 }}
              >
                变更设计
              </button>
              <button 
                className={`btn ${edgeTab === 'docs' ? 'btn-primary' : ''}`}
                onClick={() => setEdgeTab('docs')}
                style={{ fontSize: 12, padding: '6px 12px', height: 'auto', flex: 1 }}
                disabled={!selectedEdge.change}
              >
                实验文档
              </button>
            </div>

            {edgeTab === 'details' ? (
              <>
                <h2>变更设计 / Proposal Details</h2>
                <div className="stat-row">
                  <span className="stat-label">源模型 (Parent)</span>
                  <span className="stat-value"><code style={{ fontSize: '11px', color: 'var(--text-normal)' }}>{selectedEdge.source.slice(0, 10)}...</code></span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">目标模型 (Child)</span>
                  <span className="stat-value"><code style={{ fontSize: '11px', color: '#38bdf8' }}>{selectedEdge.target.slice(0, 10)}...</code></span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">所属分支</span>
                  <span className="stat-value" style={{ fontFamily: 'monospace', color: 'var(--purple)', fontWeight: 600 }}>{selectedEdge.branch}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">演化提案 (Change)</span>
                  <span className="stat-value" style={{ color: 'var(--text-bright)', fontWeight: 700 }}>{selectedEdge.change || 'init'}</span>
                </div>
                {selectedEdge.hypothesis && (
                  <div className="stat-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 8 }}>
                    <span className="stat-label">科学假设 / Hypothesis</span>
                    <span className="stat-value" style={{ fontSize: 13, color: 'var(--text-normal)', whiteSpace: 'pre-wrap', lineHeight: 1.5, alignSelf: 'stretch', background: 'rgba(255, 255, 255, 0.02)', padding: 12, borderRadius: 10, border: '1px solid var(--border)' }}>
                      {selectedEdge.hypothesis}
                    </span>
                  </div>
                )}
                {selectedEdge.param_diff && Object.keys(selectedEdge.param_diff).length > 0 && (
                  <div className="stat-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 8, borderBottom: 'none', paddingBottom: 0 }}>
                    <span className="stat-label">超参配置 / Parameters</span>
                    <div style={{ width: '100%', background: 'rgba(0,0,0,0.2)', padding: '10px 14px', borderRadius: 10, border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {Object.entries(selectedEdge.param_diff).map(([key, val]) => {
                        const warning = checkParamWarning(key, val);
                        const color = warning ? (warning.level === 'critical' ? 'var(--red)' : 'var(--yellow)') : '#60a5fa';
                        return (
                          <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                            <span style={{ fontFamily: 'monospace', color: 'var(--text-dim)' }}>{key}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span style={{ fontFamily: 'monospace', color: color, fontWeight: 700 }}>
                                {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                              </span>
                              {warning && (
                                <span 
                                  title={warning.message} 
                                  style={{ 
                                    color: warning.level === 'critical' ? 'var(--red)' : 'var(--yellow)', 
                                    cursor: 'help',
                                    display: 'inline-flex',
                                    alignItems: 'center'
                                  }}
                                >
                                  ⚠️
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <MarkdownDocViewer planName={selectedEdge.change} />
            )}
          </div>
        )}
      </div>
    </>
  );
}
