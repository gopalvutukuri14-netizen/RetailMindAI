import "./TypingIndicator.css";

export default function TypingIndicator() {
  return (
    <div className="typing-indicator" role="status" aria-label="Searching and analyzing recommendations">
      <div className="typing-indicator__avatar" aria-hidden="true">
        S
      </div>
      <div className="typing-indicator__card">
        <div className="typing-indicator__dots">
          <span className="typing-indicator__dot" />
          <span className="typing-indicator__dot" />
          <span className="typing-indicator__dot" />
        </div>
        <span className="typing-indicator__label">
          Searching catalog &amp; analyzing sentiment...
        </span>
      </div>
    </div>
  );
}
