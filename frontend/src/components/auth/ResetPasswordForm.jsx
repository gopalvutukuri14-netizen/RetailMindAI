import { useState } from "react";
import { useAuth } from "../../context/AuthContext";

export default function ResetPasswordForm() {
  const { resetPassword, pendingEmail, setAuthModalTab, authError, setAuthError } = useAuth();
  const [email, setEmail] = useState(pendingEmail || "");
  const [otp, setOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email.trim() || !otp.trim() || !newPassword || !confirmPassword) {
      setAuthError("Please fill out all fields.");
      return;
    }

    if (otp.trim().length !== 6) {
      setAuthError("Please enter the complete 6-digit reset code.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setAuthError("Passwords do not match.");
      return;
    }

    if (newPassword.length < 8) {
      setAuthError("New password must be at least 8 characters long.");
      return;
    }

    if (!/\d/.test(newPassword) || !/[a-zA-Z]/.test(newPassword)) {
      setAuthError("New password must contain at least one letter and at least one number.");
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await resetPassword({
        email: email.trim(),
        otp: otp.trim(),
        new_password: newPassword,
        confirm_new_password: confirmPassword,
      });
      setSuccessMessage(res.message || "Password reset successfully! You can now log in.");
    } catch {
      // Error handled in AuthContext
    } finally {
      setIsSubmitting(false);
    }
  }

  if (successMessage) {
    return (
      <div className="auth-form">
        <div className="auth-form__header">
          <div className="auth-form__badge-icon auth-form__badge-icon--success">
            <svg viewBox="0 0 24 24" width="28" height="28" stroke="currentColor" fill="none" strokeWidth="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <h2 id="auth-dialog-title" className="auth-form__title">Password Reset Complete</h2>
          <p className="auth-form__subtitle">{successMessage}</p>
        </div>
        <button
          type="button"
          className="auth-form__submit-btn"
          onClick={() => setAuthModalTab("login")}
        >
          Proceed to Sign In
        </button>
      </div>
    );
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form__header">
        <h2 id="auth-dialog-title" className="auth-form__title">Set New Password</h2>
        <p className="auth-form__subtitle">
          Enter the 6-digit code sent to your email along with your new password.
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
        <label htmlFor="reset-email" className="auth-form__label">
          Email Address
        </label>
        <input
          id="reset-email"
          type="email"
          className="auth-form__input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isSubmitting}
        />
      </div>

      <div className="auth-form__field">
        <label htmlFor="reset-otp" className="auth-form__label">
          6-Digit Reset Code
        </label>
        <input
          id="reset-otp"
          type="text"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={6}
          className="auth-form__input auth-form__input--otp"
          placeholder="______"
          value={otp}
          onChange={(e) => setOtp(e.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
          required
          autoFocus
          disabled={isSubmitting}
        />
      </div>

      <div className="auth-form__field">
        <label htmlFor="reset-new-password" className="auth-form__label">
          New Password
        </label>
        <div className="auth-form__input-wrapper">
          <input
            id="reset-new-password"
            type={showPassword ? "text" : "password"}
            className="auth-form__input"
            placeholder="Min 8 characters, at least 1 digit"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
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
        <label htmlFor="reset-confirm-password" className="auth-form__label">
          Confirm New Password
        </label>
        <input
          id="reset-confirm-password"
          type={showPassword ? "text" : "password"}
          className="auth-form__input"
          placeholder="Re-enter your new password"
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
          "Update Password"
        )}
      </button>

      <div className="auth-form__footer">
        Back to{" "}
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
