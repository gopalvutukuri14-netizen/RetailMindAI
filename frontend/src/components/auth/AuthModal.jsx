import { useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";
import OtpVerificationForm from "./OtpVerificationForm";
import ForgotPasswordForm from "./ForgotPasswordForm";
import ResetPasswordForm from "./ResetPasswordForm";
import "./AuthModal.css";

export default function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, authModalTab } = useAuth();

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape" && isAuthModalOpen) {
        closeAuthModal();
      }
    }
    if (isAuthModalOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.body.style.overflow = "unset";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isAuthModalOpen, closeAuthModal]);

  if (!isAuthModalOpen) return null;

  return (
    <div className="auth-modal-backdrop" onClick={closeAuthModal} role="presentation">
      <div
        className="auth-modal-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="auth-modal-close"
          onClick={closeAuthModal}
          aria-label="Close authentication modal"
          title="Close (Esc)"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" fill="none" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        <div className="auth-modal-body">
          {authModalTab === "login" && <LoginForm />}
          {authModalTab === "signup" && <SignupForm />}
          {authModalTab === "verify_otp" && <OtpVerificationForm />}
          {authModalTab === "forgot_password" && <ForgotPasswordForm />}
          {authModalTab === "reset_password" && <ResetPasswordForm />}
        </div>
      </div>
    </div>
  );
}
