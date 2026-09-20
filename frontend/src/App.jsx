import { useState, useCallback, useRef } from "react";
import ProfileSelector from "./components/ProfileSelector";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import { getRecommendations } from "./api/recommend";
import "./App.css";

const WELCOME_MESSAGE = {
  role: "bot",
  type: "welcome",
  text: "Welcome to RetailMind AI! I can help you find the perfect smartphone. Tell me what you're looking for \u2014 your budget, preferred brand, must-have features \u2014 and I'll find the best matches with real customer sentiment analysis.",
  exampleQueries: [
    "Best Samsung phone under 15000 with good camera",
    "Compare budget phones under 10000 with long battery",
    "Premium phone with great display and performance",
  ],
};

export default function App() {
  const [profileId, setProfileId] = useState("anonymous");
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);

  // Track the last recommendation's products so follow-up queries
  // like "Compare top 2" can reference them instead of doing a fresh search.
  const lastProductsRef = useRef([]);

  const sendQuery = useCallback(
    async (query) => {
      // Add user message
      const userMsg = { role: "user", text: query };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const data = await getRecommendations(
          query,
          profileId,
          5,
          lastProductsRef.current
        );

        const botMsg = { role: "bot", type: "recommendation", data };
        setMessages((prev) => [...prev, botMsg]);

        // Update the context: if this response has product recommendations,
        // store them for the next follow-up. If not (general response),
        // keep the previous ones.
        if (data.recommendations && data.recommendations.length > 0) {
          lastProductsRef.current = data.recommendations;
        }
      } catch (err) {
        const errorMsg = {
          role: "bot",
          type: "error",
          text: `Something went wrong: ${err.message}. Please make sure the backend server is running on port 8000.`,
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [profileId]
  );

  const handleFollowUp = useCallback(
    (text) => {
      if (!isLoading) {
        sendQuery(text);
      }
    },
    [sendQuery, isLoading]
  );

  return (
    <div className="app-shell">
      {/* ── Top Bar ─────────────────────────────────────── */}
      <header className="top-bar">
        <div className="top-bar__brand">
          <div className="top-bar__logo">R</div>
          <div>
            <div className="top-bar__title">RetailMind AI</div>
            <div className="top-bar__subtitle">Smart Product Recommendations</div>
          </div>
        </div>
        <ProfileSelector
          activeProfileId={profileId}
          onProfileChange={setProfileId}
        />
      </header>

      {/* ── Chat Area ───────────────────────────────────── */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onFollowUp={handleFollowUp}
      />

      {/* ── Input Bar ───────────────────────────────────── */}
      <ChatInput onSend={sendQuery} disabled={isLoading} />
    </div>
  );
}
