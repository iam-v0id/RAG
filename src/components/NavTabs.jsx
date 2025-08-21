export default function NavTabs({ currentTab, onSwitch }) {
  const tabs = [
    { id: 'search', label: 'Search & Query' },
    { id: 'upload', label: 'Upload Documents' },
    { id: 'admin', label: 'Admin Panel' },
  ]
  return (
    <nav className="nav-tabs">
      <div className="container">
        <div className="tabs">
          {tabs.map(t => (
            <button key={t.id} className={`tab-btn ${currentTab === t.id ? 'active' : ''}`} onClick={() => onSwitch(t.id)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
    </nav>
  )
}


