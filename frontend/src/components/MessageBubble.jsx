import ProductCard from "./ProductCard";
import FollowUpChips from "./FollowUpChips";
import "./MessageBubble.css";

export default function MessageBubble({ message, onFollowUp }) {
  const isUser = message.role === "user";

  // ── User message ────────────────────────────────────────
  if (isUser) {
    return (
      <div className="message-bubble message-bubble--user">
        <div className="message-bubble__avatar message-bubble__avatar--user">
          U
        </div>
        <div className="message-bubble__content">{message.text}</div>
      </div>
    );
  }

  // ── Welcome message ─────────────────────────────────────
  if (message.type === "welcome") {
    return (
      <div className="message-bubble message-bubble--bot">
        <div className="message-bubble__avatar message-bubble__avatar--bot">
          R
        </div>
        <div className="message-bubble__content">
          <div className="message-bubble__summary">{message.text}</div>
          {message.exampleQueries && (
            <div className="message-bubble__welcome-queries">
              {message.exampleQueries.map((q, i) => (
                <button
                  key={i}
                  className="message-bubble__welcome-query"
                  onClick={() => onFollowUp(q)}
                >
                  {q}
                </button>
              ))}
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
        <div className="message-bubble__avatar message-bubble__avatar--bot">
          R
        </div>
        <div className="message-bubble__content">
          <div className="message-bubble__error">{message.text}</div>
        </div>
      </div>
    );
  }

  // ── Bot recommendation message ──────────────────────────
  const data = message.data;

  return (
    <div className="message-bubble message-bubble--bot">
      <div className="message-bubble__avatar message-bubble__avatar--bot">
        R
      </div>
      <div className="message-bubble__content">
        {data.summary && (
          <div className="message-bubble__summary">{data.summary}</div>
        )}

        {data.recommendations?.length > 0 && (
          <div className="message-bubble__products">
            {data.recommendations.map((product, i) => (
              <ProductCard key={product.asin || i} product={product} rank={i + 1} />
            ))}
          </div>
        )}

        {data.additional_information && (
          <div className="message-bubble__additional">
            {data.additional_information}
          </div>
        )}

        {data.follow_up_suggestions?.length > 0 && (
          <FollowUpChips
            suggestions={data.follow_up_suggestions}
            onSelect={onFollowUp}
          />
        )}
      </div>
    </div>
  );
}
