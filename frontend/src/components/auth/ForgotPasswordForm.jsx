import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

export default function ForgotPasswordForm() {
  const { forgotPassword, setAuthModalTab, authError, setAuthError } = useAuth();
  const [identifier, setIdentifier] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!identifier.trim()) {
      setAuthError("Please enter your registered email or username.");
      return;
    }

    setIsSubmitting(true);
    try {
      await forgotPassword({ email_or_username: identifier.trim() });
      // Transition to reset_password form
    } catch {
      // Error handled in AuthContext
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form__header">
        <h2 id="auth-dialog-title" className="auth-form__title">Reset Your Password</h2>
        <p className="auth-form__subtitle">
          Enter your email or username and we will send you a 6-digit password reset code.
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
        <label htmlFor="forgot-identifier" className="auth-form__label">
          Registered Email or Username
        </label>
        <input
          id="forgot-identifier"
          type="text"
          className="auth-form__input"
          placeholder="e.g. alex@example.com"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
          autoFocus
          disabled={isSubmitting}
        />
      </div>

      <button
        type="submit"
        className="auth-form__submit-btn"
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <span className="auth-form__spinner"></span>
        ) : (
          "Send Password Reset Code"
        )}
      </button>

      <div className="auth-form__footer">
        Remembered your password?{" "}
        <button
          type="button"
          className="auth-form__switch-btn"
          onClick={() => setAuthModalTab("login")}
        >
          Back to sign in
        </button>
      </div>
    </form>
  );
}
