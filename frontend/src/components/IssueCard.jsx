import { useState } from 'react';
import { ChevronDown, ChevronUp, FileCode, Lightbulb, Wrench } from 'lucide-react';
import SeverityBadge from './SeverityBadge';

export default function IssueCard({ issue }) {
  const [expanded, setExpanded] = useState(false);

  const agentLabels = {
    security: { label: 'Security', emoji: '🔒' },
    quality: { label: 'Quality', emoji: '📐' },
    completeness: { label: 'Completeness', emoji: '🧩' },
    dependency: { label: 'Dependency', emoji: '📦' },
  };

  const agent = agentLabels[issue.agent_type] || { label: issue.agent_type, emoji: '🔍' };

  return (
    <div className="glass-card overflow-hidden hover:border-slate-700 transition-colors">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-start justify-between text-left hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex-1 min-w-0 mr-4">
          <div className="flex items-center space-x-3 mb-2">
            <SeverityBadge severity={issue.severity} />
            <span className="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded-full">
              {agent.emoji} {agent.label}
            </span>
            {issue.category && (
              <span className="text-xs text-slate-600">{issue.category.replace(/_/g, ' ')}</span>
            )}
          </div>
          <h3 className="text-sm font-medium text-slate-200 mb-1">{issue.title}</h3>
          {issue.file_path && (
            <div className="flex items-center space-x-1 text-xs text-slate-500">
              <FileCode className="w-3 h-3" />
              <span className="font-mono">
                {issue.file_path}
                {issue.line_start && `:${issue.line_start}`}
                {issue.line_end && issue.line_end !== issue.line_start && `-${issue.line_end}`}
              </span>
            </div>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-slate-500 flex-shrink-0 mt-1" />
        ) : (
          <ChevronDown className="w-5 h-5 text-slate-500 flex-shrink-0 mt-1" />
        )}
      </button>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-slate-800 p-4 space-y-4 bg-slate-900/30">
          {/* Description */}
          <p className="text-sm text-slate-300 leading-relaxed">{issue.description}</p>

          {/* Code Snippet */}
          {issue.code_snippet && (
            <div>
              <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wider">Code</p>
              <pre className="bg-slate-950 border border-slate-800 rounded-lg p-4 overflow-x-auto">
                <code className="text-sm text-slate-300 font-mono whitespace-pre">{issue.code_snippet}</code>
              </pre>
            </div>
          )}

          {/* LLM Explanation */}
          {issue.explanation && (
            <div className="bg-indigo-500/5 border border-indigo-500/20 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Lightbulb className="w-4 h-4 text-indigo-400" />
                <p className="text-xs text-indigo-400 font-medium uppercase tracking-wider">Why This Matters</p>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{issue.explanation}</p>
            </div>
          )}

          {/* Suggestion */}
          {issue.suggestion && (
            <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Wrench className="w-4 h-4 text-green-400" />
                <p className="text-xs text-green-400 font-medium uppercase tracking-wider">Recommended Fix</p>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{issue.suggestion}</p>
            </div>
          )}

          {/* Code Diff (Before/After) */}
          {issue.original_code && issue.suggested_code && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <p className="text-xs text-red-400 mb-2 font-medium uppercase tracking-wider">❌ Before</p>
                <pre className="bg-red-500/5 border border-red-500/20 rounded-lg p-3 overflow-x-auto">
                  <code className="text-xs text-slate-300 font-mono whitespace-pre">{issue.original_code}</code>
                </pre>
              </div>
              <div>
                <p className="text-xs text-green-400 mb-2 font-medium uppercase tracking-wider">✅ After</p>
                <pre className="bg-green-500/5 border border-green-500/20 rounded-lg p-3 overflow-x-auto">
                  <code className="text-xs text-slate-300 font-mono whitespace-pre">{issue.suggested_code}</code>
                </pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
