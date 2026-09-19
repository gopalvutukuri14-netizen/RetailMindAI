import { useState, useRef, useEffect } from "react";
import "./ProfileSelector.css";

const PROFILES = [
  {
    id: "anonymous",
    label: "Anonymous",
    desc: "No personalization",
    avatarClass: "profile-selector__avatar--anonymous",
    initials: "?",
  },
  {
    id: "budget_conscious",
    label: "Budget Conscious",
    desc: "Prefers phones under \u20B910,000",
    avatarClass: "profile-selector__avatar--budget",
    initials: "B",
  },
  {
    id: "camera_focused",
    label: "Camera Focused",
    desc: "Prioritizes good camera",
    avatarClass: "profile-selector__avatar--camera",
    initials: "C",
  },
  {
    id: "samsung_loyalist",
    label: "Samsung Loyalist",
    desc: "Prefers Samsung brand",
    avatarClass: "profile-selector__avatar--samsung",
    initials: "S",
  },
];

export default function ProfileSelector({ activeProfileId, onProfileChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef(null);

  const active = PROFILES.find((p) => p.id === activeProfileId) || PROFILES[0];

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="profile-selector" ref={ref}>
      <button
        className="profile-selector__trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className={`profile-selector__avatar ${active.avatarClass}`}>
          {active.initials}
        </span>
        {active.label}
        <span
          className={`profile-selector__chevron ${isOpen ? "profile-selector__chevron--open" : ""}`}
        >
          &#9662;
        </span>
      </button>

      {isOpen && (
        <div className="profile-selector__dropdown">
          {PROFILES.map((profile) => (
            <button
              key={profile.id}
              className={`profile-selector__option ${
                profile.id === activeProfileId
                  ? "profile-selector__option--active"
                  : ""
              }`}
              onClick={() => {
                onProfileChange(profile.id);
                setIsOpen(false);
              }}
            >
              <span
                className={`profile-selector__avatar ${profile.avatarClass}`}
              >
                {profile.initials}
              </span>
              <span>
                {profile.label}
                <span className="profile-selector__option-desc">
                  {profile.desc}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
