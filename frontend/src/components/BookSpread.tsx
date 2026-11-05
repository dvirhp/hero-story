import type { BookPage } from "../domain/book";
import type { Language } from "../api/contracts";
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
      dir={language === "he" ? "rtl" : "ltr"}
    >
      {page.layout !== "text" && (
        <div className="spread-art">
          {page.illustration ? (
            <img src={`/art/${page.illustration}.svg`} alt="" />
          ) : (
            <div className="blank-art" aria-hidden="true">
              ✧
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
