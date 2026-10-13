import { createContext, useContext, useState, useEffect, useCallback } from "react";
import * as authApi from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => authApi.getStoredToken());
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Modal display state
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState("login"); // login | signup | verify_otp | forgot_password | reset_password
  const [pendingEmail, setPendingEmail] = useState("");

  // Restore session on mount
  useEffect(() => {
    let isMounted = true;
    async function restoreSession() {
      const storedToken = authApi.getStoredToken();
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        const userData = await authApi.getMe(storedToken);
        if (isMounted) {
          setUser(userData);
          setToken(storedToken);
        }
      } catch (err) {
        // Expired or revoked token
        authApi.removeStoredToken();
        if (isMounted) {
          setUser(null);
          setToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      isMounted = false;
    };
  }, []);

  const openAuthModal = useCallback((tab = "login", email = "") => {
    setAuthModalTab(tab);
    if (email) setPendingEmail(email);
    setAuthError(null);
    setIsAuthModalOpen(true);
  }, []);

  const closeAuthModal = useCallback(() => {
    setIsAuthModalOpen(false);
    setAuthError(null);
  }, []);

  const login = useCallback(async ({ username_or_email, password }) => {
    setAuthError(null);
    try {
      const res = await authApi.login({ username_or_email, password });
      setUser(res.user);
      setToken(res.access_token);
      setIsAuthModalOpen(false);
      return res;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const signup = useCallback(async ({ username, email, password, confirm_password }) => {
    setAuthError(null);
    setPendingEmail(email);
    try {
      const res = await authApi.signup({ username, email, password, confirm_password });
      setAuthModalTab("verify_otp");
      return res;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const verifyEmail = useCallback(async ({ email, otp }) => {
    setAuthError(null);
    try {
      const res = await authApi.verifyEmail({ email, otp });
      setUser(res.user);
      setToken(res.access_token);
      setIsAuthModalOpen(false);
      return res;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const resendOtp = useCallback(async ({ email, purpose = "signup_verify" }) => {
    setAuthError(null);
    try {
      return await authApi.resendOtp({ email, purpose });
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const forgotPassword = useCallback(async ({ email_or_username }) => {
    setAuthError(null);
    try {
      const res = await authApi.forgotPassword({ email_or_username });
      setPendingEmail(email_or_username);
      setAuthModalTab("reset_password");
      return res;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const resetPassword = useCallback(async ({ email, otp, new_password, confirm_new_password }) => {
    setAuthError(null);
    try {
      const res = await authApi.resetPassword({
        email,
        otp,
        new_password,
        confirm_new_password,
      });
      setAuthModalTab("login");
      return res;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  }, []);

  const logout = useCallback(() => {
    authApi.removeStoredToken();
    setUser(null);
    setToken(null);
    setAuthError(null);
  }, []);

  const value = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    authError,
    setAuthError,
    isAuthModalOpen,
    authModalTab,
    pendingEmail,
    setPendingEmail,
    setAuthModalTab,
    openAuthModal,
    closeAuthModal,
    login,
    signup,
    verifyEmail,
    resendOtp,
    forgotPassword,
    resetPassword,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
