const API_BASE = "http://localhost:8000";
const TOKEN_KEY = "smartpick_access_token";

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  } catch {
    // localStorage might be unavailable or full
  }
}

export function removeStoredToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr) {
    throw new Error(
      "Unable to connect to SmartPick authentication server. Please ensure the backend is running on port 8000."
    );
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    let errorMsg = data.detail;
    if (typeof errorMsg === "object") {
      errorMsg = JSON.stringify(errorMsg);
    }
    errorMsg = errorMsg || `Request failed (${response.status})`;
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export async function signup({ username, email, password, confirm_password }) {
  return request("/auth/signup", {
    method: "POST",
    body: JSON.stringify({
      username,
      email,
      password,
      confirm_password,
    }),
  });
}

export async function verifyEmail({ email, otp }) {
  const data = await request("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({
      email,
      otp,
    }),
  });
  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function resendOtp({ email, purpose = "signup_verify" }) {
  return request("/auth/resend-otp", {
    method: "POST",
    body: JSON.stringify({
      email,
      purpose,
    }),
  });
}

export async function login({ username_or_email, password }) {
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      username_or_email,
      password,
    }),
  });
  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

export async function forgotPassword({ email_or_username }) {
  return request("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({
      email_or_username,
    }),
  });
}

export async function resetPassword({ email, otp, new_password, confirm_new_password }) {
  return request("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({
      email,
      otp,
      new_password,
      confirm_new_password,
    }),
  });
}

export async function getMe(token) {
  const authToken = token || getStoredToken();
  if (!authToken) {
    throw new Error("No token found");
  }
  return request("/auth/me", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });
}
