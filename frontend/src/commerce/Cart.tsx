import type { CartLine } from "./model";
import { quote, unitPrice } from "./model";
import type { Language } from "../api/contracts";
import { experience, money } from "../i18n/experience";
import { BookCover } from "../components/BookCover";
export function Cart({
  lines,
  locale,
  onUpdate,
  onRemove,
}: {
  lines: CartLine[];
  locale: Language;
  onUpdate: (id: string, quantity: number) => void;
  onRemove: (id: string) => void;
}) {
  const e = experience[locale],
    totals = quote(lines);
  return (
    <main className="container commerce-page">
      <p className="eyebrow">{e.demoCommerce}</p>
      <h1>{e.cart}</h1>
      {!lines.length ? (
        <div className="empty-panel">
          <h2>{e.bagEmpty}</h2>
          <p>{e.bagEmptyText}</p>
          <a href="#/books" className="button primary">
            {e.keepShopping}
          </a>
        </div>
      ) : (
        <div className="commerce-grid">
          <section className="cart-lines">
            {lines.map((line) => (
              <article className="cart-line" key={line.id}>
                <div className="cart-cover">
                  <BookCover
                    title={line.book.title}
                    art={line.book.cover}
                    color={line.book.coverColor}
                    language={line.book.language}
                    character={line.book.character}
                  />
                </div>
                <div>
                  <h2 dir="auto">{line.book.title}</h2>
                  <p className="hint">
                    {e[line.format]} · {line.book.language.toUpperCase()} ·{" "}
                    {e.configuration}
                  </p>
                  <a className="inline-link" href={`#/read/${line.book.id}`}>
                    {e.reviewBook}
                  </a>
                  <label htmlFor={`quantity-${line.id}`}>{e.quantity}</label>
                  <select
                    id={`quantity-${line.id}`}
                    value={line.quantity}
                    onChange={(event) =>
                      onUpdate(line.id, Number(event.target.value))
                    }
                  >
                    {Array.from({ length: 10 }, (_, i) => (
                      <option key={i + 1} value={i + 1}>
                        {i + 1}
                      </option>
                    ))}
                  </select>
                  <button
                    className="text-button danger-text"
                    onClick={() => onRemove(line.id)}
                  >
                    {e.remove}
                  </button>
                </div>
                <strong>
                  <bdi>
                    {money(unitPrice(line.format) * line.quantity, locale)}
                  </bdi>
                </strong>
              </article>
            ))}
          </section>
          <aside className="order-summary">
            <h2>{e.review}</h2>
            <dl>
              <div>
                <dt>{e.subtotal}</dt>
                <dd>{money(totals.subtotalCents, locale)}</dd>
              </div>
            </dl>
            <p className="hint">{e.deliveryNote}</p>
            <p className="demo-notice">{e.demoPrices}</p>
            <a className="button primary" href="#/checkout">
              {e.checkout}
            </a>
            <a href="#/books" className="inline-link">
              {e.keepShopping}
            </a>
            <p className="hint">{e.accountNote}</p>
          </aside>
        </div>
      )}
    </main>
  );
}
