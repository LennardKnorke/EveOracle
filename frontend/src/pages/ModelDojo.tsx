import React from 'react';
import ModelBuilder from '../components/ModelBuilder';
import './ModelDojo.css'; // optional

function ModelDojo() {
    return (
        
        <div style={{ padding: '20px' }}>
            <h2 style={{ color: '#eee' }}>Model Dojo</h2>
            <h2>NOTHING TO SEE HERE! (yet)</h2>;
            <p style={{ color: '#aaa' }}>Drag layers from the sidebar onto the canvas to build your neural network.</p>
            <ModelBuilder />
        </div>
    );
}

export default ModelDojo;