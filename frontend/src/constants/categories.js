/**
 * Category metadata and dynamic example queries for SmartPick.
 */

export const CATEGORIES_DEF = [
  {
    id: "all",
    label: "All Categories",
    shortLabel: "All",
    sampleQuery: "",
  },
  {
    id: "phones",
    categoryEnum: "Cell_Phones_and_Accessories",
    label: "Cell Phones & Accessories",
    shortLabel: "Phones",
    sampleQuery: "Samsung phone under ₹30000 with 8GB RAM",
  },
  {
    id: "electronics",
    categoryEnum: "Electronics",
    label: "Electronics",
    shortLabel: "Electronics",
    sampleQuery: "Wireless Bluetooth headphones for gaming",
  },
  {
    id: "home",
    categoryEnum: "Home_and_Kitchen",
    label: "Home & Kitchen",
    shortLabel: "Home & Kitchen",
    sampleQuery: "Non-stick cookware set for a family",
  },
  {
    id: "clothing",
    categoryEnum: "Clothing_Shoes_and_Jewelry",
    label: "Clothing & Shoes",
    shortLabel: "Clothing",
    sampleQuery: "Durable winter jacket",
  },
  {
    id: "office",
    categoryEnum: "Office_Products",
    label: "Office Products",
    shortLabel: "Office",
    sampleQuery: "Comfortable ergonomic office chair",
  },
  {
    id: "sports",
    categoryEnum: "Sports_and_Outdoors",
    label: "Sports & Outdoors",
    shortLabel: "Sports",
    sampleQuery: "Running shoes for daily jogging",
  },
];

export const CATEGORY_EXAMPLE_QUERIES = {
  all: [
    { category: "Cell Phones & Accessories", query: "Samsung phone under ₹30000 with 8GB RAM" },
    { category: "Electronics", query: "Wireless Bluetooth headphones for gaming" },
    { category: "Home & Kitchen", query: "Non-stick cookware set for a family" },
    { category: "Clothing & Shoes", query: "Durable winter jacket" },
    { category: "Office Products", query: "Comfortable ergonomic office chair" },
    { category: "Sports & Outdoors", query: "Running shoes for daily jogging" },
  ],
  phones: [
    { category: "Cell Phones & Accessories", query: "Samsung phone under ₹30000 with 8GB RAM" },
    { category: "Cell Phones & Accessories", query: "Budget-friendly 5G smartphone with 128GB storage" },
    { category: "Cell Phones & Accessories", query: "Fast wireless charging pad for phones" },
  ],
  electronics: [
    { category: "Electronics", query: "Wireless Bluetooth headphones for gaming" },
    { category: "Electronics", query: "Noise-cancelling wireless earbuds with mic" },
    { category: "Electronics", query: "Portable Bluetooth speaker with deep bass" },
  ],
  home: [
    { category: "Home & Kitchen", query: "Non-stick cookware set for a family" },
    { category: "Home & Kitchen", query: "Stainless steel kitchen knife set" },
    { category: "Home & Kitchen", query: "Air fryer for quick healthy cooking" },
  ],
  clothing: [
    { category: "Clothing & Shoes", query: "Durable winter jacket" },
    { category: "Clothing & Shoes", query: "Waterproof hiking footwear" },
    { category: "Clothing & Shoes", query: "Casual everyday cotton t-shirts" },
  ],
  office: [
    { category: "Office Products", query: "Comfortable ergonomic office chair" },
    { category: "Office Products", query: "Adjustable height standing desk" },
    { category: "Office Products", query: "Mesh desk organizer and office accessories" },
  ],
  sports: [
    { category: "Sports & Outdoors", query: "Running shoes for daily jogging" },
    { category: "Sports & Outdoors", query: "Adjustable dumbbells set for home gym" },
    { category: "Sports & Outdoors", query: "Durable waterproof tent for outdoor camping" },
  ],
};
