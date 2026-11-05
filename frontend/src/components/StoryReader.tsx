import { useEffect, useState } from "react";
import type { Book } from "../domain/book";
import type { Copy } from "../i18n/locales";
import type { ProductCopy } from "../i18n/product";
import { BookCover } from "./BookCover";
import { BookSpread } from "./BookSpread";
export function StoryReader({
  book,
  copy: c,
  p,
  onCreate,
  saved = false,
  onSave,
}: {
  book: Book | null;
  copy: Copy;
  p: ProductCopy;
  onCreate: () => void;
  saved?: boolean;
  onSave?: () => void;
}) {
  const [index, setIndex] = useState(-1);
  useEffect(() => setIndex(-1), [book?.id]);
  useEffect(() => {
    const keys = (event: KeyboardEvent) => {
      if (
        !book ||
        event.altKey ||
        event.ctrlKey ||
        event.metaKey ||
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement ||
        event.target instanceof HTMLSelectElement
      )
        return;
      const forward = book.language === "he" ? "ArrowLeft" : "ArrowRight";
      const back = book.language === "he" ? "ArrowRight" : "ArrowLeft";
      if (event.key === forward) {
        event.preventDefault();
        setIndex((i) => Math.min(book.pages.length - 1, i + 1));
      }
      if (event.key === back) {
        event.preventDefault();
        setIndex((i) => Math.max(-1, i - 1));
      }
    };
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  }, [book]);
  if (!book?.pages.length)
    return (
      <main className="state-screen container">
        <div className="state-symbol" aria-hidden="true">
          ✧
        </div>
        <h1>{p.noBook}</h1>
        <p>{p.noBookText}</p>
        <button className="button primary" onClick={onCreate}>
          {c.create}
        </button>
        <a href="#/books" className="inline-link">
          {p.browse}
        </a>
      </main>
    );
  const page = book.pages[Math.max(0, index)];
  return (
    <main className="reader container">
      <div className="reader-heading">
        <a className="inline-link" href="#/my-books">
          {p.libraryBack}
        </a>
        <span className="micro-label">
          {book.demo ? p.demoProduct : p.ready}
        </span>
        {book.method === "MANUAL" && (
          <a className="inline-link" href={`#/studio/${book.id}`}>
            {p.continueEditing}
          </a>
        )}
        {onSave && book.method === "AI_GENERATED" && (
          <button
            className="button secondary"
            disabled={saved}
            onClick={onSave}
          >
            {saved ? p.saved : p.saveLibrary}
          </button>
        )}
      </div>
      <h1 lang={book.language} dir={book.language === "he" ? "rtl" : "ltr"}>
        {book.title || p.untitled}
      </h1>
      {index === -1 ? (
        <div className="reader-cover-scene">
          <BookCover
            title={book.title || p.untitled}
            art={book.cover}
            color={book.coverColor}
            language={book.language}
          />
          <button className="button primary" onClick={() => setIndex(0)}>
            {p.openBook} ↗
          </button>
        </div>
      ) : (
        <article
          className="reader-book"
          lang={book.language}
          dir={book.language === "he" ? "rtl" : "ltr"}
          aria-label={`${c.page} ${index + 1}`}
          aria-live="polite"
          aria-atomic="true"
        >
          <BookSpread page={page} language={book.language} />
        </article>
      )}
      <nav className="reader-navigation" aria-label={p.readerProgress}>
        <button
          className="button secondary"
          disabled={index === -1}
          onClick={() => setIndex(index - 1)}
        >
          {index === 0 ? p.backCover : c.previous}
        </button>
        <span className="page-counter" role="status">
          {index === -1
            ? p.cover
            : `${c.page} ${index + 1} ${c.of} ${book.pages.length}`}
        </span>
        <button
          className="button secondary"
          disabled={index === book.pages.length - 1}
          onClick={() => setIndex(index + 1)}
        >
          {index === -1 ? p.openBook : c.next}
        </button>
      </nav>
      <progress
        className="reading-progress"
        value={index + 1}
        max={book.pages.length}
        aria-label={p.readerProgress}
      />
      <p className="hint reader-keyboard-help">{p.keyboardHelp}</p>
      <div className="reader-end">
        <button className="text-button" onClick={onCreate}>
          {c.startOver} ✧
        </button>
      </div>
    </main>
  );
}
