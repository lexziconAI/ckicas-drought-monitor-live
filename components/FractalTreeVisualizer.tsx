import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface FractalNode {
  id: string;
  content: string;
  score: number;
  status: string;
  children: FractalNode[];
}

interface FractalTreeVisualizerProps {
  tree: FractalNode | null;
  activePath: string[];
}

const FractalTreeVisualizer: React.FC<FractalTreeVisualizerProps> = ({ tree, activePath }) => {
  if (!tree) return null;

  return (
    <div className="w-full h-64 bg-slate-950 rounded-lg border border-slate-800 overflow-hidden relative p-4">
      <div className="absolute top-2 right-2 text-[10px] text-emerald-500 font-mono animate-pulse">
        FRACTAL ENGINE ACTIVE
      </div>
      <div className="flex flex-col items-center gap-4 h-full overflow-y-auto custom-scrollbar">
        <TreeNode node={tree} activePath={activePath} depth={0} />
      </div>
    </div>
  );
};

const TreeNode: React.FC<{ node: FractalNode; activePath: string[]; depth: number }> = ({ node, activePath, depth }) => {
  const isActive = activePath.includes(node.id);
  const isLeaf = node.children.length === 0;

  return (
    <div className="flex flex-col items-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`
          relative z-10 px-3 py-2 rounded-lg border text-xs max-w-[200px] text-center transition-all duration-300
          ${isActive 
            ? 'bg-emerald-900/50 border-emerald-500/50 text-emerald-200 shadow-[0_0_15px_rgba(16,185,129,0.3)]' 
            : 'bg-slate-900/50 border-slate-700 text-slate-400 opacity-60'}
        `}
      >
        <div className="font-medium truncate">{node.content}</div>
        {node.score > 0 && (
          <div className={`text-[10px] mt-1 ${node.score > 0.7 ? 'text-emerald-400' : 'text-amber-400'}`}>
            Score: {node.score.toFixed(2)}
          </div>
        )}
      </motion.div>

      {!isLeaf && (
        <div className="flex gap-4 mt-4 relative">
          {/* Connecting Lines (Simplified) */}
          <div className="absolute top-[-16px] left-1/2 -translate-x-1/2 w-px h-4 bg-slate-700" />
          
          {node.children.map((child) => (
            <div key={child.id} className="relative pt-2">
               {/* Horizontal connector logic would go here for a perfect tree, 
                   but for this MVP we just stack them or use flex gap */}
              <TreeNode node={child} activePath={activePath} depth={depth + 1} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FractalTreeVisualizer;
