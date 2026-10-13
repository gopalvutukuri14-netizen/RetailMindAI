import { useState, useCallback, useRef } from "react";
import { useAuth } from "./context/AuthContext";
import ProfileSelector from "./components/ProfileSelector";
import AuthModal from "./components/auth/AuthModal";
import CategoryBar, { CATEGORIES } from "./components/CategoryBar";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import { getRecommendations } from "./api/recommend";
import "./App.css";

const MULTI_CATEGORY_QUERIES = [
  { category: "Phones", query: "Samsung phone under ₹30000 with 8GB RAM" },
  { category: "Electronics", query: "Wireless Bluetooth headphones for gaming" },
  { category: "Home & Kitchen", query: "Non-stick cookware set for a family" },
  { category: "Clothing", query: "Durable winter jacket" },
  { category: "Office", query: "Comfortable ergonomic office chair" },
  { category: "Sports", query: "Running shoes for daily jogging" },
  { category: "Demo", query: "Test product images & fallbacks" },
];

const WELCOME_MESSAGE = {
  role: "bot",
  type: "welcome",
  exampleQueries: MULTI_CATEGORY_QUERIES,
};

export default function App() {
  const { user } = useAuth();
  const [activeCategory, setActiveCategory] = useState("all");
  const [messages, setMessages] = useState([WELCOME_MESSAGE]);
  const [isLoading, setIsLoading] = useState(false);

  // Track the last recommendation's products so follow-up queries
  // like "Compare top 2" can reference them instead of doing a fresh search.
  const lastProductsRef = useRef([]);

  const handleNewSearch = useCallback(() => {
    setMessages([WELCOME_MESSAGE]);
    lastProductsRef.current = [];
    setActiveCategory("all");
  }, []);

  const sendQuery = useCallback(
    async (query) => {
      // Add user message
      const userMsg = { role: "user", text: query };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      // Check if user clicked a specific category or typed fresh
      const matchingCategory = CATEGORIES.find(
        (c) => c.sampleQuery && c.sampleQuery.toLowerCase() === query.toLowerCase().trim()
      );
      if (matchingCategory) {
        setActiveCategory(matchingCategory.id);
      } else {
        // Fresh natural-language query: avoid stale category lock
        setActiveCategory("all");
      }

      // Diagnostic scenario test: renders valid image, missing image, and broken image fallback
      const normalizedQuery = query.toLowerCase().trim();
      if (
        normalizedQuery === "test images" ||
        normalizedQuery === "demo images" ||
        normalizedQuery === "test product images & fallbacks"
      ) {
        setTimeout(() => {
          const diagnosticData = {
            summary:
              "Image Verification Suite: Demonstrating recommendation cards with (1) authentic Amazon image URL, (2) missing image URL (null), and (3) invalid/broken image URL triggering automatic onError fallback.",
            recommendations: [
              {
                asin: "B07RPHM14M",
                title: "Galaxy S10 5G Enabled 6.7in SM-G977UZAVZW 8GB+256GB (Valid Image)",
                brand: "SAMSUNG",
                price_inr: 28687.12,
                image_url: "https://m.media-amazon.com/images/I/41lVosxv3pL._AC_.jpg",
                explanation:
                  "Rendered with authentic Amazon image URL sourced from dataset metadata 'images' field.",
                key_factors: ["Valid Image URL", "Proper Sizing", "High Quality"],
              },
              {
                asin: "B00MISSING",
                title: "Rare Vintage Audio Component (Missing Image - null)",
                brand: "VintageAudio",
                price_inr: 12500.0,
                image_url: null,
                explanation:
                  "Product without image in metadata (null). Renders elegant SVG fallback placeholder.",
                key_factors: ["Missing Image", "Clean Fallback", "Responsive"],
              },
              {
                asin: "B00BROKEN",
                title: "Rugged Tactical Protective Case (Broken 404 Image URL)",
                brand: "ArmorShield",
                price_inr: 1499.0,
                image_url: "https://invalid-domain-nonexistent.example.com/broken_photo.jpg",
                explanation:
                  "Product with broken image URL. img onError event triggers instant fallback placeholder.",
                key_factors: ["Invalid URL", "onError Fallback", "Zero Layout Shift"],
              },
            ],
            additional_information:
              "All three product image states verified: authentic image, missing image (null), and broken image URL fallback.",
            follow_up_suggestions: [
              "Wireless Bluetooth headphones for gaming",
              "Comfortable ergonomic office chair",
              "Compare the top 2 options",
            ],
          };

          const botMsg = { role: "bot", type: "recommendation", data: diagnosticData };
          setMessages((prev) => [...prev, botMsg]);
          lastProductsRef.current = diagnosticData.recommendations;
          setIsLoading(false);
        }, 300);
        return;
      }

      try {
        const data = await getRecommendations(
          query,
          user?.id || "anonymous",
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
          text: `Something went wrong: ${err.message}. Please check that the SmartPick backend server is running on port 8000.`,
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    [user?.id]
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
    <div className="app-layout">
      {/* ── Stable Header Area (Top Bar + Category Discovery) ── */}
      <header className="app-header-area" role="banner">
        <div className="app-header-inner">
          <div className="top-bar">
            <a
              href="/"
              className="top-bar__brand"
              onClick={(e) => {
                e.preventDefault();
                handleNewSearch();
              }}
            >
              <div className="top-bar__logo" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <path d="M16 10a4 4 0 0 1-8 0" />
                </svg>
              </div>
              <div className="top-bar__text">
                <div className="top-bar__title">
                  Smart<span className="top-bar__title-accent">Pick</span>
                </div>
                <div className="top-bar__subtitle">Find the right product for you.</div>
              </div>
            </a>

            <div className="top-bar__actions">
              {messages.length > 1 && (
                <button
                  type="button"
                  className="top-bar__new-search-btn"
                  onClick={handleNewSearch}
                  title="Start a new search"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 4v16m-8-8h16" />
                  </svg>
                  <span>New Search</span>
                </button>
              )}

              <ProfileSelector />
            </div>
          </div>

          <CategoryBar
            activeCategory={activeCategory}
            onSelectCategory={setActiveCategory}
            onTriggerQuery={sendQuery}
          />
        </div>
      </header>

      {/* ── Main Conversation Region (Page-right scrollbar) ── */}
      <main className="app-main-scroller" role="main">
        <div className="app-conversation-content">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onFollowUp={handleFollowUp}
          />
        </div>
      </main>

      {/* ── Sticky Bottom Search Composer ── */}
      <div className="app-composer-area">
        <div className="app-composer-inner">
          <ChatInput onSend={sendQuery} disabled={isLoading} />
        </div>
      </div>

      {/* ── Authentication Modal (Sign In / Signup / OTP / Reset) ── */}
      <AuthModal />
    </div>
  );
}
