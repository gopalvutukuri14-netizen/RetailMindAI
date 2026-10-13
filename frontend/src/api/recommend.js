import { getStoredToken } from "./auth";

const API_BASE = "http://localhost:8000";

/**
 * Call the SmartPick recommendation pipeline.
 * Attaches Authorization header if user is logged in.
 *
 * @param {string} query              - Natural-language shopping query
 * @param {string} userId             - Fallback profile ID if anonymous
 * @param {number} topK               - Number of products to return
 * @param {Array}  previousProducts   - Products from the last recommendation (for follow-up context)
 * @param {string|null} category      - Explicit category context if selected
 * @returns {Promise<object>} ResponseResult from the backend
 */
export async function getRecommendations(
  query,
  userId = "anonymous",
  topK = 5,
  previousProducts = [],
  category = null
) {
  const body = {
    query,
    user_id: userId,
    top_k: topK,
  };

  // Only send previous products if there are any
  if (previousProducts.length > 0) {
    body.previous_products = previousProducts;
  }

  // Attach explicit category filter context if provided
  if (category) {
    body.category = category;
  }

  const headers = {
    "Content-Type": "application/json",
  };

  const token = getStoredToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}/recommend`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch (netErr) {
    throw new Error(
      "Unable to connect to SmartPick recommendation server. Please check your network or ensure the backend is running on port 8000."
    );
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}
