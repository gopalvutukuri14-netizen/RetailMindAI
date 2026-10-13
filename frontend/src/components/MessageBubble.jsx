import ProductCard from "./ProductCard";
import FollowUpChips from "./FollowUpChips";
import "./MessageBubble.css";

export default function MessageBubble({ message, onFollowUp }) {
  const isUser = message.role === "user";

  // ── User message ────────────────────────────────────────
  if (isUser) {
    return (
      <div className="message-bubble message-bubble--user">
        <div className="message-bubble__content message-bubble__content--user">
          <div className="message-bubble__user-text">{message.text}</div>
        </div>
      </div>
    );
  }

  // ── Welcome message ─────────────────────────────────────
  if (message.type === "welcome") {
    return (
      <div className="message-bubble message-bubble--welcome">
        <div className="welcome-card">
          <div className="welcome-card__header">
            <div className="welcome-card__badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
              </svg>
              Smart Shopping Assistant
            </div>
            <h2 className="welcome-card__title">
              Find products that fit your needs, budget, and preferences.
            </h2>
            <p className="welcome-card__subtitle">
              Tell us what you are looking for. SmartPick compares relevant products across six categories and helps you understand your options with real customer sentiment.
            </p>
          </div>

          {message.exampleQueries?.length > 0 && (
            <div className="welcome-card__queries-section">
              <span className="welcome-card__queries-label">
                Popular example searches:
              </span>
              <div
                className={`welcome-card__queries-grid ${
                  message.exampleQueries.length === 6
                    ? "welcome-card__queries-grid--all"
                    : "welcome-card__queries-grid--category"
                }`}
              >
                {message.exampleQueries.map((item, i) => {
                  const queryText = typeof item === "string" ? item : item.query;
                  const catTag = typeof item === "object" ? item.category : null;
                  return (
                    <button
                      key={i}
                      type="button"
                      className="welcome-card__query-btn"
                      onClick={() => onFollowUp(queryText)}
                    >
                      {catTag && (
                        <span className="welcome-card__query-tag">{catTag}</span>
                      )}
                      <span className="welcome-card__query-text">{queryText}</span>
                      <span className="welcome-card__query-arrow">→</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Error message ───────────────────────────────────────
  if (message.type === "error") {
    return (
      <div className="message-bubble message-bubble--bot">
        <div className="message-bubble__avatar" aria-hidden="true">
          S
        </div>
        <div className="message-bubble__content">
          <div className="message-bubble__error" role="alert">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <div>
              <strong>Unable to complete search</strong>
              <p>{message.text}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Bot recommendation message ──────────────────────────
  const data = message.data || {};
  const isComparison = Boolean(data.comparison);

  return (
    <div className="message-bubble message-bubble--bot">
      <div className="message-bubble__avatar" aria-hidden="true">
        S
      </div>
      <div className="message-bubble__content message-bubble__content--bot">
        {/* ── Comparison Heading (if in comparison mode) ── */}
        {isComparison && data.comparison?.heading && (
          <div className="message-bubble__comparison-header">
            <div className="message-bubble__comparison-badge">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="14" height="14">
                <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
              </svg>
              <span>Side-by-Side Comparison</span>
            </div>
            <h2 className="message-bubble__comparison-title">{data.comparison.heading}</h2>
          </div>
        )}

        {/* ── Standard Summary (if NOT in comparison mode) ── */}
        {!isComparison && data.summary && (
          <div className="message-bubble__summary-box">
            <div className="message-bubble__summary-header">
              <svg className="message-bubble__spark-icon" viewBox="0 0 20 20" fill="currentColor">
                <path d="M15.98 1.804a1 1 0 0 0-1.96 0l-.24 1.192a8 8 0 0 1-6.192 6.192l-1.192.24a1 1 0 0 0 0 1.96l1.192.24a8 8 0 0 1 6.192 6.192l.24 1.192a1 1 0 0 0 1.96 0l.24-1.192a8 8 0 0 1 6.192-6.192l1.192-.24a1 1 0 0 0 0-1.96l-1.192-.24a8 8 0 0 1-6.192-6.192l-.24-1.192Z" />
              </svg>
              <span>Recommendation Overview</span>
            </div>
            <p className="message-bubble__summary-text">{data.summary}</p>
          </div>
        )}

        {/* ── Product Cards (2 side-by-side if comparison, grid otherwise) ── */}
        {data.recommendations?.length > 0 && (
          <div
            className={`message-bubble__products-grid ${
              isComparison ? "message-bubble__products-grid--comparison" : ""
            }`}
            role="region"
            aria-label={isComparison ? "Compared products" : "Recommended products"}
          >
            {data.recommendations
              .slice(0, isComparison ? 2 : data.recommendations.length)
              .map((product, i) => (
                <ProductCard
                  key={product.asin || i}
                  product={product}
                  rank={i + 1}
                />
              ))}
          </div>
        )}

        {/* ── Compare Top 2 Action Button (when 2+ recommendations in standard mode) ── */}
        {!isComparison && data.recommendations?.length >= 2 && (
          <div className="message-bubble__compare-action-row">
            <button
              type="button"
              className="message-bubble__compare-top-btn"
              onClick={() => onFollowUp("Compare the top 2 products")}
              title="Compare the top 2 products side-by-side"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="15" height="15">
                <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
              </svg>
              <span>Compare Top 2 Products</span>
            </button>
          </div>
        )}

        {/* ── Structured Side-by-Side Comparison Table ── */}
        {isComparison && data.comparison?.rows?.length > 0 && (
          <div
            className="message-bubble__comparison-table-wrapper"
            role="region"
            aria-label="Product comparison table"
          >
            <table className="comparison-table">
              <thead>
                <tr>
                  <th scope="col" className="comparison-table__th-aspect">Aspect</th>
                  <th scope="col" className="comparison-table__th-product">
                    <span className="comparison-table__th-badge">#1</span>
                    <span className="comparison-table__th-title">
                      {data.recommendations?.[0]?.brand ? `${data.recommendations[0].brand} ` : ""}
                      {data.recommendations?.[0]?.title || "Product 1"}
                    </span>
                  </th>
                  <th scope="col" className="comparison-table__th-product">
                    <span className="comparison-table__th-badge">#2</span>
                    <span className="comparison-table__th-title">
                      {data.recommendations?.[1]?.brand ? `${data.recommendations[1].brand} ` : ""}
                      {data.recommendations?.[1]?.title || "Product 2"}
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.comparison.rows.map((row, idx) => (
                  <tr
                    key={idx}
                    className={idx % 2 === 0 ? "comparison-table__tr--even" : "comparison-table__tr--odd"}
                  >
                    <td className="comparison-table__td-aspect">
                      <strong>{row.aspect}</strong>
                    </td>
                    <td className="comparison-table__td-val">
                      {row.product_a || "Not available in catalog"}
                    </td>
                    <td className="comparison-table__td-val">
                      {row.product_b || "Not available in catalog"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Comparison Verdict / Conclusion Paragraph ── */}
        {isComparison && data.comparison?.conclusion && (
          <div className="message-bubble__comparison-conclusion">
            <div className="message-bubble__conclusion-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="16" height="16">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Comparison Verdict & Recommendations</span>
            </div>
            <p className="message-bubble__conclusion-text">{data.comparison.conclusion}</p>
          </div>
        )}

        {/* ── Standard Additional Information Box ── */}
        {!isComparison && data.additional_information && (
          <div className="message-bubble__additional-box">
            <span className="message-bubble__additional-label">Comparison Insights:</span>
            <p className="message-bubble__additional-text">{data.additional_information}</p>
          </div>
        )}

        {/* ── Follow-Up Suggestions ── */}
        {data.follow_up_suggestions?.length > 0 && (
          <div className="message-bubble__followup-wrapper">
            <span className="message-bubble__followup-label">Suggested next steps:</span>
            <FollowUpChips
              suggestions={data.follow_up_suggestions}
              onSelect={onFollowUp}
            />
          </div>
        )}
      </div>
    </div>
  );
}
