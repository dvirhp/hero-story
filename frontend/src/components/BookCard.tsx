import type { BookTemplate } from "../data/catalog";
import { ageLabels } from "../data/catalog";
import type { Language } from "../api/contracts";
import type { ProductCopy } from "../i18n/product";
import { BookCover } from "./BookCover";
export function BookCard({
  book,
  locale,
  p,
}: {
  book: BookTemplate;
  locale: Language;
  p: ProductCopy;
}) {
  return (
    <article className={`book-card world-${book.art}`}>
      <a
        className="book-card-art"
        href={`#/books/${book.id}`}
        title={p.details}
      >
        <BookCover
          title={book.title[locale]}
          art={book.art}
          color={book.color}
          language={locale}
        />
        <span className="card-peek">
          {p.preview} <span aria-hidden="true">↗</span>
        </span>
      </a>
      <div className="book-card-info">
        <p className="micro-label">
          {p[book.category]} <span>·</span> {p[ageLabels[book.ages[0]]]}
        </p>
        <h3>
          <a href={`#/books/${book.id}`}>{book.title[locale]}</a>
        </h3>
        <p>{book.description[locale]}</p>
        <a className="inline-link" href={`#/personalize/${book.id}`}>
          {p.personalize} <span aria-hidden="true">↗</span>
        </a>
      </div>
    </article>
  );
}
