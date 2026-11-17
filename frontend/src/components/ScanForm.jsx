import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Upload, ArrowRight, Loader2 } from 'lucide-react';
import api from '../services/api';

export default function ScanForm() {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('url'); // 'url' or 'upload'
  const fileRef = useRef(null);
  const navigate = useNavigate();

  const handleUrlSubmit = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setLoading(true);
    setError('');

    try {
      const result = await api.createScan(repoUrl.trim());
      navigate(`/scan/${result.scan_id}`);
    } catch (err) {
      setError(err.message || 'Failed to start scan');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.zip')) {
      setError('Please upload a ZIP file');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await api.uploadScan(file);
      navigate(`/scan/${result.scan_id}`);
    } catch (err) {
      setError(err.message || 'Failed to upload file');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Mode Toggle */}
      <div className="flex justify-center mb-6">
        <div className="bg-slate-900 rounded-lg p-1 flex space-x-1">
          <button
            onClick={() => setMode('url')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              mode === 'url'
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Search className="w-4 h-4 inline mr-2" />
            GitHub URL
          </button>
          <button
            onClick={() => setMode('upload')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
              mode === 'upload'
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Upload className="w-4 h-4 inline mr-2" />
            Upload ZIP
          </button>
        </div>
      </div>

      {/* URL Input */}
      {mode === 'url' && (
        <form onSubmit={handleUrlSubmit} className="relative">
          <div className="glass-card glow-border p-2 flex items-center">
            <div className="pl-4 pr-2 text-slate-500">
              <Search className="w-5 h-5" />
            </div>
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/username/repository"
              className="flex-1 bg-transparent border-none outline-none text-white placeholder-slate-500 py-3 px-2 text-lg"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !repoUrl.trim()}
              className="btn-primary flex items-center space-x-2 mr-1"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <span>Scan</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>
      )}

      {/* File Upload */}
      {mode === 'upload' && (
        <div
          onClick={() => !loading && fileRef.current?.click()}
          className="glass-card glow-border p-12 text-center cursor-pointer hover:border-indigo-400/50 transition-all"
        >
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            onChange={handleFileUpload}
            className="hidden"
          />
          {loading ? (
            <Loader2 className="w-12 h-12 text-indigo-400 animate-spin mx-auto mb-4" />
          ) : (
            <Upload className="w-12 h-12 text-slate-500 mx-auto mb-4" />
          )}
          <p className="text-lg text-slate-300 mb-2">
            {loading ? 'Uploading...' : 'Drop your ZIP file here or click to browse'}
          </p>
          <p className="text-sm text-slate-500">Supports any project — Python, JavaScript, Java, Go, PHP, and more</p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Example URLs */}
      {mode === 'url' && !loading && (
        <div className="mt-6 text-center">
          <p className="text-sm text-slate-500 mb-3">Try an example:</p>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              'https://github.com/pallets/flask',
              'https://github.com/expressjs/express',
              'https://github.com/tiangolo/fastapi',
            ].map((url) => (
              <button
                key={url}
                onClick={() => setRepoUrl(url)}
                className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white px-3 py-1.5 rounded-full transition-all"
              >
                {url.split('/').slice(-2).join('/')}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
