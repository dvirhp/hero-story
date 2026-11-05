import { useState } from "react";
import type { Book } from "../domain/book";
import type { Language } from "../api/contracts";
import type { ProductCopy } from "../i18n/product";
import { BookCover } from "../components/BookCover";
export function Library({
  books,
  locale,
  p,
  onRemove,
}: {
  books: Book[];
  locale: Language;
  p: ProductCopy;
  onRemove: (id: string) => void;
}) {
  const [filter, setFilter] = useState<"all" | "ready" | "draft" | "failed">(
    "all",
  );
  const [removing, setRemoving] = useState<string | null>(null);
  const visible = books.filter(
    (book) => filter === "all" || book.status === filter,
  );
  const date = new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeZone: "Asia/Jerusalem",
  });
  return (
    <main>
      <section className="page-banner lavender">
        <div className="container">
          <p className="eyebrow">{p.library}</p>
          <h1>{p.libraryTitle}</h1>
          <p>{p.libraryIntro}</p>
          <a className="button primary" href="#/studio/new">
            {p.manual} ✎
          </a>
        </div>
      </section>
      <section className="container section">
        <div className="category-chips">
          {(["all", "ready", "draft", "failed"] as const).map((status) => (
            <button
              key={status}
              aria-pressed={filter === status}
              onClick={() => setFilter(status)}
            >
              {p[status]}
            </button>
          ))}
        </div>
        {visible.length ? (
          <div className="book-grid library-grid">
            {visible.map((book) => (
              <article className="library-card" key={book.id}>
                <a
                  href={
                    book.status === "draft"
                      ? `#/studio/${book.id}`
                      : `#/read/${book.id}`
                  }
                  className="library-cover"
                >
                  <BookCover
                    title={book.title || p.untitled}
                    art={book.cover}
                    color={book.coverColor}
                    language={book.language}
                  />
                  <span className={`status-badge ${book.status}`}>
                    {p[book.status]}
                  </span>
                </a>
                <h2 dir="auto">{book.title || p.untitled}</h2>
                <p className="hint">
                  {p.created} {date.format(new Date(book.createdAt))}
                </p>
                <a
                  className="inline-link"
                  href={
                    book.status === "draft"
                      ? `#/studio/${book.id}`
                      : `#/read/${book.id}`
                  }
                >
                  {book.status === "draft" ? p.continueEditing : p.read}
                  <span aria-hidden="true">↗</span>
                </a>
                {book.method === "MANUAL" && book.status === "ready" && (
                  <a className="text-button" href={`#/studio/${book.id}`}>
                    {p.edit}
                  </a>
                )}
                <button
                  className="remove-book"
                  onClick={() => setRemoving(book.id)}
                  aria-label={`${p.remove}: ${book.title}`}
                >
                  ×
                </button>
                {removing === book.id && (
                  <div
                    className="remove-confirm"
                    role="group"
                    aria-label={p.removeConfirm}
                  >
                    <p>{p.removeConfirm}</p>
                    <button
                      className="button secondary"
                      onClick={() => setRemoving(null)}
                    >
                      {p.cancel}
                    </button>
                    <button
                      className="button danger"
                      onClick={() => {
                        onRemove(book.id);
                        setRemoving(null);
                      }}
                    >
                      {p.confirmRemove}
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-panel">
            <span aria-hidden="true">▤</span>
            <h2>{p.emptyLibrary}</h2>
            <p>{p.emptyLibraryText}</p>
            <a className="button primary" href="#/books">
              {p.browse}
            </a>
          </div>
        )}
      </section>
    </main>
  );
}
