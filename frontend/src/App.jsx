import { useState, useEffect, useRef } from 'react';
import { createClient } from '@supabase/supabase-js';
import { Search, Loader2, Play, Square, Terminal } from 'lucide-react';
import './index.css';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const supabase = supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;

function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [yearFilter, setYearFilter] = useState('2026');
  const [deptFilter, setDeptFilter] = useState('CSE');
  const [semFilter, setSemFilter] = useState('3');
  const [error, setError] = useState(null);

  // Scraper State
  const [scraperState, setScraperState] = useState({
    is_running: false,
    current_prn: 0,
    total_prns: 200,
    logs: []
  });
  const terminalRef = useRef(null);

  useEffect(() => {
    fetchResults();
  }, [yearFilter, deptFilter, semFilter]);

  // Poll Scraper Status
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5000/api/status');
        if (res.ok) {
          const data = await res.json();
          setScraperState(data);
          // If it just finished or is running, maybe refresh data occasionally
        }
      } catch (err) {
        // API offline
      }
    };
    const interval = setInterval(pollStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [scraperState.logs]);

  const fetchResults = async () => {
    if (!supabase) {
      setError('Supabase credentials not configured in .env.local');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    setError(null);
    try {
      const { data, error } = await supabase
        .from('results')
        .select('*')
        .eq('year', parseInt(yearFilter))
        .eq('department', deptFilter)
        .eq('semester', parseInt(semFilter))
        .order('gpa', { ascending: false });

      if (error) throw error;
      setResults(data || []);
    } catch (err) {
      console.error('Error fetching data:', err.message);
      setError('Failed to fetch results.');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      await fetch('http://127.0.0.1:5000/api/start', { method: 'POST' });
    } catch (err) {
      alert("Failed to connect to local Python API. Make sure 'python api.py' is running!");
    }
  };

  const handleStop = async () => {
    try {
      await fetch('http://127.0.0.1:5000/api/stop', { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  const filteredResults = results.filter(
    (res) =>
      res.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      res.prn.toString().includes(searchTerm)
  );

  const progressPercent = Math.min(100, Math.round((scraperState.current_prn / scraperState.total_prns) * 100)) || 0;

  return (
    <div>
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">ResultScout</h1>
          <p className="dashboard-subtitle">Live Academic Performance Dashboard</p>
        </div>
      </div>

      {/* Control Panel */}
      <div className="glass-panel" style={{ display: 'flex', gap: '2rem' }}>
        <div style={{ flex: 1 }}>
          <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 0 }}>
            <Terminal size={20} className="text-accent" /> Control Panel
          </h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            Control the local Python scraper directly from the browser.
          </p>
          
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
            <button 
              onClick={handleStart} 
              disabled={scraperState.is_running}
              style={{
                background: scraperState.is_running ? 'rgba(255,255,255,0.1)' : 'var(--accent)',
                color: 'white', border: 'none', padding: '0.75rem 1.5rem', borderRadius: '8px',
                display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: scraperState.is_running ? 'not-allowed' : 'pointer',
                fontWeight: 600, transition: '0.2s'
              }}
            >
              <Play size={18} /> Start Scraping
            </button>
            <button 
              onClick={handleStop}
              disabled={!scraperState.is_running}
              style={{
                background: !scraperState.is_running ? 'rgba(255,255,255,0.1)' : 'rgba(239, 68, 68, 0.2)',
                color: !scraperState.is_running ? 'rgba(255,255,255,0.3)' : '#ef4444',
                border: '1px solid ' + (!scraperState.is_running ? 'transparent' : 'rgba(239, 68, 68, 0.5)'),
                padding: '0.75rem 1.5rem', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '0.5rem',
                cursor: !scraperState.is_running ? 'not-allowed' : 'pointer', fontWeight: 600, transition: '0.2s'
              }}
            >
              <Square size={18} /> Stop
            </button>
            <button 
              onClick={fetchResults}
              style={{
                background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--panel-border)', 
                padding: '0.75rem 1.5rem', borderRadius: '8px', cursor: 'pointer', fontWeight: 600
              }}
            >
              Refresh Table
            </button>
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.875rem' }}>
              <span>Progress: {scraperState.current_prn} / {scraperState.total_prns} PRNs</span>
              <span>{progressPercent}%</span>
            </div>
            <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ 
                width: `${progressPercent}%`, height: '100%', background: 'var(--accent)', 
                transition: 'width 0.3s ease' 
              }}></div>
            </div>
          </div>
        </div>

        {/* Live Terminal */}
        <div style={{ flex: 1, background: '#000', borderRadius: '8px', padding: '1rem', border: '1px solid var(--panel-border)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ fontSize: '0.75rem', color: '#666', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.5rem' }}>Live Terminal</div>
          <div ref={terminalRef} style={{ flex: 1, overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.875rem', color: '#10b981', maxHeight: '200px' }}>
            {scraperState.logs.length === 0 ? (
              <span style={{ color: '#666' }}>Waiting for logs...</span>
            ) : (
              scraperState.logs.map((log, i) => <div key={i}>{log}</div>)
            )}
          </div>
        </div>
      </div>

      <div className="glass-panel">
        <div className="filters-container">
          <div className="filter-group">
            <label className="filter-label">Search Student</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} size={18} />
              <input type="text" className="filter-input" placeholder="Name or PRN..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} style={{ paddingLeft: '40px', width: '100%', boxSizing: 'border-box' }} />
            </div>
          </div>
          <div className="filter-group">
            <label className="filter-label">Department</label>
            <select className="filter-select" value={deptFilter} onChange={(e) => setDeptFilter(e.target.value)}>
              <option value="CSE">CSE</option>
              <option value="AIML">AIML</option>
              <option value="IT">IT</option>
            </select>
          </div>
          <div className="filter-group">
            <label className="filter-label">Semester</label>
            <select className="filter-select" value={semFilter} onChange={(e) => setSemFilter(e.target.value)}>
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
              <option value="4">4</option>
              <option value="5">5</option>
              <option value="6">6</option>
              <option value="7">7</option>
              <option value="8">8</option>
            </select>
          </div>
          <div className="filter-group">
            <label className="filter-label">Year</label>
            <select className="filter-select" value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
              <option value="2026">2026</option>
              <option value="2025">2025</option>
              <option value="2024">2024</option>
            </select>
          </div>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        {error ? (
          <div style={{ padding: '2rem', color: '#ef4444', textAlign: 'center' }}>{error}</div>
        ) : loading ? (
          <div className="loading-spinner"><Loader2 className="spinner" /></div>
        ) : filteredResults.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>No results found for the selected criteria.</div>
        ) : (
          <div className="table-container">
            <table className="results-table">
              <thead>
                <tr>
                  <th>PRN</th>
                  <th>Name</th>
                  <th>Seat Number</th>
                  <th>GPA</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((row) => {
                  const isNa = row.gpa === 'TNG' || row.gpa === 'N/A' || row.gpa === 'Not Found';
                  return (
                    <tr key={row.prn}>
                      <td style={{ fontWeight: 500 }}>{row.prn}</td>
                      <td>{row.name}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{row.seat}</td>
                      <td>
                        <span className={`gpa-badge ${isNa ? 'gpa-na' : ''}`}>{row.gpa}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
