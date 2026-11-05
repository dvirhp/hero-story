import type { Art } from "../domain/book";
import type { CSSProperties } from "react";
import { CharacterPreview } from "../personalization/CharacterPreview";
import type { Character } from "../personalization/character";
const darkInk = "#253c42";
const lightInk = "#fff5d8";
function relativeLuminance(color: string) {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const channel = parseInt(color.slice(i, i + 2), 16) / 255;
    return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  });
  return r! * 0.2126 + g! * 0.7152 + b! * 0.0722;
}
export function contrastRatio(a: string, b: string) {
  const [lighter, darker] = [relativeLuminance(a), relativeLuminance(b)].sort(
    (x, y) => y - x,
  );
  return (lighter + 0.05) / (darker + 0.05);
}
/** Pick the higher-contrast title ink for the actual cover colour. */
export function coverInk(color: string) {
  const resolved = /^#[0-9a-f]{6}$/i.test(color) ? color : "#b7cfc1";
  return contrastRatio(resolved, lightInk) > contrastRatio(resolved, darkInk)
    ? lightInk
    : darkInk;
}
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
  return (
    <div
      className={`book-cover ${small ? "small" : ""}`}
      style={
        {
          backgroundColor: resolvedColor,
          "--cover-ink": coverInk(resolvedColor),
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
