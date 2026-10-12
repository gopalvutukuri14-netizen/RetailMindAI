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
              <div className="welcome-card__queries-grid">
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

  return (
    <div className="message-bubble message-bubble--bot">
      <div className="message-bubble__avatar" aria-hidden="true">
        S
      </div>
      <div className="message-bubble__content message-bubble__content--bot">
        {data.summary && (
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

        {data.recommendations?.length > 0 && (
          <div
            className="message-bubble__products-grid"
            role="region"
            aria-label="Recommended products"
          >
            {data.recommendations.map((product, i) => (
              <ProductCard
                key={product.asin || i}
                product={product}
                rank={i + 1}
              />
            ))}
          </div>
        )}

        {data.additional_information && (
          <div className="message-bubble__additional-box">
            <span className="message-bubble__additional-label">Comparison Insights:</span>
            <p className="message-bubble__additional-text">{data.additional_information}</p>
          </div>
        )}

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
