import { useState, useRef, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import "./ProfileSelector.css";

export default function ProfileSelector() {
  const { user, isAuthenticated, logout, openAuthModal } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    function handleKeyDown(e) {
      if (e.key === "Escape" && isOpen) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const initials = user?.username
    ? user.username.slice(0, 2).toUpperCase()
    : "G";

  return (
    <div className="profile-selector" ref={ref}>
      {isAuthenticated ? (
        <button
          type="button"
          className="profile-selector__trigger profile-selector__trigger--authenticated"
          onClick={() => setIsOpen(!isOpen)}
          aria-haspopup="true"
          aria-expanded={isOpen}
          title={`Signed in as ${user.username}`}
        >
          <span className="profile-selector__avatar profile-selector__avatar--user">
            {initials}
          </span>
          <span className="profile-selector__label">{user.username}</span>
          <span
            className={`profile-selector__chevron ${
              isOpen ? "profile-selector__chevron--open" : ""
            }`}
            aria-hidden="true"
          >
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </span>
        </button>
      ) : (
        <div className="profile-selector__guest-wrap">
          <button
            type="button"
            className="profile-selector__trigger profile-selector__trigger--guest"
            onClick={() => setIsOpen(!isOpen)}
            aria-haspopup="true"
            aria-expanded={isOpen}
            title="Account & Personalization"
          >
            <span className="profile-selector__avatar profile-selector__avatar--anonymous">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </span>
            <span className="profile-selector__label">Guest</span>
            <span
              className={`profile-selector__chevron ${
                isOpen ? "profile-selector__chevron--open" : ""
              }`}
              aria-hidden="true"
            >
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="6 9 12 15 18 9" />
              </svg>
            </span>
          </button>

          <button
            type="button"
            className="profile-selector__signin-quick-btn"
            onClick={() => openAuthModal("login")}
            title="Sign in to save your shopping memory"
          >
            Sign In
          </button>
        </div>
      )}

      {isOpen && (
        <div className="profile-selector__dropdown" role="menu">
          {isAuthenticated ? (
            <>
              <div className="profile-selector__user-card">
                <div className="profile-selector__avatar profile-selector__avatar--large">
                  {initials}
                </div>
                <div className="profile-selector__user-info">
                  <div className="profile-selector__username">{user.username}</div>
                  <div className="profile-selector__email">{user.email}</div>
                  <div className="profile-selector__badge">
                    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span>Verified Account</span>
                  </div>
                </div>
              </div>

              <div className="profile-selector__memory-status">
                <div className="profile-selector__memory-indicator">
                  <span className="profile-selector__pulse-dot"></span>
                  <strong>Dynamic Memory Active</strong>
                </div>
                <p className="profile-selector__memory-desc">
                  Preferences dynamically learned from your searches and securely stored in Cloud PostgreSQL.
                </p>
              </div>

              <div className="profile-selector__divider"></div>

              <button
                type="button"
                role="menuitem"
                className="profile-selector__logout-btn"
                onClick={() => {
                  logout();
                  setIsOpen(false);
                }}
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                <span>Sign Out</span>
              </button>
            </>
          ) : (
            <>
              <div className="profile-selector__dropdown-header">
                Shopping Mode
              </div>

              <div className="profile-selector__guest-info">
                <div className="profile-selector__guest-title">Browsing as Guest</div>
                <p className="profile-selector__guest-desc">
                  Neutral recommendations without memory. Sign in to personalize your shopping experience.
                </p>
              </div>

              <button
                type="button"
                role="menuitem"
                className="profile-selector__action-btn profile-selector__action-btn--primary"
                onClick={() => {
                  setIsOpen(false);
                  openAuthModal("login");
                }}
              >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                  <polyline points="10 17 15 12 10 7" />
                  <line x1="15" y1="12" x2="3" y2="12" />
                </svg>
                <span>Sign In to Your Account</span>
              </button>

              <button
                type="button"
                role="menuitem"
                className="profile-selector__action-btn profile-selector__action-btn--secondary"
                onClick={() => {
                  setIsOpen(false);
                  openAuthModal("signup");
                }}
              >
                <span>Create New Account</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
