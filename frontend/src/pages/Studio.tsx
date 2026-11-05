import { useEffect, useState } from "react";
import type { Language } from "../api/contracts";
import type {
  Art,
  Book,
  BookPage,
  PageColor,
  PageLayout,
} from "../domain/book";
import { blankPage, canFinalize, movePage, reindex } from "../domain/book";
import type { ProductCopy } from "../i18n/product";
import { locales } from "../i18n/locales";
import { BookSpread } from "../components/BookSpread";
const artOptions: Exclude<Art, "hero-striped">[] = [
  "garden",
  "whale",
  "moon",
  "alphabet",
  "hero",
  "family",
];
export function Studio({
  book,
  p,
  locale,
  onChange,
  onSave,
  onPreview,
}: {
  book: Book;
  p: ProductCopy;
  locale: Language;
  onChange: (book: Book) => void;
  onSave: (book: Book, final: boolean) => void;
  onPreview: (book: Book) => void;
}) {
  const [selected, setSelected] = useState(0);
  const [notice, setNotice] = useState<"clean" | "saved" | "invalid" | "dirty">(
    "clean",
  );
  const index = Math.min(selected, book.pages.length - 1);
  const page = book.pages[index];
  const change = (next: Book) => {
    onChange({ ...next, status: "draft", updatedAt: new Date().toISOString() });
    setNotice("dirty");
  };
  const patch = (values: Partial<BookPage>) =>
    change({
      ...book,
      pages: book.pages.map((item, i) =>
        i === index ? { ...item, ...values } : item,
      ),
    });
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (notice === "dirty") {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [notice]);
  const save = (final: boolean) => {
    if (final && !canFinalize(book)) {
      setNotice("invalid");
      return;
    }
    onSave(
      {
        ...book,
        status: final ? "ready" : "draft",
        updatedAt: new Date().toISOString(),
      },
      final,
    );
    setNotice("saved");
  };
  return (
    <main className="studio-page container">
      <div className="studio-heading">
        <div>
          <p className="eyebrow">{p.editorKicker}</p>
          <h1>{p.editorTitle}</h1>
        </div>
        <a href="#/my-books" className="inline-link">
          {p.library} ↗
        </a>
      </div>
      <p className="intro">{p.editorNote}</p>
      <div className="studio-metadata">
        <div className="field">
          <label htmlFor="book-title">{p.bookTitle}</label>
          <input
            id="book-title"
            value={book.title}
            maxLength={120}
            dir="auto"
            placeholder={p.untitled}
            onChange={(e) => change({ ...book, title: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="manual-language">{p.language}</label>
          <select
            id="manual-language"
            value={book.language}
            onChange={(e) =>
              change({ ...book, language: e.target.value as Language })
            }
          >
            {Object.entries(locales).map(([key, item]) => (
              <option key={key} value={key}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="manual-child">{p.optionalChild}</label>
          <input
            id="manual-child"
            maxLength={40}
            value={book.childName || ""}
            dir="auto"
            onChange={(e) => change({ ...book, childName: e.target.value })}
          />
        </div>
      </div>
      <div className="studio-layout">
        <aside className="page-rail">
          <h2>
            {p.pages} <span>{book.pages.length}</span>
          </h2>
          <ol>
            {book.pages.map((item, i) => (
              <li key={item.pageId}>
                <button
                  className="page-thumbnail"
                  aria-label={`${p.pages} ${i + 1}`}
                  aria-current={index === i ? "page" : undefined}
                  onClick={() => setSelected(i)}
                >
                  <span>{i + 1}</span>
                  {item.illustration && item.layout !== "text" ? (
                    <img src={`/art/${item.illustration}.svg`} alt="" />
                  ) : (
                    <span className="thumbnail-lines" aria-hidden="true">
                      ☰
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ol>
          <button
            className="button secondary"
            disabled={book.pages.length >= 32}
            onClick={() => {
              change({ ...book, pages: reindex([...book.pages, blankPage()]) });
              setSelected(book.pages.length);
            }}
          >
            {p.addPage} +
          </button>
          <p className="hint">{p.editorLimit}</p>
        </aside>
        <div className="studio-canvas">
          <BookSpread
            page={page}
            language={book.language}
            emptyText={p.textPlaceholder}
            preview
          />
          <div className="page-tools">
            <button
              className="button secondary"
              disabled={index === 0}
              onClick={() => {
                change(movePage(book, index, index - 1));
                setSelected(index - 1);
              }}
            >
              {p.moveEarlier}
            </button>
            <button
              className="button secondary"
              disabled={index === book.pages.length - 1}
              onClick={() => {
                change(movePage(book, index, index + 1));
                setSelected(index + 1);
              }}
            >
              {p.moveLater}
            </button>
            <button
              className="text-button danger-text"
              disabled={book.pages.length === 1}
              onClick={() => {
                change({
                  ...book,
                  pages: reindex(book.pages.filter((_, i) => i !== index)),
                });
                setSelected(Math.max(0, index - 1));
              }}
            >
              {p.removePage}
            </button>
          </div>
          <div className="page-controls">
            <div className="field">
              <label htmlFor="page-text">
                {p.pageText} · {index + 1}
              </label>
              <textarea
                id="page-text"
                value={page.sentenceUnits.join("\n")}
                dir={book.language === "he" ? "rtl" : "ltr"}
                lang={book.language}
                rows={5}
                maxLength={12000}
                placeholder={p.textPlaceholder}
                onChange={(e) =>
                  patch({ sentenceUnits: e.target.value.split("\n") })
                }
              />
            </div>
            <div className="two-columns">
              <div className="field">
                <label htmlFor="page-layout">{p.layout}</label>
                <select
                  id="page-layout"
                  value={page.layout}
                  onChange={(e) =>
                    patch({ layout: e.target.value as PageLayout })
                  }
                >
                  <option value="split">{p.split}</option>
                  <option value="full">{p.full}</option>
                  <option value="text">{p.textOnly}</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="page-color">{p.background}</label>
                <select
                  id="page-color"
                  value={page.background}
                  onChange={(e) =>
                    patch({ background: e.target.value as PageColor })
                  }
                >
                  {(["cream", "mint", "pink", "lavender", "sky"] as const).map(
                    (value, i) => (
                      <option key={value} value={value}>
                        {locale === "he"
                          ? ["שמנת", "מנטה", "ורוד", "לבנדר", "תכלת"][i]
                          : [
                              "Cream",
                              "Mint",
                              "Coral pink",
                              "Lavender",
                              "Sky blue",
                            ][i]}
                      </option>
                    ),
                  )}
                </select>
              </div>
            </div>
            <fieldset className="illustration-picker">
              <legend>{p.illustration}</legend>
              <button
                type="button"
                aria-pressed={page.illustration === null}
                onClick={() => patch({ illustration: null })}
              >
                {p.none}
              </button>
              {artOptions.map((art) => (
                <button
                  type="button"
                  key={art}
                  aria-pressed={page.illustration === art}
                  aria-label={
                    locale === "he"
                      ? {
                          garden: "גינה",
                          whale: "לווייתן",
                          moon: "ירח",
                          alphabet: "אותיות",
                          hero: "גיבור־על",
                          family: "משפחה",
                        }[art]
                      : art
                  }
                  onClick={() => patch({ illustration: art })}
                >
                  <img src={`/art/${art}.svg`} alt="" />
                </button>
              ))}
            </fieldset>
          </div>
        </div>
      </div>
      <div className="studio-bottom">
        <p
          role="status"
          className={notice === "invalid" ? "field-error" : "hint"}
        >
          {notice === "invalid"
            ? p.editorValidation
            : notice === "saved"
              ? p.editorSaved
              : p.notSaved}
        </p>
        <div>
          <button className="button secondary" onClick={() => save(false)}>
            {p.saveDraft}
          </button>
          <button className="button secondary" onClick={() => onPreview(book)}>
            {p.editorPreview}
          </button>
          <button className="button primary" onClick={() => save(true)}>
            {p.finalize} ✧
          </button>
        </div>
      </div>
    </main>
  );
}
