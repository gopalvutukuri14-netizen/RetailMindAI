import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

export default function SignupForm() {
  const { signup, setAuthModalTab, authError, setAuthError, setPendingEmail } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!username.trim() || !email.trim() || !password || !confirmPassword) {
      setAuthError("Please fill out all fields.");
      return;
    }

    if (username.trim().length < 3) {
      setAuthError("Username must be at least 3 characters long.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setAuthError("Please enter a valid email address.");
      return;
    }

    if (password !== confirmPassword) {
      setAuthError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setAuthError("Password must be at least 8 characters long.");
      return;
    }

    if (!/\d/.test(password) || !/[a-zA-Z]/.test(password)) {
      setAuthError("Password must contain at least one letter and at least one number.");
      return;
    }

    setIsSubmitting(true);
    try {
      await signup({
        username: username.trim(),
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
      });
      // Signup successful -> AuthContext transitions tab to verify_otp
    } catch {
      // Error handled in AuthContext
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form__header">
        <h2 id="auth-dialog-title" className="auth-form__title">Create Your Account</h2>
        <p className="auth-form__subtitle">
          Start with fresh, independent memory personalized just for you.
        </p>
      </div>

      {authError && (
        <div className="auth-form__error-banner" role="alert">
          <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span>{authError}</span>
            {authError.toLowerCase().includes("account created") && (
              <button
                type="button"
                style={{
                  background: "none",
                  border: "none",
                  color: "#2563eb",
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "left",
                  padding: 0,
                  fontSize: "0.85rem",
                  textDecoration: "underline",
                }}
                onClick={() => {
                  setPendingEmail(email.trim());
                  setAuthModalTab("verify_otp");
                }}
              >
                Go to Verification Form &rarr;
              </button>
            )}
            {authError.toLowerCase().includes("already exists") && (
              <button
                type="button"
                style={{
                  background: "none",
                  border: "none",
                  color: "#2563eb",
                  fontWeight: 600,
                  cursor: "pointer",
                  textAlign: "left",
                  padding: 0,
                  fontSize: "0.85rem",
                  textDecoration: "underline",
                }}
                onClick={() => setAuthModalTab("login")}
              >
                Sign In Instead &rarr;
              </button>
            )}
          </div>
        </div>
      )}

      <div className="auth-form__field">
        <label htmlFor="signup-username" className="auth-form__label">
          Username
        </label>
        <input
          id="signup-username"
          type="text"
          className="auth-form__input"
          placeholder="e.g. alex_shopper"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoFocus
          disabled={isSubmitting}
        />
        <span className="auth-form__hint">Letters, numbers, and underscores (min 3 chars).</span>
      </div>

      <div className="auth-form__field">
        <label htmlFor="signup-email" className="auth-form__label">
          Email Address
        </label>
        <input
          id="signup-email"
          type="email"
          className="auth-form__input"
          placeholder="e.g. alex@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="auth-form__field">
        <label htmlFor="signup-password" className="auth-form__label">
          Password
        </label>
        <div className="auth-form__input-wrapper">
          <input
            id="signup-password"
            type={showPassword ? "text" : "password"}
            className="auth-form__input"
            placeholder="Min 8 characters, at least 1 digit"
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

      <div className="auth-form__field">
        <label htmlFor="signup-confirm-password" className="auth-form__label">
          Confirm Password
        </label>
        <input
          id="signup-confirm-password"
          type={showPassword ? "text" : "password"}
          className="auth-form__input"
          placeholder="Re-enter your password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
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
          "Register & Send Verification Code"
        )}
      </button>

      <div className="auth-form__footer">
        Already have an account?{" "}
        <button
          type="button"
          className="auth-form__switch-btn"
          onClick={() => setAuthModalTab("login")}
        >
          Sign in
        </button>
      </div>
    </form>
  );
}
