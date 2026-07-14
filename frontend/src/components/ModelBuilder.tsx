import React, { useState, useCallback, useRef } from 'react';
import ReactFlow, {
  addEdge,
  type Connection,
  type Edge,
  type Node,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  ReactFlowProvider,
  Panel,
  MarkerType,
  Handle,
  Position
} from 'reactflow';
import 'reactflow/dist/style.css';

// --- Node Types (we'll just use a generic 'layerNode' for all) ---
const layerNodeTypes = {
  layerNode: LayerNode,
};

// The custom node component
function LayerNode({ data }: { data: any }) {
    return (
        <div style={{ padding: '10px', background: '#2a2a3a', borderRadius: '6px', border: '1px solid #555', minWidth: '120px', position: 'relative' }}>
            {/* Target handle (input) - left side */}
            <Handle
                type="target"
                position={Position.Left}
                style={{ background: '#555', width: '10px', height: '10px' }}
            />
            
            <div style={{ fontWeight: 'bold', color: '#eee' }}>{data.label}</div>
            {data.params && (
                <div style={{ fontSize: '0.7rem', color: '#aaa' }}>
                    {Object.entries(data.params)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(', ')}
                </div>
            )}

            {/* Source handle (output) - right side */}
            <Handle
                type="source"
                position={Position.Right}
                style={{ background: '#555', width: '10px', height: '10px' }}
            />
        </div>
    );
}

// --- Main component ---
interface ModelBuilderProps {
  onModelChange?: (nodes: Node[], edges: Edge[]) => void;
}

export function ModelBuilder({ onModelChange }: ModelBuilderProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  // --- Add node from sidebar drag ---
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      // Position where dropped
      const position = reactFlowWrapper.current?.getBoundingClientRect();
      if (!position) return;
      const x = event.clientX - position.left;
      const y = event.clientY - position.top;

      // Default parameters per layer type
      const defaultParams = {
        Linear: { in_features: 128, out_features: 64 },
        Conv2d: { in_channels: 3, out_channels: 16, kernel_size: 3 },
        ReLU: {},
        Dropout: { p: 0.5 },
      };

      const newId = `${type}-${Date.now()}`;
      const newNode: Node = {
        id: newId,
        type: 'layerNode',
        position: { x, y },
        data: {
          label: type,
          params: defaultParams[type] || {},
          onEdit: () => setSelectedNode(nodes.find(n => n.id === newId) || null),
        },
        style: { width: 180 },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [nodes, setNodes]
  );

  // --- Handle connections ---
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges]
  );

  // --- Select node ---
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  // --- Delete node ---
  const onDeleteNode = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
      setEdges((eds) => eds.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
      setSelectedNode(null);
    }
  }, [selectedNode, setNodes, setEdges]);

  // --- Update node params ---
  const updateNodeParams = useCallback(
    (nodeId: string, newParams: any) => {
      setNodes((nds) =>
        nds.map((n) => {
          if (n.id === nodeId) {
            return { ...n, data: { ...n.data, params: { ...n.data.params, ...newParams } } };
          }
          return n;
        })
      );
      // Update selected node too
      setSelectedNode((prev) => {
        if (prev && prev.id === nodeId) {
          return { ...prev, data: { ...prev.data, params: { ...prev.data.params, ...newParams } } };
        }
        return prev;
      });
    },
    [setNodes]
  );

  // --- Sidebar drag handler ---
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div style={{ display: 'flex', height: '700px', gap: '1rem', background: '#1a1a2e', borderRadius: '8px', padding: '0.5rem' }}>
      {/* Sidebar */}
      <div style={{ width: '150px', background: '#242438', padding: '1rem', borderRadius: '6px' }}>
        <h3 style={{ color: '#eee', fontSize: '0.9rem', marginTop: 0 }}>Layers</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {['Linear', 'Conv2d', 'ReLU', 'Dropout'].map((type) => (
            <div
              key={type}
              draggable
              onDragStart={(e) => onDragStart(e, type)}
              style={{
                background: '#2a2a3a',
                color: '#eee',
                padding: '0.5rem',
                borderRadius: '4px',
                cursor: 'grab',
                textAlign: 'center',
                border: '1px solid #444',
              }}
            >
              {type}
            </div>
          ))}
        </div>
        <div style={{ marginTop: '1rem', fontSize: '0.7rem', color: '#666' }}>
          Drag layers to canvas
        </div>
      </div>

      {/* Canvas */}
      <div style={{ flex: 1, height: '100%' }} ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          nodeTypes={layerNodeTypes}
          fitView
        >
          <Controls />
          <Background color="#333" gap={12} size={1} />
          <Panel position="top-right">
            <button
              onClick={() => setNodes([])}
              style={{
                background: '#e94560',
                color: '#fff',
                border: 'none',
                padding: '4px 8px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.8rem',
              }}
            >
              Clear All
            </button>
          </Panel>
        </ReactFlow>
      </div>

      {/* Property Panel (simple modal) */}
      {selectedNode && (
        <div
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: '#1e1e32',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid #444',
            minWidth: '300px',
            maxWidth: '400px',
            zIndex: 1000,
            color: '#eee',
          }}
        >
          <h3 style={{ marginTop: 0 }}>Edit {selectedNode.data.label}</h3>
          {Object.entries(selectedNode.data.params || {}).map(([key, value]) => (
            <div key={key} style={{ marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <label style={{ minWidth: '80px', color: '#aaa' }}>{key}:</label>
              <input
                type="text"
                value={String(value)}
                onChange={(e) => {
                  const newVal = isNaN(Number(e.target.value)) ? e.target.value : Number(e.target.value);
                  updateNodeParams(selectedNode.id, { [key]: newVal });
                }}
                style={{
                  background: '#2a2a3a',
                  color: '#eee',
                  border: '1px solid #444',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  flex: 1,
                }}
              />
            </div>
          ))}
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
            <button
              onClick={() => setSelectedNode(null)}
              style={{ background: '#555', color: '#fff', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}
            >
              Close
            </button>
            <button
              onClick={onDeleteNode}
              style={{ background: '#e94560', color: '#fff', border: 'none', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}
            >
              Delete
            </button>
          </div>
        </div>
      )}
      {selectedNode && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'rgba(0,0,0,0.5)',
            zIndex: 999,
          }}
          onClick={() => setSelectedNode(null)}
        />
      )}
    </div>
  );
}

export default ModelBuilder;