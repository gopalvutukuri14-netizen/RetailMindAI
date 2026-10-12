import { useState, useEffect } from "react";
import "./ProductCard.css";

export default function ProductCard({ product, rank }) {
  const [hasError, setHasError] = useState(false);

  // Reset error state if product or image URL changes
  useEffect(() => {
    setHasError(false);
  }, [product.image_url]);

  const priceDisplay =
    product.price_inr != null
      ? `₹${Math.round(product.price_inr).toLocaleString("en-IN")}`
      : "Price unavailable";

  const hasValidImage = Boolean(product.image_url) && !hasError;

  return (
    <article className="product-card" data-testid="product-card" tabIndex={0}>
      <div className="product-card__header">
        <span className="product-card__rank-badge" aria-label={`Recommendation rank ${rank}`}>
          #{rank}
        </span>
        {product.brand && (
          <span className="product-card__brand" title={`Brand: ${product.brand}`}>
            {product.brand}
          </span>
        )}
      </div>

      <div className="product-card__media">
        {hasValidImage ? (
          <img
            src={product.image_url}
            alt={product.title || "Product image"}
            className="product-card__image"
            loading="lazy"
            onError={() => setHasError(true)}
          />
        ) : (
          <div className="product-card__fallback" aria-label="No image available">
            <svg
              className="product-card__fallback-icon"
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <span className="product-card__fallback-text">Image unavailable</span>
          </div>
        )}
      </div>

      <div className="product-card__content">
        <h3 className="product-card__title" title={product.title}>
          {product.title}
        </h3>

        <div className="product-card__pricing">
          <span className={`product-card__price ${product.price_inr == null ? "product-card__price--na" : ""}`}>
            {priceDisplay}
          </span>
        </div>

        {product.explanation && (
          <div className="product-card__match-reason">
            <span className="product-card__match-label">Why it matches</span>
            <p className="product-card__explanation">{product.explanation}</p>
          </div>
        )}

        {product.key_factors?.length > 0 && (
          <div className="product-card__evidence" aria-label="Key decision factors">
            {product.key_factors.map((factor, i) => (
              <span key={i} className="product-card__tag">
                <svg
                  className="product-card__check-icon"
                  width="11"
                  height="11"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>{factor}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </article>
  );
}
