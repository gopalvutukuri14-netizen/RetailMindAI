import { useState } from "react";
import "./ChatInput.css";

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <div className="chat-input">
      <form className="chat-input__form" onSubmit={handleSubmit}>
        <input
          className="chat-input__field"
          type="text"
          placeholder="Ask about smartphones..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          autoFocus
        />
        <button
          className="chat-input__send"
          type="submit"
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          &#10148;
        </button>
      </form>
    </div>
  );
}
