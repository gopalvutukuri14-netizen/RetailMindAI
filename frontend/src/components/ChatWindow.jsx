import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import "./ChatWindow.css";

export default function ChatWindow({ messages, isLoading, onFollowUp }) {
  const lastBotMsgRef = useRef(null);
  const loadingRef = useRef(null);
  const prevCountRef = useRef(messages.length);

  useEffect(() => {
    // If loading started, smoothly show typing indicator
    if (isLoading && loadingRef.current) {
      loadingRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }

    // When new messages arrive (and not initial load)
    if (messages.length > prevCountRef.current && messages.length > 1) {
      const lastMsg = messages[messages.length - 1];
      if (lastMsg.role === "bot" && lastBotMsgRef.current) {
        // Bring start of recommendation into view so user sees #1 match immediately
        lastBotMsgRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }
    prevCountRef.current = messages.length;
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      {messages.map((msg, i) => {
        const isLatestBot = msg.role === "bot" && i === messages.length - 1;
        return (
          <div
            key={i}
            ref={isLatestBot ? lastBotMsgRef : null}
            className="chat-window__message-wrapper"
          >
            <MessageBubble message={msg} onFollowUp={onFollowUp} />
          </div>
        );
      })}

      {isLoading && (
        <div ref={loadingRef}>
          <TypingIndicator />
        </div>
      )}
    </div>
  );
}
