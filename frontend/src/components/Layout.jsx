import { Link } from 'react-router-dom';

export function Layout({ children }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true">
            聽
          </span>
          <span>英語跟讀</span>
        </Link>
      </header>
      <main className="page">{children}</main>
    </div>
  );
}
