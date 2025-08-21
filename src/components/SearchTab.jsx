import { useState } from 'react'
import SourceCard from './SourceCard'

export default function SearchTab({ onSearch, results, queryHistory, onHistoryClick, onClearFilters }) {
  const [query, setQuery] = useState('')
  const [department, setDepartment] = useState('')
  const [category, setCategory] = useState('')
  const [year, setYear] = useState('')

  return (
    <div id="search-tab" className="tab-content active">
      <div className="container">
        <div className="search-section">
          <div className="search-container">
            <h2>Search Documents</h2>
            <form className="search-form" onSubmit={(e) => { e.preventDefault(); onSearch(query, { department, category, year }) }}>
              <div className="search-input-group">
                <input className="form-control search-input" placeholder="Ask a question about your documents..." value={query} onChange={(e) => setQuery(e.target.value)} required />
                <button type="submit" className="btn btn--primary search-btn">Search</button>
              </div>
            </form>
            <div className="filters-panel">
              <h3>Filters</h3>
              <div className="filters-grid">
                <div className="form-group">
                  <label className="form-label" htmlFor="department-filter">Department</label>
                  <select id="department-filter" className="form-control" value={department} onChange={(e) => setDepartment(e.target.value)}>
                    <option value="">All Departments</option>
                    <option value="HR">HR</option>
                    <option value="Engineering">Engineering</option>
                    <option value="Finance">Finance</option>
                    <option value="Legal">Legal</option>
                    <option value="Marketing">Marketing</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="category-filter">Category</label>
                  <select id="category-filter" className="form-control" value={category} onChange={(e) => setCategory(e.target.value)}>
                    <option value="">All Categories</option>
                    <option value="Policy">Policy</option>
                    <option value="FAQ">FAQ</option>
                    <option value="Research">Research</option>
                    <option value="Manual">Manual</option>
                    <option value="Contract">Contract</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="year-filter">Year</label>
                  <select id="year-filter" className="form-control" value={year} onChange={(e) => setYear(e.target.value)}>
                    <option value="">All Years</option>
                    <option value="2024">2024</option>
                    <option value="2023">2023</option>
                    <option value="2022">2022</option>
                  </select>
                </div>
                
              </div>
              <button onClick={() => { setDepartment(''); setCategory(''); setYear(''); onClearFilters() }} className="btn btn--secondary btn--sm">Clear Filters</button>
            </div>
          </div>

          <div id="results-section" className={`results-section ${results ? '' : 'hidden'}`}>
            {!results?.ready && (
              <div id="search-loading" className={`loading-spinner ${results?.loading ? '' : 'hidden'}`}>
                <div className="spinner"></div>
                <p>Searching documents...</p>
              </div>
            )}

            {results?.ready && (
              <div id="search-results">
                <div className="results-header">
                  <h3>Search Results</h3>
                  <div className="performance-metrics">
                    <span id="response-time" className="metric">Response time: <strong>{results.responseTime}ms</strong></span>
                    <span id="chunks-processed" className="metric">Chunks processed: <strong>{results.chunksProcessed}</strong></span>
                  </div>
                </div>
                <div id="answer-section" className="answer-section">
                  <h4>Generated Answer</h4>
                  <div id="generated-answer" className="answer-text">{results.answer}</div>
                </div>
                <div id="sources-section" className="sources-section">
                  <h4>Source Documents</h4>
                  <div id="source-documents" className="source-documents">
                    {results.sources.map((doc, i) => (<SourceCard key={doc.id} doc={doc} index={i} />))}
                    {results.sources.length === 0 && (
                      <p style={{ color: 'var(--color-text-secondary)' }}>No source documents found matching your query and filters.</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="query-history">
            <h3>Recent Queries</h3>
            <div id="query-history-list" className="query-list">
              {queryHistory.map(item => (
                <div key={item.id} className="query-item" onClick={() => onHistoryClick(item)}>
                  <div className="query-text">{item.query}</div>
                  <div className="query-meta">{new Date(item.timestamp).toLocaleString()} • {item.resultCount} results {Object.keys(item.filters).filter(k => item.filters[k]).length > 0 ? '• Filtered' : ''}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


