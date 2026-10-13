import "./CategoryBar.css";

export const CATEGORIES = [
  {
    id: "all",
    label: "All Categories",
    shortLabel: "All",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
      </svg>
    ),
    sampleQuery: "",
  },
  {
    id: "phones",
    categoryEnum: "Cell_Phones_and_Accessories",
    label: "Cell Phones & Accessories",
    shortLabel: "Phones",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="5" y="2" width="14" height="20" rx="3" />
        <line x1="12" y1="18" x2="12.01" y2="18" />
      </svg>
    ),
    sampleQuery: "Samsung phone under ₹30000 with 8GB RAM",
  },
  {
    id: "electronics",
    categoryEnum: "Electronics",
    label: "Electronics",
    shortLabel: "Electronics",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
        <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
      </svg>
    ),
    sampleQuery: "Wireless Bluetooth headphones for gaming",
  },
  {
    id: "home",
    categoryEnum: "Home_and_Kitchen",
    label: "Home & Kitchen",
    shortLabel: "Home & Kitchen",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
    sampleQuery: "Non-stick cookware set for a family",
  },
  {
    id: "clothing",
    categoryEnum: "Clothing_Shoes_and_Jewelry",
    label: "Clothing & Shoes",
    shortLabel: "Clothing",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20.38 3.46L16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.5a2 2 0 0 0 1.54 1.63L6 11.2V20a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-8.8l1.6-.38a2 2 0 0 0 1.54-1.63l.58-3.5a2 2 0 0 0-1.34-2.23z" />
      </svg>
    ),
    sampleQuery: "Durable winter jacket",
  },
  {
    id: "office",
    categoryEnum: "Office_Products",
    label: "Office Products",
    shortLabel: "Office",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </svg>
    ),
    sampleQuery: "Comfortable ergonomic office chair",
  },
  {
    id: "sports",
    categoryEnum: "Sports_and_Outdoors",
    label: "Sports & Outdoors",
    shortLabel: "Sports",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
        <path d="M2 12h20" />
      </svg>
    ),
    sampleQuery: "Running shoes for daily jogging",
  },
];

export default function CategoryBar({ activeCategory, onSelectCategory, onTriggerQuery }) {
  return (
    <nav className="category-bar" aria-label="Product categories">
      <div className="category-bar__list">
        {CATEGORIES.map((cat) => {
          const isActive = activeCategory === cat.id;
          return (
            <button
              key={cat.id}
              type="button"
              className={`category-bar__item ${isActive ? "category-bar__item--active" : ""}`}
              onClick={() => {
                onSelectCategory(cat.id);
              }}
              aria-pressed={isActive}
            >
              <span className="category-bar__icon">{cat.icon}</span>
              <span className="category-bar__label">{cat.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
