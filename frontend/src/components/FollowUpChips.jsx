import "./FollowUpChips.css";

export default function FollowUpChips({ suggestions, onSelect }) {
  if (!suggestions?.length) return null;

  return (
    <div className="followup-chips" role="group" aria-label="Follow-up action suggestions">
      {suggestions.map((text, i) => (
        <button
          key={i}
          type="button"
          className="followup-chips__chip"
          onClick={() => onSelect(text)}
        >
          <span className="followup-chips__text">{text}</span>
          <span className="followup-chips__arrow" aria-hidden="true">→</span>
        </button>
      ))}
    </div>
  );
}
