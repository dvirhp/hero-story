import type { Art } from "../domain/book";
import type { CSSProperties } from "react";
import {CharacterPreview} from '../personalization/CharacterPreview';
import type {Character} from '../personalization/character';
export function BookCover({
  title,
  art,
  color,
  language = "en",
  small = false,
  character,
}: {
  title: string;
  art: Art;
  color?: string;
  language?: string;
  small?: boolean;
  character?:Character;
}) {
  const resolvedColor = color || "#b7cfc1";
  const channels = [1, 3, 5]
    .map((i) => parseInt(resolvedColor.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  const luminance =
    channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  return (
    <div
      className={`book-cover ${small ? "small" : ""}`}
      style={
        {
          backgroundColor: resolvedColor,
          "--cover-ink": luminance < 0.28 ? "#fff5d8" : "#253c42",
        } as CSSProperties
      }
      lang={language}
      dir={language === "he" ? "rtl" : "ltr"}
    >
      <img src={`/art/${art}.svg`} alt="" loading="lazy" />
      {character&&<div className="cover-avatar"><CharacterPreview character={character}/></div>}
      <div className="cover-heading">
        <span className="cover-imprint">STORYFORGE ORIGINALS</span>
        <strong>{title}</strong>
      </div>
      <span className="cover-seal" aria-hidden="true">
        ✦
      </span>
      <div className="book-spine" />
    </div>
  );
}
