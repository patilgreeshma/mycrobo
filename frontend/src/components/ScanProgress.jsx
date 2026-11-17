import { Shield, Loader2 } from 'lucide-react';

export default function ScanProgress({ progress }) {
  if (!progress) return null;

  const pct = Math.round((progress.progress || 0) * 100);
  const step = progress.current_step || 'Initializing...';
  const issuesFound = progress.total_issues || 0;

  const steps = [
    { key: 'cloning', label: 'Clone Repository', threshold: 0.05 },
    { key: 'analyzing', label: 'Analyze Structure', threshold: 0.10 },
    { key: 'security', label: 'Security Scan', threshold: 0.35 },
    { key: 'quality', label: 'Quality Analysis', threshold: 0.55 },
    { key: 'completeness', label: 'Completeness Check', threshold: 0.70 },
    { key: 'dependencies', label: 'Dependency Audit', threshold: 0.80 },
    { key: 'enhance', label: 'AI Enhancement', threshold: 0.90 },
    { key: 'report', label: 'Generate Report', threshold: 1.0 },
  ];

  return (
    <div className="max-w-2xl mx-auto">
      <div className="glass-card glow-border p-8">
        {/* Animated shield icon */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            <div className="w-20 h-20 bg-indigo-600/20 rounded-2xl flex items-center justify-center animate-pulse-slow">
              <Shield className="w-10 h-10 text-indigo-400" />
            </div>
            <div className="absolute -top-1 -right-1 w-6 h-6 bg-indigo-500 rounded-full flex items-center justify-center">
              <Loader2 className="w-3 h-3 text-white animate-spin" />
            </div>
          </div>
        </div>

        <h2 className="text-xl font-semibold text-center text-white mb-2">
          Scanning Your Codebase
        </h2>
        <p className="text-sm text-slate-400 text-center mb-6">{step}</p>

        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex justify-between text-xs text-slate-500 mb-2">
            <span>Progress</span>
            <span>{pct}%</span>
          </div>
          <div className="h-2.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full progress-bar-animated rounded-full transition-all duration-700 ease-out"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Step indicators */}
        <div className="space-y-2">
          {steps.map((s, i) => {
            const pctVal = progress.progress || 0;
            const isDone = pctVal > s.threshold;
            const isCurrent = !isDone && (i === 0 || pctVal > steps[i - 1].threshold);

            return (
              <div key={s.key} className="flex items-center space-x-3">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                  isDone ? 'bg-green-500/20 text-green-400' :
                  isCurrent ? 'bg-indigo-500/20 text-indigo-400' :
                  'bg-slate-800 text-slate-600'
                }`}>
                  {isDone ? '✓' : isCurrent ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (i + 1)}
                </div>
                <span className={`text-sm ${
                  isDone ? 'text-slate-400' :
                  isCurrent ? 'text-white font-medium' :
                  'text-slate-600'
                }`}>
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Issues found counter */}
        {issuesFound > 0 && (
          <div className="mt-6 text-center">
            <span className="text-sm text-slate-400">
              Issues found so far: <span className="text-indigo-400 font-semibold">{issuesFound}</span>
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
