import { formatFileSize } from '../lib/utils'

export default function UploadTab({ onFiles, uploadState, metadataState, onCancelMetadata, onSubmitMetadata, setMetadataField }) {
  const fileInputId = 'file-input-react'
  return (
    <div id="upload-tab" className="tab-content active">
      <div className="container">
        <div className="upload-section">
          <h2>Upload Documents</h2>
          <div className="upload-container">
            <div id="drop-zone" className="drop-zone" onDragOver={(e) => { e.preventDefault(); }} onDrop={(e) => { e.preventDefault(); const files = Array.from(e.dataTransfer.files); if (files.length) onFiles(files) }}>
              <div className="drop-zone-content">
                <div className="upload-icon">📄</div>
                <p>Drag and drop files here or <button className="link-btn" onClick={(e) => { e.preventDefault(); document.getElementById(fileInputId)?.click() }}>browse</button></p>
                <small>Supported formats: PDF, TXT, DOCX (max 10MB)</small>
              </div>
              <input type="file" id={fileInputId} className="hidden" multiple accept=".pdf,.txt,.docx" onChange={(e) => { const files = Array.from(e.target.files || []); if (files.length) onFiles(files) }} />
            </div>
            <div id="upload-progress" className={`upload-progress ${uploadState.visible ? '' : 'hidden'}`}>
              <div className="progress-bar">
                <div id="progress-fill" className="progress-fill" style={{ width: `${uploadState.progress}%` }}></div>
              </div>
              <p id="progress-text">{uploadState.text}</p>
            </div>
          </div>

          {metadataState.visible && (
            <div id="metadata-modal" className="modal">
              <div className="modal-content">
                <div className="modal-header">
                  <h3>Edit Document Metadata</h3>
                  <button className="btn btn--outline btn--sm" onClick={onCancelMetadata}>×</button>
                </div>
                <form onSubmit={(e) => { e.preventDefault(); onSubmitMetadata() }}>
                  <div className="modal-body">
                    <div className="metadata-preview">
                      <h4>Auto-Extracted Information</h4>
                      <div id="auto-metadata" className="auto-metadata">
                        {Object.entries(metadataState.auto).map(([k, v]) => (
                          <div key={k} className="auto-metadata-item">
                            <div className="auto-metadata-label">{k.charAt(0).toUpperCase() + k.slice(1)}:</div>
                            <div className="auto-metadata-value">{v}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="metadata-fields">
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-title">Title</label>
                        <input id="doc-title" className="form-control" value={metadataState.fields.title} onChange={(e) => setMetadataField('title', e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-author">Author</label>
                        <input id="doc-author" className="form-control" value={metadataState.fields.author} onChange={(e) => setMetadataField('author', e.target.value)} />
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-category">Category</label>
                        <select id="doc-category" className="form-control" value={metadataState.fields.category} onChange={(e) => setMetadataField('category', e.target.value)} required>
                          <option value="">Select Category</option>
                          <option value="Policy">Policy</option>
                          <option value="FAQ">FAQ</option>
                          <option value="Research">Research</option>
                          <option value="Manual">Manual</option>
                          <option value="Contract">Contract</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-department">Department</label>
                        <select id="doc-department" className="form-control" value={metadataState.fields.department} onChange={(e) => setMetadataField('department', e.target.value)} required>
                          <option value="">Select Department</option>
                          <option value="HR">HR</option>
                          <option value="Engineering">Engineering</option>
                          <option value="Finance">Finance</option>
                          <option value="Legal">Legal</option>
                          <option value="Marketing">Marketing</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-confidentiality">Confidentiality Level</label>
                        <select id="doc-confidentiality" className="form-control" value={metadataState.fields.confidentiality_level} onChange={(e) => setMetadataField('confidentiality_level', e.target.value)} required>
                          <option value="">Select Level</option>
                          <option value="Public">Public</option>
                          <option value="Internal">Internal</option>
                          <option value="Confidential">Confidential</option>
                          <option value="Restricted">Restricted</option>
                        </select>
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-year">Year</label>
                        <input type="number" id="doc-year" className="form-control" min={2020} max={2030} value={metadataState.fields.year} onChange={(e) => setMetadataField('year', e.target.value)} required />
                      </div>
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-tags">Tags (comma-separated)</label>
                        <input id="doc-tags" className="form-control" placeholder="tag1, tag2, tag3" value={metadataState.fields.tags} onChange={(e) => setMetadataField('tags', e.target.value)} />
                      </div>
                    </div>
                  </div>
                  <div className="modal-footer form-actions">
                    <button type="button" className="btn btn--secondary" onClick={onCancelMetadata}>Cancel</button>
                    <button type="submit" className="btn btn--primary">Save & Ingest</button>
                  </div>
                </form>
              </div>
            </div>
          )}

          <div className="upload-history">
            <h3>Recently Uploaded Documents</h3>
            <div id="upload-history-list" className="document-list">
              {uploadState.recentDocs.map(doc => (
                <div key={doc.id} className="document-item">
                  <div className="document-info">
                    <div className="document-title">{doc.title}</div>
                    <div className="document-meta">
                      <span>Chunks: {doc.chunk_count || 0}</span>
                      <span>Department: {doc.department}</span>
                      <span>Category: {doc.category}</span>
                      <span className={`status status--${doc.processing_status === 'completed' ? 'success' : (doc.processing_status === 'processing' ? 'warning' : 'error')}`}>{doc.processing_status}</span>
                    </div>
                  </div>
                  <div className="document-actions">
                    <button className="btn btn--outline btn--sm">View</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


