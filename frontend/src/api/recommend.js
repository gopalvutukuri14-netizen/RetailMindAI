const API_BASE = "http://localhost:8000";

/**
 * Call the RetailMind AI recommendation pipeline.
 *
 * @param {string} query    - Natural-language shopping query
 * @param {string} userId   - Profile ID for personalization
 * @param {number} topK     - Number of products to return
 * @returns {Promise<object>} ResponseResult from the backend
 */
export async function getRecommendations(query, userId = "anonymous", topK = 5) {
  const response = await fetch(`${API_BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      user_id: userId,
      top_k: topK,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}
