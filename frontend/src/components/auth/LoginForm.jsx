import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

export default function LoginForm() {
  const { login, setAuthModalTab, authError, setAuthError } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setAuthError("Please enter both username/email and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ username_or_email: identifier.trim(), password });
    } catch {
      // Error handled in AuthContext
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form__header">
        <h2 id="auth-dialog-title" className="auth-form__title">Welcome Back</h2>
        <p className="auth-form__subtitle">
          Sign in to access your personal shopping memory and preferences.
        </p>
      </div>

      {authError && (
        <div className="auth-form__error-banner" role="alert">
          <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{authError}</span>
        </div>
      )}

      <div className="auth-form__field">
        <label htmlFor="login-identifier" className="auth-form__label">
          Username or Email
        </label>
        <input
          id="login-identifier"
          type="text"
          className="auth-form__input"
          placeholder="e.g. alex or alex@example.com"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
          autoFocus
          disabled={isSubmitting}
        />
      </div>

      <div className="auth-form__field">
        <div className="auth-form__label-row">
          <label htmlFor="login-password" className="auth-form__label">
            Password
          </label>
          <button
            type="button"
            className="auth-form__link-btn"
            onClick={() => setAuthModalTab("forgot_password")}
            tabIndex={0}
          >
            Forgot password?
          </button>
        </div>
        <div className="auth-form__input-wrapper">
          <input
            id="login-password"
            type={showPassword ? "text" : "password"}
            className="auth-form__input"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={isSubmitting}
          />
          <button
            type="button"
            className="auth-form__toggle-pw"
            onClick={() => setShowPassword(!showPassword)}
            title={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>
      </div>

      <button
        type="submit"
        className="auth-form__submit-btn"
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <span className="auth-form__spinner"></span>
        ) : (
          "Sign In"
        )}
      </button>

      <div className="auth-form__footer">
        Don&apos;t have an account?{" "}
        <button
          type="button"
          className="auth-form__switch-btn"
          onClick={() => setAuthModalTab("signup")}
        >
          Create account
        </button>
      </div>
    </form>
  );
}
