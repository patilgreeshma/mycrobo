import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  ArrowLeft, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  GitBranch, 
  Clock, 
  Terminal,
  Activity
} from 'lucide-react';
import ScanProgress from '../components/ScanProgress';
import api from '../services/api';

export default function Scan() {
  const { scanId } = useParams();
  const navigate = useNavigate();

  const [scanInfo, setScanInfo] = useState(null);
  const [progress, setProgress] = useState({
    scan_id: scanId,
    status: 'pending',
    progress: 0.05,
    current_step: 'Initializing scan...',
    total_issues: 0,
  });
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [isWsConnected, setIsWsConnected] = useState(false);

  const wsRef = useRef(null);
  const pollTimerRef = useRef(null);

  // Helper to add activity log entry
  const addLog = (message) => {
    if (!message) return;
    setLogs((prev) => {
      if (prev.length > 0 && prev[prev.length - 1].message === message) {
        return prev;
      }
      return [...prev.slice(-30), { time: new Date().toLocaleTimeString(), message }];
    });
  };

  // Initial fetch for scan metadata
  useEffect(() => {
    let isMounted = true;

    const fetchInitial = async () => {
      try {
        const data = await api.getScan(scanId);
        if (isMounted && data && data.scan) {
          setScanInfo(data.scan);
          setProgress((prev) => ({
            ...prev,
            status: data.scan.status,
            progress: data.scan.progress || prev.progress,
            current_step: data.scan.current_step || prev.current_step,
            total_issues: data.scan.total_issues || 0,
          }));

          if (data.scan.status === 'complete') {
            navigate(`/report/${scanId}`, { replace: true });
          } else if (data.scan.status === 'failed') {
            setError(data.scan.error_message || 'The scan encountered an unexpected error.');
          }
        }
      } catch (err) {
        console.error('Failed to load scan info:', err);
      }
    };

    fetchInitial();

    return () => {
      isMounted = false;
    };
  }, [scanId, navigate]);

  // Connect WebSocket and setup Polling fallback
  useEffect(() => {
    let isMounted = true;

    const handleUpdate = (data) => {
      if (!isMounted || !data) return;

      setProgress((prev) => ({
        ...prev,
        ...data,
      }));

      if (data.current_step) {
        addLog(data.current_step);
      }

      if (data.status === 'complete') {
        setTimeout(() => {
          if (isMounted) {
            navigate(`/report/${scanId}`);
          }
        }, 1200);
      } else if (data.status === 'failed') {
        setError(data.error_message || 'The scan encountered an unexpected error.');
      }
    };

    // 1. Try WebSocket
    try {
      const ws = api.connectWebSocket(
        scanId,
        (data) => {
          setIsWsConnected(true);
          handleUpdate(data);
        },
        () => {
          setIsWsConnected(false);
        }
      );
      wsRef.current = ws;
    } catch (e) {
      console.warn('WebSocket connection not available, falling back to polling', e);
      setIsWsConnected(false);
    }

    // 2. Polling fallback every 2.5s
    const poll = async () => {
      try {
        const data = await api.getScanProgress(scanId);
        if (data && isMounted) {
          handleUpdate(data);
          if (data.status === 'complete' || data.status === 'failed') {
            clearInterval(pollTimerRef.current);
          }
        }
      } catch (e) {
        console.warn('Polling error:', e);
      }
    };

    pollTimerRef.current = setInterval(poll, 2500);
    poll(); // Run immediately

    return () => {
      isMounted = false;
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch (_) {}
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, [scanId, navigate]);

  const isComplete = progress.status === 'complete';
  const isFailed = progress.status === 'failed';

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header & Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800/80 gap-4">
        <div className="flex items-center space-x-3">
          <Link
            to="/"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <GitBranch className="w-4 h-4 text-cyan-400" />
              <h1 className="text-xl font-bold text-white">
                {scanInfo?.repo_name || scanInfo?.repo_url || 'Auditing Repository'}
              </h1>
            </div>
            <div className="flex items-center space-x-3 text-xs text-slate-500 mt-1">
              <span>Scan ID: {scanId}</span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <span className={`w-2 h-2 rounded-full ${isWsConnected ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
                <span>{isWsConnected ? 'Live Stream' : 'Syncing'}</span>
              </span>
            </div>
          </div>
        </div>

        {isComplete && (
          <Link
            to={`/report/${scanId}`}
            className="inline-flex items-center justify-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-cyan-500/20 transition-all"
          >
            <FileText className="w-4 h-4" />
            <span>View Full Report</span>
          </Link>
        )}
      </div>

      {/* Main Scan Progress Area */}
      {!isFailed ? (
        <div className="space-y-8">
          <ScanProgress progress={progress} />

          {/* Activity Log Console */}
          <div className="max-w-2xl mx-auto bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-3">
              <div className="flex items-center space-x-2 text-xs font-semibold text-slate-300">
                <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                <span>Agent Execution Feed</span>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">
                {logs.length} events logged
              </span>
            </div>
            <div className="space-y-1.5 font-mono text-xs max-h-48 overflow-y-auto pr-2">
              {logs.length === 0 ? (
                <div className="text-slate-600 italic">Waiting for agent events...</div>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="flex items-start space-x-2 text-slate-400">
                    <span className="text-slate-600 select-none">[{log.time}]</span>
                    <span className="text-cyan-400 select-none">›</span>
                    <span className="text-slate-300">{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Error / Failed State */
        <div className="max-w-2xl mx-auto p-8 rounded-2xl bg-rose-950/20 border border-rose-900/50 text-center space-y-4">
          <div className="w-14 h-14 bg-rose-900/40 text-rose-400 rounded-2xl flex items-center justify-center mx-auto border border-rose-800/60">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-white">Scan Failed</h2>
          <p className="text-sm text-rose-300 max-w-md mx-auto">
            {error || 'The audit pipeline was unable to complete the analysis for this repository.'}
          </p>
          <div className="pt-4 flex justify-center space-x-3">
            <Link
              to="/"
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors"
            >
              Return Home
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
