export default function Header({ username, onLogout }) {
  return (
    <header className="header">
      <div className="container flex justify-between items-center">
        <h1 className="header-title">RAG Document System</h1>
        <div className="header-actions">
          <span className="user-info">Welcome, <span>{username}</span></span>
          <button onClick={onLogout} className="btn btn--outline btn--sm">Logout</button>
        </div>
      </div>
    </header>
  )
}


