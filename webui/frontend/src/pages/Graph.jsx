import { useState, useEffect, useMemo, useCallback } from 'react';
import ReactFlow, { Background, Controls, MarkerType, useNodesState, useEdgesState, Handle, Position } from 'reactflow';
import 'reactflow/dist/style.css';
import { api } from '../api';

// 分支颜色映射表，对应 mainline=蓝, v3-anti-overfit=紫, v4-stabilize=绿
const BRANCH_COLORS = {
  'mainline': 'var(--blue)',        // 蓝色
  'v3-anti-overfit': 'var(--purple)', // 紫色
  'v4-stabilize': 'var(--green)',    // 绿色
};

// 获取分支颜色，非预设分支默认为黄/橙色
const getBranchColor = (branch) => BRANCH_COLORS[branch] || 'var(--yellow)';

// Custom Node Component to display model status in DAG
// 自定义模型节点，在演化图中展示模型详细状态
function ModelNode({ data, selected }) {
  const branchColor = getBranchColor(data.branch);
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

const nodeTypes = { model: ModelNode };

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

export default function Graph() {
  const [graph, setGraph] = useState(null);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

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

      const newNodes = nodesData.map(n => {
        const round = n.round;
        const branch = n.branch;
        const key = `${round}-${branch}`;
        
        const stackIndex = countPerRoundBranch[key] || 0;
        countPerRoundBranch[key] = stackIndex + 1;
        
        // Base X: 200px separation per round
        const x = (round - minRound) * 200;
        
        // Base Y: branch horizontal lane offset + stacked node index vertical offset
        const y = (branchYMap[branch] || 0) + stackIndex * 90;

        return {
          id: n.hash,
          type: 'model',
          position: { x, y },
          data: { ...n },
        };
      });

      setNodes(newNodes);

      // Map parent-child connections to smooth bezier or smoothstep edges
      // 路由连接线条，使用默认的 bezier (贝塞尔曲线) 并应用分支颜色
      setEdges((g.edges || []).map((e, i) => {
        const sourceBranch = nodeBranchMap[e.from] || 'mainline';
        const edgeColor = getBranchColor(sourceBranch);
        
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
    }).catch(e => setError(e.message));
  }, [setNodes, setEdges]);

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node.data);
    setSelectedEdge(null);
  }, []);

  const onEdgeClick = useCallback((_, edge) => {
    setSelectedEdge(edge.data ? { ...edge.data, source: edge.source, target: edge.target } : null);
    setSelectedNode(null);
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
          <div className="graph-legend-container">
            <div className="graph-legend-title">分支图例 / Branches</div>
            <div className="graph-legend-item">
              <span className="graph-legend-color" style={{ background: 'var(--blue)', boxShadow: '0 0 6px var(--blue)' }} />
              <span>mainline (主干)</span>
            </div>
            <div className="graph-legend-item">
              <span className="graph-legend-color" style={{ background: 'var(--purple)', boxShadow: '0 0 6px var(--purple)' }} />
              <span>v3-anti-overfit (防过拟合)</span>
            </div>
            <div className="graph-legend-item">
              <span className="graph-legend-color" style={{ background: 'var(--green)', boxShadow: '0 0 6px var(--green)' }} />
              <span>v4-stabilize (稳定版)</span>
            </div>
            <div className="graph-legend-item">
              <span className="graph-legend-color" style={{ background: 'var(--yellow)', boxShadow: '0 0 6px var(--yellow)' }} />
              <span>others (其它分支)</span>
            </div>
          </div>

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
          </div>
        )}

        {/* Selected edge details side card */}
        {selectedEdge && (
          <div className="card graph-details" style={{ width: 340, overflow: 'auto', flexShrink: 0, marginBottom: 0, display: 'flex', flexDirection: 'column', gap: 14 }}>
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
                <div style={{ maxHeight: 180, overflowY: 'auto', width: '100%', background: 'rgba(0,0,0,0.2)', padding: 10, borderRadius: 10, border: '1px solid var(--border)' }}>
                  <pre style={{ fontSize: 11, fontFamily: 'monospace', color: '#60a5fa', margin: 0 }}>
                    {JSON.stringify(selectedEdge.param_diff, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
