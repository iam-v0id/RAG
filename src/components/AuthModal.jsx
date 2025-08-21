import { useState } from 'react'

export default function AuthModal({ onLogin, error }) {
  const [username, setUsername] = useState('demo_user')
  const [password, setPassword] = useState('')
  return (
    <div className="modal">
      <div className="modal-content">
        <h2>Login to RAG System</h2>
        <form onSubmit={(e) => { e.preventDefault(); onLogin(username.trim(), password.trim()) }}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">Username</label>
            <input id="username" className="form-control" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="demo_user" required />
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input id="password" type="password" className="form-control" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" required />
          </div>
          <button type="submit" className="btn btn--primary btn--full-width">Login</button>
        </form>
        <div className={`error-message ${error ? '' : 'hidden'}`}>{error}</div>
      </div>
    </div>
  )
}


