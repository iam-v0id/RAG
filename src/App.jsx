import { useEffect, useMemo, useState } from 'react'
import Header from './components/Header'
import NavTabs from './components/NavTabs'
import AuthModal from './components/AuthModal'
import SearchTab from './components/SearchTab'
import UploadTab from './components/UploadTab'
import AdminTab from './components/AdminTab'
// Remove demo data; rely on backend only
import { extractTextFromPdf } from './lib/utils'

export default function App() {
  const [currentUser, setCurrentUser] = useState(null)
  const [currentTab, setCurrentTab] = useState('search')
  const [documents, setDocuments] = useState([])
  const [queryHistory, setQueryHistory] = useState([])
  const [queryLogs, setQueryLogs] = useState([])
  const [authError, setAuthError] = useState('')
  // hybridWeight removed (Pinecone-only backend)
  const [results, setResults] = useState(null)

  const [uploadState, setUploadState] = useState({ visible: false, progress: 0, text: '', recentDocs: [] })
  const [metadataState, setMetadataState] = useState({ visible: false, auto: {}, fields: { title: '', author: '', category: '', department: '', confidentiality_level: '', year: new Date().getFullYear(), tags: '' } })
  const [processingTimeout, setProcessingTimeout] = useState(null)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    // Fetch server-side document registry
    ;(async () => {
      try {
        const res = await fetch('/api/docs')
        if (res.ok) {
          const data = await res.json()
          const items = Array.isArray(data.items) ? data.items : []
          setDocuments(items)
          setUploadState(s => ({ ...s, recentDocs: items.slice(0, 10) }))
        }
      } catch (_) {}
    })()
    setQueryHistory(prev => (prev.length ? prev : []))
    return () => { if (processingTimeout) clearTimeout(processingTimeout) }
  }, [])

  const metrics = useMemo(() => ({
    total_documents: documents.length,
    total_chunks: documents.reduce((sum, d) => sum + (d.chunk_count || 0), 0),
    total_storage_mb: (documents.reduce((sum, d) => sum + d.file_size, 0) / 1024 / 1024).toFixed(2),
    average_query_time_ms: 1250,
    total_queries_today: queryLogs.length,
    system_uptime: '2d 14h 32m',
  }), [documents, queryLogs])

  function handleLogin(username, password) {
    if (username === 'demo_user' && password === 'password') {
      setCurrentUser({ id: 'user_001', username: 'demo_user', email: 'demo@company.com', role: 'admin', department: 'Engineering' })
      setAuthError('')
    } else {
      setAuthError('Invalid username or password. Use demo_user / password')
    }
  }

  function handleLogout() {
    setCurrentUser(null)
    setAuthError('')
  }

  async function onSearch(query, filters) {
    const start = Date.now()
    setResults({ loading: true })
    let backendOk = false
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, filters }),
      })
      if (res.ok) {
        const data = await res.json()
        const responseTime = data.responseTime ?? (Date.now() - start)
        const chunksProcessed = data.chunksProcessed ?? (data.sources || []).reduce((s, d) => s + (d.chunk_count || 0), 0)
        setResults({ ready: true, loading: false, answer: data.answer, sources: data.sources || [], responseTime, chunksProcessed })
        const historyItem = { id: Date.now(), query, filters, resultCount: (data.sources || []).length, timestamp: new Date().toISOString() }
        setQueryHistory(prev => [historyItem, ...prev].slice(0, 10))
        const logItem = { id: Date.now(), query, filters, responseTime, timestamp: new Date().toISOString(), user: currentUser ? currentUser.username : 'anonymous' }
        setQueryLogs(prev => [logItem, ...prev].slice(0, 50))
        backendOk = true
      }
    } catch (_) {
      // ignore and fall back
    }
    if (backendOk) return

    // No fallback; surface error state
    setResults({ ready: true, loading: false, answer: 'Search backend unavailable. Please ensure the API is running.', sources: [], responseTime: Date.now() - start, chunksProcessed: 0 })
  }

  function onHistoryClick(_item) {}

  function onClearFilters() {
    // Reset filters if needed
  }

  function validateFiles(files) {
    const validTypes = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    const maxSize = 10 * 1024 * 1024
    const valid = []
    for (const f of files) {
      if (!validTypes.includes(f.type)) { alert(`Invalid file type: ${f.name}. Only PDF, TXT, and DOCX files are allowed.`); continue }
      if (f.size > maxSize) { alert(`File too large: ${f.name}. Maximum size is 10MB.`); continue }
      valid.push(f)
    }
    return valid
  }

  async function onFiles(files) {
    const valid = validateFiles(files)
    for (const f of valid) {
      await uploadSingleFile(f)
    }
  }

  async function uploadSingleFile(file) {
    setUploadState(s => ({ ...s, visible: true, text: `Uploading ${file.name}...`, progress: 0 }))
    // For demo, only handle small .txt content inline; for PDFs/DOCX you'd extract text server-side
    let textContent = ''
    if (file.type === 'text/plain') {
      textContent = await file.text()
    } else if (file.type === 'application/pdf') {
      try {
        textContent = await extractTextFromPdf(file)
      } catch (_) {
        textContent = 'Failed to extract text from PDF on client.'
      }
    } else {
      // Placeholder: In a real app, upload the file to storage and extract text via backend
      textContent = 'Content extraction for non-txt files is not implemented in this demo.'
    }
    setUploadState(s => ({ ...s, text: 'Preparing metadata...' }))
    setUploadState(s => ({ ...s, visible: false }))
    showMetadataModal(file, textContent)
  }

  function showMetadataModal(file, textContent) {
    const sizeLabel = typeof file.size === 'number' ? (file.size/1024/1024).toFixed(2) + ' MB' : 'Unknown'
    const filename = typeof file.name === 'string' ? file.name : 'untitled'
    const filetype = typeof file.type === 'string' ? file.type : 'unknown'
    const auto = { filename, size: sizeLabel, type: filetype, uploadDate: new Date().toLocaleDateString(), author: 'Not detected', __textContent: textContent || '' }
    setMetadataState({ visible: true, auto, fields: { title: filename.replace(/\.[^/.]+$/, ''), author: '', category: '', department: '', confidentiality_level: '', year: new Date().getFullYear(), tags: '' } })
  }

  function setMetadataField(field, value) {
    setMetadataState(s => ({ ...s, fields: { ...s.fields, [field]: value } }))
  }

  function onCancelMetadata() {
    setMetadataState(s => ({ ...s, visible: false }))
  }

  function onSubmitMetadata() {
    const f = metadataState.fields
    const newDoc = {
      id: `doc_${Date.now()}`,
      filename: `${f.title}.pdf`,
      original_filename: `${f.title}.pdf`,
      file_size: 512000,
      file_type: 'pdf',
      uploaded_at: new Date().toISOString(),
      processed_at: null,
      title: f.title,
      author: f.author || 'Unknown',
      category: f.category,
      department: f.department,
      confidentiality_level: f.confidentiality_level,
      year: parseInt(f.year),
      tags: f.tags.split(',').map(t => t.trim()).filter(Boolean),
      language: 'en',
      page_count: 5,
      chunk_count: 0,
      processing_status: 'processing',
      error_message: null,
      content_preview: 'Document is being processed...'
    }
    setMetadataState(s => ({ ...s, visible: false }))
    ;(async () => {
      try {
        const content = metadataState.auto.__textContent || ''
        const res = await fetch('/api/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: newDoc.id,
            title: newDoc.title,
            department: newDoc.department,
            category: newDoc.category,
            year: newDoc.year,
            content,
            chunk_count: 0,
          })
        })
        if (!res.ok) throw new Error('Upload failed')
        const data = await res.json()
        newDoc.processing_status = 'completed'
        newDoc.processed_at = new Date().toISOString()
        newDoc.chunk_count = 1
        newDoc.content_preview = content.slice(0, 300)
        setDocuments(d => [newDoc, ...d])
        setUploadState(s => ({ ...s, recentDocs: [newDoc, ...documents].slice(0, 10) }))
        alert('Uploaded and ingested into Pinecone successfully.')
      } catch (e) {
        alert('Upload failed. Check backend logs.')
      }
    })()
  }

  function onDeleteDoc(docId) {
    console.log('Delete button clicked for docId:', docId)
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      console.log('Delete cancelled by user')
      return
    }
    console.log('Proceeding with delete...')
    ;(async () => {
      try {
        const deleteUrl = `/api/docs?id=${encodeURIComponent(docId)}`
        console.log('Making DELETE request to:', deleteUrl)
        const res = await fetch(deleteUrl, { method: 'DELETE' })
        console.log('Delete response status:', res.status)
        console.log('Delete response ok:', res.ok)
        
        if (!res.ok) {
          const errorText = await res.text()
          console.error('Delete failed with status:', res.status, 'Error:', errorText)
          throw new Error(`Delete failed: ${res.status} ${errorText}`)
        }
        
        const data = await res.json()
        console.log('Delete response data:', data)
        
        if (data && data.ok) {
          setDocuments(docs => docs.filter(d => d.id !== docId))
          setUploadState(s => ({ ...s, recentDocs: s.recentDocs.filter(d => d.id !== docId) }))
          console.log('Document deleted successfully from state')
          alert('Document deleted from Pinecone successfully')
        } else {
          console.error('Delete response indicates failure:', data)
          alert('Failed to delete document. Please try again.')
        }
      } catch (e) {
        console.error('Delete error:', e)
        alert(`Delete failed: ${e.message}`)
      }
    })()
  }

  async function onRefreshDocs() {
    if (isRefreshing) return // Prevent multiple simultaneous refreshes
    
    setIsRefreshing(true)
    try {
      const res = await fetch('/api/docs')
      if (res.ok) {
        const data = await res.json()
        const items = Array.isArray(data.items) ? data.items : []
        setDocuments(items)
        setUploadState(s => ({ ...s, recentDocs: items.slice(0, 10) }))
        console.log(`Refreshed ${items.length} documents from backend`)
      } else {
        console.error('Failed to refresh documents:', res.status, res.statusText)
        alert('Failed to refresh documents. Please try again.')
      }
    } catch (error) {
      console.error('Error refreshing documents:', error)
      alert('Error refreshing documents. Please check your connection.')
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <div>
      {!currentUser && (
        <AuthModal onLogin={handleLogin} error={authError} />
      )}
      <div id="app" className={!currentUser ? 'hidden' : ''}>
        <Header username={currentUser?.username || ''} onLogout={handleLogout} />
        <NavTabs currentTab={currentTab} onSwitch={setCurrentTab} />

        {currentTab === 'search' && (
          <SearchTab onSearch={onSearch} results={results} queryHistory={queryHistory} onHistoryClick={onHistoryClick} onClearFilters={onClearFilters} />
        )}
        {currentTab === 'upload' && (
          <UploadTab onFiles={onFiles} uploadState={{ ...uploadState, recentDocs: documents.slice(0, 10) }} metadataState={metadataState} onCancelMetadata={onCancelMetadata} onSubmitMetadata={onSubmitMetadata} setMetadataField={setMetadataField} />
        )}
        {currentTab === 'admin' && (
          <AdminTab metrics={metrics} documents={documents} onDeleteDoc={onDeleteDoc} queryLogs={queryLogs} onRefresh={onRefreshDocs} isRefreshing={isRefreshing} />
        )}
      </div>
    </div>
  )
}
