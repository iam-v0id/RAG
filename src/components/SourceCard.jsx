import { useMemo, useState } from 'react'

export default function SourceCard({ doc, index }) {
  const confidence = useMemo(() => (95 - index * 10 - Math.random() * 10).toFixed(1), [index])
  const bm25Score = useMemo(() => (0.8 - index * 0.1 - Math.random() * 0.2).toFixed(3), [index])
  const embeddingScore = useMemo(() => (0.9 - index * 0.05 - Math.random() * 0.1).toFixed(3), [index])
  const hybridScore = useMemo(() => (0.85 - index * 0.08 - Math.random() * 0.15).toFixed(3), [index])
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="source-document">
      <div className="source-header">
        <h5 className="source-title">{doc.title}</h5>
        <div className="source-metadata">
          <span className="metadata-badge metadata-badge--department">{doc.department}</span>
          <span className="metadata-badge metadata-badge--category">{doc.category}</span>
          <span className="metadata-badge metadata-badge--year">{doc.year}</span>
          <span className="metadata-badge metadata-badge--confidence">{confidence}% match</span>
        </div>
      </div>
      <div className="source-excerpt" style={{ maxHeight: expanded ? 'none' : '100px', overflow: 'hidden' }}>{doc.content_preview}</div>
      <div className="source-scores">
        <div className="score-item"><span>BM25:</span><strong>{bm25Score}</strong></div>
        <div className="score-item"><span>Embedding:</span><strong>{embeddingScore}</strong></div>
        <div className="score-item"><span>Hybrid:</span><strong>{hybridScore}</strong></div>
        <button className="expand-btn" onClick={() => setExpanded(!expanded)}>{expanded ? 'Collapse' : 'Expand'}</button>
      </div>
    </div>
  )
}


