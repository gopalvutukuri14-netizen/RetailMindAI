import { useState } from "react";
import "./ChatInput.css";

export default function ChatInput({ onSend, disabled, currentQuery = "" }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleClear() {
    setValue("");
  }

  return (
    <div className="chat-input" role="region" aria-label="Search composer">
      <form className="chat-input__form" onSubmit={handleSubmit}>
        <div className="chat-input__icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </div>

        <input
          className="chat-input__field"
          type="text"
          placeholder="Describe what you need, your budget, or preferred features…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          aria-label="Product search query"
        />

        {value.trim() && !disabled && (
          <button
            type="button"
            className="chat-input__clear"
            onClick={handleClear}
            aria-label="Clear input"
          >
            ✕
          </button>
        )}

        <button
          className="chat-input__send"
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label={disabled ? "Searching..." : "Search products"}
          title="Search products"
        >
          {disabled ? (
            <span className="chat-input__spinner" aria-hidden="true" />
          ) : (
            <>
              <span className="chat-input__send-label">Find</span>
              <svg
                className="chat-input__send-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </>
          )}
        </button>
      </form>
      <div className="chat-input__hint">
        Tip: Try queries like <em>&ldquo;Wireless headphones under ₹5,000&rdquo;</em> or <em>&ldquo;Ergonomic chair with lumbar support&rdquo;</em>
      </div>
    </div>
  );
}
