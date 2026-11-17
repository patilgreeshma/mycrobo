import { ShieldAlert, Code2, Puzzle, Package } from 'lucide-react';

export default function StatCards({ scan }) {
  if (!scan) return null;

  const cards = [
    {
      title: 'Health Score',
      value: `${Math.round(scan.health_score || 0)}/100`,
      color: (scan.health_score || 0) >= 80 ? 'text-green-400' : (scan.health_score || 0) >= 50 ? 'text-yellow-400' : 'text-red-400',
      bgColor: (scan.health_score || 0) >= 80 ? 'bg-green-500/10' : (scan.health_score || 0) >= 50 ? 'bg-yellow-500/10' : 'bg-red-500/10',
      subtitle: (scan.health_score || 0) >= 80 ? 'Good' : (scan.health_score || 0) >= 50 ? 'Needs Work' : 'Critical',
    },
    {
      title: 'Total Issues',
      value: scan.total_issues || 0,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10',
      subtitle: `${scan.total_files || 0} files scanned`,
    },
    {
      title: 'Critical & High',
      value: (scan.critical_count || 0) + (scan.high_count || 0),
      color: (scan.critical_count || 0) > 0 ? 'text-red-400' : 'text-orange-400',
      bgColor: (scan.critical_count || 0) > 0 ? 'bg-red-500/10' : 'bg-orange-500/10',
      subtitle: `${scan.critical_count || 0} critical, ${scan.high_count || 0} high`,
    },
    {
      title: 'Languages',
      value: scan.languages ? Object.keys(scan.languages).length : 0,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      subtitle: scan.languages ? Object.keys(scan.languages).slice(0, 3).join(', ') : 'N/A',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <div key={card.title} className={`glass-card p-5 ${card.bgColor} border-transparent`}>
          <p className="text-sm text-slate-400 mb-1">{card.title}</p>
          <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
          <p className="text-xs text-slate-500 mt-1">{card.subtitle}</p>
        </div>
      ))}
    </div>
  );
}

export function SeverityBar({ scan }) {
  if (!scan || !scan.total_issues) return null;

  const total = scan.total_issues;
  const segments = [
    { count: scan.critical_count || 0, color: 'bg-red-500', label: 'Critical' },
    { count: scan.high_count || 0, color: 'bg-orange-500', label: 'High' },
    { count: scan.medium_count || 0, color: 'bg-yellow-500', label: 'Medium' },
    { count: scan.low_count || 0, color: 'bg-green-500', label: 'Low' },
    { count: scan.info_count || 0, color: 'bg-blue-500', label: 'Info' },
  ].filter(s => s.count > 0);

  return (
    <div className="glass-card p-5">
      <p className="text-sm text-slate-400 mb-3">Issue Distribution</p>
      <div className="flex h-3 rounded-full overflow-hidden bg-slate-800 mb-3">
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`${seg.color} transition-all duration-500`}
            style={{ width: `${(seg.count / total) * 100}%` }}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-4">
        {segments.map((seg, i) => (
          <div key={i} className="flex items-center space-x-2">
            <div className={`w-2.5 h-2.5 rounded-full ${seg.color}`} />
            <span className="text-xs text-slate-400">{seg.label}: {seg.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AgentBreakdown({ issues }) {
  if (!issues || !issues.length) return null;

  const agents = [
    { type: 'security', label: 'Security', icon: ShieldAlert, color: 'text-red-400' },
    { type: 'quality', label: 'Code Quality', icon: Code2, color: 'text-yellow-400' },
    { type: 'completeness', label: 'Completeness', icon: Puzzle, color: 'text-blue-400' },
    { type: 'dependency', label: 'Dependencies', icon: Package, color: 'text-purple-400' },
  ];

  return (
    <div className="glass-card p-5">
      <p className="text-sm text-slate-400 mb-4">Issues by Agent</p>
      <div className="space-y-3">
        {agents.map(({ type, label, icon: Icon, color }) => {
          const count = issues.filter(i => i.agent_type === type).length;
          const pct = issues.length > 0 ? (count / issues.length) * 100 : 0;
          return (
            <div key={type}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-2">
                  <Icon className={`w-4 h-4 ${color}`} />
                  <span className="text-sm text-slate-300">{label}</span>
                </div>
                <span className="text-sm font-medium text-slate-200">{count}</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${
                    type === 'security' ? 'bg-red-500' :
                    type === 'quality' ? 'bg-yellow-500' :
                    type === 'completeness' ? 'bg-blue-500' : 'bg-purple-500'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
