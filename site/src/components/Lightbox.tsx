import React, { useEffect } from "react";
import { X } from "lucide-react";

interface LightboxProps {
  imageUrl: string;
  title: string;
  onClose: () => void;
}

export const Lightbox: React.FC<LightboxProps> = ({ imageUrl, title, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="lightbox-overlay" onClick={onClose}>
      <div className="lightbox-container" onClick={(e) => e.stopPropagation()}>
        <button className="lightbox-close" onClick={onClose} aria-label="Закрыть">
          <X size={28} />
        </button>
        <img src={imageUrl} alt={title} className="lightbox-image" />
        <div className="lightbox-title">{title}</div>
      </div>
    </div>
  );
};
