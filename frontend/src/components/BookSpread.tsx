import { readingDirection } from "../i18n/registry";
import type { BookPage } from "../domain/book";
import type { Language } from "../api/contracts";
import { CharacterPreview } from "../personalization/CharacterPreview";
export function BookSpread({
  page,
  language,
  emptyText = "",
  preview = false,
}: {
  page: BookPage;
  language: Language;
  emptyText?: string;
  preview?: boolean;
}) {
  return (
    <div
      className={`book-spread layout-${page.layout} page-${page.background} ${preview ? "is-preview" : ""}`}
      lang={language}
      dir={readingDirection(language)}
    >
      {page.layout !== "text" && (
        <div className="spread-art">
          {page.illustration ? (
            <img
              src={`/art/${page.illustration}.svg`}
              alt=""
              data-positioned={page.imageFrame ? true : undefined}
              style={
                page.imageFrame
                  ? {
                      width: `${page.imageFrame.scale}%`,
                      height: `${page.imageFrame.scale}%`,
                      left: `${Math.max(page.imageFrame.scale / 2, Math.min(100 - page.imageFrame.scale / 2, page.imageFrame.x))}%`,
                      top: `${Math.max(page.imageFrame.scale / 2, Math.min(100 - page.imageFrame.scale / 2, page.imageFrame.y))}%`,
                      transform: "translate(-50%,-50%)",
                    }
                  : undefined
              }
            />
          ) : (
            <div className="blank-art" aria-hidden="true">
              ✧
            </div>
          )}
          {page.character && (
            <div className="page-avatar">
              <CharacterPreview character={page.character} />
            </div>
          )}
        </div>
      )}
      <div className="spread-words">
        <span className="page-ornament" aria-hidden="true">
          ✧
        </span>
        <div>
          {page.sentenceUnits.some((unit) => unit.trim()) ? (
            page.sentenceUnits.map((text, i) => <p key={i}>{text}</p>)
          ) : (
            <p className="empty-prose">{emptyText}</p>
          )}
        </div>
        <span className="printed-page">{page.pageNumber}</span>
      </div>
    </div>
  );
}
