import "./FollowUpChips.css";

export default function FollowUpChips({ suggestions, onSelect }) {
  if (!suggestions?.length) return null;

  return (
    <div className="followup-chips">
      {suggestions.map((text, i) => (
        <button
          key={i}
          className="followup-chips__chip"
          onClick={() => onSelect(text)}
        >
          {text}
        </button>
      ))}
    </div>
  );
}
