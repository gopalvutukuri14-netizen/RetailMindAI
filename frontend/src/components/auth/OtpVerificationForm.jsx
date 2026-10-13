import { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";

export default function OtpVerificationForm() {
  const { verifyEmail, resendOtp, pendingEmail, setPendingEmail, setAuthModalTab, authError, setAuthError } = useAuth();
  const [emailInput, setEmailInput] = useState(pendingEmail || "");
  const [otp, setOtp] = useState("");
  const [countdown, setCountdown] = useState(60);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(null);

  useEffect(() => {
    if (pendingEmail) {
      setEmailInput(pendingEmail);
    }
  }, [pendingEmail]);

  // 60-second countdown for resend
  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setInterval(() => {
      setCountdown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const activeEmail = (pendingEmail || emailInput).trim();

  async function handleVerify(e) {
    e.preventDefault();
    if (!activeEmail) {
      setAuthError("Please enter the email address for verification.");
      return;
    }
    const cleanOtp = otp.trim();
    if (cleanOtp.length !== 6) {
      setAuthError("Please enter the complete 6-digit verification code.");
      return;
    }

    setIsSubmitting(true);
    setResendSuccess(null);
    try {
      await verifyEmail({ email: activeEmail, otp: cleanOtp });
      // Verification successful -> AuthContext closes modal & logs user in
    } catch {
      // Error handled in AuthContext
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleResend() {
    if (!activeEmail) {
      setAuthError("Please enter your email address to receive a code.");
      return;
    }
    if (countdown > 0 || isResending) return;
    setIsResending(true);
    setResendSuccess(null);
    setAuthError(null);
    try {
      const res = await resendOtp({ email: activeEmail, purpose: "signup_verify" });
      setCountdown(60);
      setResendSuccess(res.message || "A fresh verification code request was accepted.");
    } catch {
      // Error handled in AuthContext; countdown remains 0 so user can retry
    } finally {
      setIsResending(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={handleVerify} noValidate>
      <div className="auth-form__header">
        <div className="auth-form__badge-icon">
          <svg viewBox="0 0 24 24" width="28" height="28" stroke="currentColor" fill="none" strokeWidth="2">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
            <polyline points="22,6 12,13 2,6" />
          </svg>
        </div>
        <h2 id="auth-dialog-title" className="auth-form__title">Verify Your Email</h2>
        <p className="auth-form__subtitle">
          Enter the 6-digit verification code for <strong>{activeEmail || "your email"}</strong> to activate your account.
        </p>
      </div>

      {!pendingEmail && (
        <div className="auth-form__field">
          <label htmlFor="otp-email-input" className="auth-form__label">
            Email Address
          </label>
          <input
            id="otp-email-input"
            type="email"
            className="auth-form__input"
            placeholder="e.g. alex@example.com"
            value={emailInput}
            onChange={(e) => {
              setEmailInput(e.target.value);
              setPendingEmail(e.target.value);
            }}
            required
            disabled={isSubmitting || isResending}
          />
        </div>
      )}

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

      {resendSuccess && (
        <div className="auth-form__success-banner" role="status">
          <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" fill="none" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <span>{resendSuccess}</span>
        </div>
      )}

      <div className="auth-form__field">
        <label htmlFor="otp-input" className="auth-form__label">
          6-Digit Verification Code
        </label>
        <input
          id="otp-input"
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
        <span className="auth-form__hint">Valid for 5 minutes.</span>
      </div>

      <button
        type="submit"
        className="auth-form__submit-btn"
        disabled={isSubmitting || otp.length !== 6}
      >
        {isSubmitting ? (
          <span className="auth-form__spinner"></span>
        ) : (
          "Verify & Activate Account"
        )}
      </button>

      <div className="auth-form__resend-area">
        {countdown > 0 ? (
          <span className="auth-form__countdown-text">
            Resend available in {countdown}s
          </span>
        ) : (
          <button
            type="button"
            className="auth-form__resend-btn"
            onClick={handleResend}
            disabled={isResending}
          >
            {isResending ? "Sending..." : "Resend Verification Code"}
          </button>
        )}
      </div>

      <div className="auth-form__footer">
        Wrong email?{" "}
        <button
          type="button"
          className="auth-form__switch-btn"
          onClick={() => setAuthModalTab("signup")}
        >
          Change email
        </button>
      </div>
    </form>
  );
}
