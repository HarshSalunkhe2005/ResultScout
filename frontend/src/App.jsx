import { useState, useEffect } from 'react';
import { createClient } from '@supabase/supabase-js';
import { Search, Loader2 } from 'lucide-react';
import './index.css';

// Initialize Supabase client
// We use env vars for Netlify deployment
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

  useEffect(() => {
    fetchResults();
  }, [yearFilter, deptFilter, semFilter]);

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
      setError('Failed to fetch results. Ensure Supabase is configured and table exists.');
    } finally {
      setLoading(false);
    }
  };

  const filteredResults = results.filter(
    (res) =>
      res.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      res.prn.toString().includes(searchTerm)
  );

  return (
    <div>
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">ResultScout</h1>
          <p className="dashboard-subtitle">Live Academic Performance Dashboard</p>
        </div>
      </div>

      <div className="glass-panel">
        <div className="filters-container">
          <div className="filter-group">
            <label className="filter-label">Search Student</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Search style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} size={18} />
              <input
                type="text"
                className="filter-input"
                placeholder="Name or PRN..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ paddingLeft: '40px', width: '100%', boxSizing: 'border-box' }}
              />
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
          <div style={{ padding: '2rem', color: '#ef4444', textAlign: 'center' }}>
            {error}
          </div>
        ) : loading ? (
          <div className="loading-spinner">
            <Loader2 className="spinner" />
          </div>
        ) : filteredResults.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No results found for the selected criteria.
          </div>
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
                        <span className={`gpa-badge ${isNa ? 'gpa-na' : ''}`}>
                          {row.gpa}
                        </span>
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
