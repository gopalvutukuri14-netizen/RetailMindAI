import { useState, useRef, useEffect } from "react";
import "./ProfileSelector.css";

const PROFILES = [
  {
    id: "anonymous",
    label: "Standard Search",
    desc: "No personalization profile",
    avatarClass: "profile-selector__avatar--anonymous",
    initials: "✦",
  },
  {
    id: "budget_conscious",
    label: "Budget Conscious",
    desc: "Prefers items under ₹10,000",
    avatarClass: "profile-selector__avatar--budget",
    initials: "B",
  },
  {
    id: "camera_focused",
    label: "Quality & Optics",
    desc: "Prioritizes camera & build quality",
    avatarClass: "profile-selector__avatar--camera",
    initials: "Q",
  },
  {
    id: "samsung_loyalist",
    label: "Brand Loyalist",
    desc: "Prefers Samsung brand items",
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
        aria-haspopup="true"
        aria-expanded={isOpen}
        title="Personalization Profile"
      >
        <span className={`profile-selector__avatar ${active.avatarClass}`}>
          {active.initials}
        </span>
        <span className="profile-selector__label">{active.label}</span>
        <span
          className={`profile-selector__chevron ${
            isOpen ? "profile-selector__chevron--open" : ""
          }`}
        >
          ▾
        </span>
      </button>

      {isOpen && (
        <div className="profile-selector__dropdown" role="menu">
          <div className="profile-selector__dropdown-header">
            Shopping Persona
          </div>
          {PROFILES.map((profile) => (
            <button
              key={profile.id}
              role="menuitem"
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
              <span className="profile-selector__option-content">
                <span className="profile-selector__option-title">{profile.label}</span>
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
