import { formatFileSize } from '../lib/utils'

export default function AdminTab({ metrics, documents, onDeleteDoc, queryLogs, onRefresh, isRefreshing }) {
  return (
    <div id="admin-tab" className="tab-content active">
      <div className="container">
        <div className="admin-section">
          <h2>Admin Panel</h2>
          <div className="metrics-grid">
            <div className="metric-card"><h3>{metrics.total_documents}</h3><p>Total Documents</p></div>
            <div className="metric-card"><h3>{metrics.total_chunks}</h3><p>Document Chunks</p></div>
            <div className="metric-card"><h3>{metrics.total_storage_mb} MB</h3><p>Storage Used</p></div>
            <div className="metric-card"><h3>{metrics.average_query_time_ms} ms</h3><p>Avg Query Time</p></div>
            <div className="metric-card"><h3>{metrics.total_queries_today}</h3><p>Queries Today</p></div>
            <div className="metric-card"><h3>{metrics.system_uptime}</h3><p>System Uptime</p></div>
          </div>
          <div className="admin-section-content">
            <div className="section-header">
              <h3>Document Management ({documents.length} documents)</h3>
              <button 
                className="btn btn--outline btn--sm" 
                onClick={onRefresh}
                disabled={isRefreshing}
              >
                {isRefreshing ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
            <div id="admin-documents" className="admin-documents">
              {documents.length === 0 ? (
                <div className="no-documents">
                  <p>No documents found. Upload some documents to get started.</p>
                </div>
              ) : (
                documents.map(doc => (
                  <div key={doc.id} className="admin-document-item">
                    <div className="admin-document-info">
                      <div className="admin-document-title">{doc.title}</div>
                      <div className="admin-document-meta">
                        <span>ID: {doc.id}</span>
                        <span>Size: {formatFileSize(doc.file_size)}</span>
                        <span>Chunks: {doc.chunk_count}</span>
                        <span>Department: {doc.department}</span>
                        <span>Uploaded: {new Date(doc.uploaded_at).toLocaleDateString()}</span>
                        <span className={`status status--${doc.processing_status === 'completed' ? 'success' : 'warning'}`}>{doc.processing_status}</span>
                      </div>
                    </div>
                    <div className="admin-document-actions">
                      <button className="btn btn--outline btn--sm" disabled>View (Disabled)</button>
                      <button className="btn btn--outline btn--sm" onClick={() => onDeleteDoc(doc.id)}>Delete</button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="admin-section-content">
            <h3>Query Logs</h3>
            <div id="query-logs" className="query-logs">
              {queryLogs.length === 0 && (
                <p style={{ color: 'var(--color-text-secondary)' }}>No query logs available</p>
              )}
              {queryLogs.slice(0, 20).map(log => (
                <div key={log.id} className="log-item">
                  <div className="log-query">{log.query}</div>
                  <div className="log-meta">{new Date(log.timestamp).toLocaleString()} • {log.user} • {log.responseTime}ms • Filters: {Object.keys(log.filters).filter(k => log.filters[k]).join(', ') || 'None'}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="admin-section-content">
            <h3>System Status</h3>
            <div className="status-grid">
              <div className="status-item"><span className="status-label">Vector Index</span><span className="status status--success">Healthy</span></div>
              <div className="status-item"><span className="status-label">Search Engine</span><span className="status status--success">Active</span></div>
              <div className="status-item"><span className="status-label">Document Processing</span><span className="status status--success">Online</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


