import "./ProductCard.css";

export default function ProductCard({ product, rank }) {
  const priceDisplay =
    product.price_inr != null
      ? `Rs.${product.price_inr.toLocaleString("en-IN")}`
      : "Price N/A";

  return (
    <div className="product-card">
      <div className="product-card__rank">{rank}</div>

      <div className="product-card__title">{product.title}</div>

      <div className="product-card__meta">
        <span className="product-card__price">{priceDisplay}</span>
        {product.brand && (
          <span className="product-card__brand">{product.brand}</span>
        )}
      </div>

      {product.explanation && (
        <div className="product-card__explanation">{product.explanation}</div>
      )}

      {product.key_factors?.length > 0 && (
        <div className="product-card__tags">
          {product.key_factors.map((tag, i) => (
            <span key={i} className="product-card__tag">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
