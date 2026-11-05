import { useState } from "react";
import type { Language } from "../api/contracts";
import { catalog, categories, ages, ageLabels } from "../data/catalog";
import type { AgeGroup, Category } from "../data/catalog";
import { BookCard } from "../components/BookCard";
import { locales } from "../i18n/locales";
import type { ProductCopy } from "../i18n/product";
export function Discover({ locale, p }: { locale: Language; p: ProductCopy }) {
  const query = new URLSearchParams(location.hash.split("?")[1]);
  const [category, setCategory] = useState(query.get("category") || "all");
  const [age, setAge] = useState(query.get("age") || "all");
  const [search, setSearch] = useState("");
  const [language, setLanguage] = useState<Language>(locale);
  const results = catalog.filter(
    (book) =>
      (category === "all" || book.category === category) &&
      (age === "all" || book.ages.includes(age as AgeGroup)) &&
      book.languages.includes(language) &&
      `${book.title[locale]} ${book.description[locale]}`
        .toLocaleLowerCase()
        .includes(search.toLocaleLowerCase()),
  );
  const reset = () => {
    setCategory("all");
    setAge("all");
    setSearch("");
  };
  return (
    <main>
      <section className="page-banner mint">
        <div className="container">
          <p className="eyebrow">{p.demoCollection}</p>
          <h1>{p.catalogTitle}</h1>
          <p>{p.catalogIntro}</p>
        </div>
      </section>
      <div className="container catalog-section">
        <div className="catalog-filters">
          <div className="search-field">
            <label htmlFor="catalog-search">{p.search}</label>
            <input
              id="catalog-search"
              type="search"
              placeholder={p.searchPlaceholder}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="catalog-age">{p.ageFilter}</label>
            <select
              id="catalog-age"
              value={age}
              onChange={(e) => setAge(e.target.value)}
            >
              <option value="all">{p.all}</option>
              {ages.map((group) => (
                <option key={group} value={group}>
                  {p[ageLabels[group]]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="catalog-language">{p.language}</label>
            <select
              id="catalog-language"
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
            >
              {Object.entries(locales).map(([key, item]) => (
                <option key={key} value={key}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="category-chips" aria-label={p.category}>
          {(["all", ...categories] as ("all" | Category)[]).map((item) => (
            <button
              key={item}
              aria-pressed={category === item}
              onClick={() => setCategory(item)}
            >
              {p[item]}
            </button>
          ))}
        </div>
        <p className="result-count" role="status">
          {results.length} {p.results}
        </p>
        {results.length ? (
          <div className="book-grid catalog-grid">
            {results.map((book) => (
              <BookCard key={book.id} book={book} locale={locale} p={p} />
            ))}
          </div>
        ) : (
          <div className="empty-panel">
            <span aria-hidden="true">✧</span>
            <h2>{p.noResults}</h2>
            <button className="button secondary" onClick={reset}>
              {p.clearFilters}
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
