export default function SeverityBadge({ severity, size = 'md' }) {
  const config = {
    critical: { label: 'Critical', bg: 'bg-red-500/15', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-500' },
    high:     { label: 'High',     bg: 'bg-orange-500/15', text: 'text-orange-400', border: 'border-orange-500/30', dot: 'bg-orange-500' },
    medium:   { label: 'Medium',   bg: 'bg-yellow-500/15', text: 'text-yellow-400', border: 'border-yellow-500/30', dot: 'bg-yellow-500' },
    low:      { label: 'Low',      bg: 'bg-green-500/15', text: 'text-green-400', border: 'border-green-500/30', dot: 'bg-green-500' },
    info:     { label: 'Info',     bg: 'bg-blue-500/15', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-500' },
  };

  const c = config[severity] || config.info;
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-1';

  return (
    <span className={`inline-flex items-center ${sizeClasses} rounded-full border ${c.bg} ${c.text} ${c.border} font-medium`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} mr-1.5`}></span>
      {c.label}
    </span>
  );
}
