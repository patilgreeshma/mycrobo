import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  Shield, 
  Sparkles, 
  CheckCircle2, 
  Package, 
  Clock, 
  ArrowRight, 
  RefreshCw, 
  FileCode, 
  GitBranch, 
  AlertTriangle 
} from 'lucide-react';
import ScanForm from '../components/ScanForm';
import api from '../services/api';

export default function Home() {
  const navigate = useNavigate();
  const [recentScans, setRecentScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRecentScans = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listScans(10);
      setRecentScans(data?.scans || []);
    } catch (err) {
      console.error('Failed to fetch recent scans:', err);
      setError('Unable to load previous scans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentScans();
  }, []);

  const handleScanCreated = (scan) => {
    if (scan && scan.id) {
      navigate(`/scan/${scan.id}`);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'complete':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-900/40 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Complete
          </span>
        );
      case 'scanning':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-900/40 text-cyan-400 border border-cyan-800/60 animate-pulse">
            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
            Scanning
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-900/40 text-rose-400 border border-rose-800/60">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300">
            <Clock className="w-3 h-3 mr-1" />
            Queued
          </span>
        );
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-16">
      {/* Hero Section */}
      <section className="text-center space-y-6 max-w-3xl mx-auto pt-4">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-semibold tracking-wide uppercase">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Next-Gen Autonomous Security & Quality Review</span>
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-tight">
          Audit any codebase. <br />
          <span className="bg-gradient-to-r from-cyan-400 via-sky-400 to-indigo-400 bg-clip-text text-transparent">
            Catch risks before production.
          </span>
        </h1>
        <p className="text-lg text-slate-400 leading-relaxed max-w-2xl mx-auto">
          Architecture-agnostic agent team that deeply scans your repositories for security flaws, AI-generated slop, incomplete logic, and dependency risks with actionable fixes.
        </p>
      </section>

      {/* Main Scan Input Card */}
      <section className="max-w-2xl mx-auto">
        <ScanForm onScanCreated={handleScanCreated} />
      </section>

      {/* Feature Pillar Highlights */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 hover:border-slate-700/80 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mb-4">
            <Shield className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Security Auditor</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Identifies hardcoded API tokens, SQL injections, insecure deserialization, SSRF vectors, and unsafe configs.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 hover:border-slate-700/80 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-4">
            <Sparkles className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Quality & AI Slop</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Detects hallucinated patterns, dead code, duplicated logic, redundant comments, and excessive cyclomatic complexity.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 hover:border-slate-700/80 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-4">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Completeness</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Surfaces lingering TODOs, empty error catch blocks, unhandled promise rejections, missing input validations, and stubs.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 hover:border-slate-700/80 transition-colors">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4">
            <Package className="w-5 h-5" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Dependency Risks</h3>
          <p className="text-sm text-slate-400 leading-relaxed">
            Cross-references package manifests (npm, pip, cargo, maven, go) against known security advisories and outdated versions.
          </p>
        </div>
      </section>

      {/* Recent Scans Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div>
            <h2 className="text-xl font-bold text-white">Recent Audits</h2>
            <p className="text-sm text-slate-400">Past repository analysis reports and live scanning tasks</p>
          </div>
          <button
            onClick={fetchRecentScans}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 rounded-lg border border-slate-700/50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {error && (
          <div className="p-4 bg-rose-950/20 border border-rose-900/40 rounded-xl text-rose-400 text-sm">
            {error}
          </div>
        )}

        {!loading && recentScans.length === 0 && (
          <div className="text-center py-12 bg-slate-900/30 border border-slate-800/60 rounded-xl space-y-2">
            <FileCode className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-slate-400 font-medium">No audit scans run yet</p>
            <p className="text-slate-500 text-xs">Enter a GitHub repository URL or upload a ZIP archive above to start your first audit.</p>
          </div>
        )}

        {recentScans.length > 0 && (
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden divide-y divide-slate-800/60">
            {recentScans.map((scan) => {
              const targetUrl = scan.status === 'complete' ? `/report/${scan.id}` : `/scan/${scan.id}`;
              const formattedDate = scan.created_at ? new Date(scan.created_at).toLocaleString() : 'Just now';

              return (
                <Link
                  key={scan.id}
                  to={targetUrl}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-4 hover:bg-slate-800/40 transition-colors group"
                >
                  <div className="flex items-start sm:items-center space-x-3 mb-2 sm:mb-0">
                    <div className="p-2 rounded-lg bg-slate-800/80 text-cyan-400 mt-1 sm:mt-0">
                      <GitBranch className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-white group-hover:text-cyan-400 transition-colors">
                          {scan.repo_name || scan.repo_url || 'Codebase Scan'}
                        </span>
                        {getStatusBadge(scan.status)}
                      </div>
                      <div className="flex items-center space-x-4 text-xs text-slate-500 mt-1">
                        <span>ID: {scan.id.slice(0, 8)}...</span>
                        <span>{formattedDate}</span>
                        {scan.total_files > 0 && <span>{scan.total_files} files</span>}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4">
                    {scan.status === 'complete' && (
                      <div className="flex items-center space-x-3 text-right">
                        <div>
                          <div className="text-xs text-slate-400">Score</div>
                          <div className={`text-base font-bold ${
                            scan.health_score >= 80 ? 'text-emerald-400' :
                            scan.health_score >= 60 ? 'text-amber-400' : 'text-rose-400'
                          }`}>
                            {scan.health_score}/100
                          </div>
                        </div>
                        <div className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300">
                          {scan.total_issues ?? 0} issues
                        </div>
                      </div>
                    )}
                    <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-cyan-400 transition-transform group-hover:translate-x-1" />
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
