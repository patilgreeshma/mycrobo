import { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  Download, 
  FileText, 
  Code2, 
  Layers, 
  Search, 
  Filter, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle, 
  GitBranch, 
  Cpu,
  SlidersHorizontal
} from 'lucide-react';
import api from '../services/api';
import StatCards, { SeverityBar, AgentBreakdown } from '../components/StatCards';
import IssueCard from '../components/IssueCard';

export default function Report() {
  const { scanId } = useParams();

  const [scan, setScan] = useState(null);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [selectedSeverity, setSelectedSeverity] = useState('all');

  const fetchReport = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getScan(scanId);
      if (data && data.scan) {
        setScan(data.scan);
        setIssues(data.issues || []);
      } else {
        throw new Error('Scan not found');
      }
    } catch (err) {
      console.error('Error fetching report:', err);
      setError(err.message || 'Failed to load report');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [scanId]);

  // Export handlers
  const handleExport = async (format) => {
    try {
      setExporting(true);
      if (format === 'markdown') {
        const res = await api.getReport(scanId, 'markdown');
        const blob = new Blob([res.content || ''], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `codesentinel-report-${scan?.repo_name || scanId}.md`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        const res = await api.getReport(scanId, 'json');
        const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `codesentinel-report-${scan?.repo_name || scanId}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Export error:', err);
      alert(`Export failed: ${err.message}`);
    } finally {
      setExporting(false);
    }
  };

  // Filtered issues computation
  const filteredIssues = useMemo(() => {
    return issues.filter((issue) => {
      // Agent filter
      if (selectedAgent !== 'all' && issue.agent_type !== selectedAgent) {
        return false;
      }
      // Severity filter
      if (selectedSeverity !== 'all' && issue.severity !== selectedSeverity) {
        return false;
      }
      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const inTitle = (issue.title || '').toLowerCase().includes(q);
        const inDesc = (issue.description || '').toLowerCase().includes(q);
        const inFile = (issue.file_path || '').toLowerCase().includes(q);
        const inCat = (issue.category || '').toLowerCase().includes(q);
        if (!inTitle && !inDesc && !inFile && !inCat) {
          return false;
        }
      }
      return true;
    });
  }, [issues, selectedAgent, selectedSeverity, searchQuery]);

  // Count helper for tabs
  const getAgentCount = (type) => {
    if (type === 'all') return issues.length;
    return issues.filter((i) => i.agent_type === type).length;
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center space-y-4">
        <RefreshCw className="w-10 h-10 text-cyan-400 animate-spin mx-auto" />
        <h2 className="text-xl font-semibold text-white">Loading Audit Report...</h2>
        <p className="text-sm text-slate-400">Aggregating multi-agent findings and security metrics</p>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center space-y-4">
        <AlertCircle className="w-12 h-12 text-rose-400 mx-auto" />
        <h2 className="text-2xl font-bold text-white">Report Unavailable</h2>
        <p className="text-slate-400 text-sm">{error || 'Could not find this scan report.'}</p>
        <Link
          to="/"
          className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Home</span>
        </Link>
      </div>
    );
  }

  const agentTabs = [
    { key: 'all', label: 'All Findings' },
    { key: 'security', label: 'Security' },
    { key: 'quality', label: 'Code Quality' },
    { key: 'completeness', label: 'Completeness' },
    { key: 'dependency', label: 'Dependencies' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Breadcrumb & Actions Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800/80 gap-4">
        <div className="flex items-center space-x-3">
          <Link
            to="/"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Return to Dashboard"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <GitBranch className="w-4 h-4 text-cyan-400" />
              <h1 className="text-xl sm:text-2xl font-bold text-white">
                {scan.repo_name || scan.repo_url || 'Codebase Audit Report'}
              </h1>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mt-1">
              <span>Audited on {new Date(scan.completed_at || scan.created_at).toLocaleDateString()}</span>
              <span>•</span>
              <span>{scan.total_files || 0} source files</span>
              {scan.total_lines > 0 && (
                <>
                  <span>•</span>
                  <span>{scan.total_lines.toLocaleString()} lines of code</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Export Buttons */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={() => handleExport('markdown')}
            disabled={exporting}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-200 text-xs font-semibold hover:text-white transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-cyan-400" />
            <span>Markdown</span>
          </button>
          <button
            onClick={() => handleExport('json')}
            disabled={exporting}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 text-slate-200 text-xs font-semibold hover:text-white transition-colors"
          >
            <FileText className="w-3.5 h-3.5 text-indigo-400" />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {/* Tech Stack Banner */}
      {(scan.languages || scan.frameworks) && (
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-4 flex flex-wrap items-center gap-4 text-xs">
          <div className="flex items-center space-x-1.5 text-slate-400 font-semibold uppercase tracking-wider">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>Architecture Detected:</span>
          </div>
          {scan.languages && (
            <div className="flex flex-wrap items-center gap-1.5">
              {Object.entries(scan.languages).map(([lang, count]) => (
                <span
                  key={lang}
                  className="px-2.5 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[11px]"
                >
                  {lang} ({count} files)
                </span>
              ))}
            </div>
          )}
          {scan.frameworks && scan.frameworks.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pl-2 border-l border-slate-800">
              {scan.frameworks.map((fw) => (
                <span
                  key={fw}
                  className="px-2.5 py-0.5 rounded-full bg-indigo-950/40 border border-indigo-800/50 text-indigo-300 text-[11px]"
                >
                  {fw}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stat Cards */}
      <StatCards scan={scan} />

      {/* Visual Distributions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SeverityBar scan={scan} />
        <AgentBreakdown issues={issues} />
      </div>

      {/* Issues Explorer Section */}
      <section className="space-y-4 pt-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center space-x-2">
              <Layers className="w-5 h-5 text-cyan-400" />
              <span>Audit Findings & Actionable Fixes</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {filteredIssues.length} of {issues.length} detected problems
            </p>
          </div>

          {/* Search Input */}
          <div className="relative w-full lg:w-72">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search file, title, snippet..."
              className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-900/60 border border-slate-800/80 rounded-xl p-3">
          {/* Agent Category Tabs */}
          <div className="flex items-center space-x-1 overflow-x-auto pb-1 sm:pb-0">
            {agentTabs.map((tab) => {
              const count = getAgentCount(tab.key);
              const isActive = selectedAgent === tab.key;
              return (
                <button
                  key={tab.key}
                  onClick={() => setSelectedAgent(tab.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors flex items-center space-x-1.5 ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  <span>{tab.label}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                      isActive ? 'bg-cyan-500/30 text-cyan-200' : 'bg-slate-800 text-slate-500'
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Severity Dropdown Filter */}
          <div className="flex items-center space-x-2 self-end sm:self-center">
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-300 px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>
        </div>

        {/* Issue Cards Feed */}
        {filteredIssues.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/30 border border-slate-800/60 rounded-xl space-y-2">
            <CheckCircle className="w-10 h-10 text-emerald-500 mx-auto" />
            <h3 className="text-base font-semibold text-white">No Issues Match Filters</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Try resetting your search query or selecting a different agent category or severity level.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredIssues.map((issue) => (
              <IssueCard key={issue.id} issue={issue} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
