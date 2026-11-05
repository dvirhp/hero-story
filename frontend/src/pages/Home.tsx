import { useState } from "react";
import type { Language } from "../api/contracts";
import type { ProductCopy } from "../i18n/product";
import { catalog, categories, ages, ageLabels } from "../data/catalog";
import { BookCard } from "../components/BookCard";
import { BookCover } from "../components/BookCover";
export function Home({ locale, p }: { locale: Language; p: ProductCopy }) {
  const [name, setName] = useState("");
  return (
    <main>
      <section className="store-hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">✦ {p.heroKicker}</p>
            <h1>
              {p.heroTitle}
              <br />
              <em>{p.heroAccent}</em>
            </h1>
            <p className="hero-description">{p.heroText}</p>
            <a href="#/books" className="button primary">
              {p.browse}
              <span aria-hidden="true">↗</span>
            </a>
            <p className="hero-footnote">✧ {p.demoCollection}</p>
          </div>
          <div className="hero-books" aria-label={p.demoCollection}>
            <div className="hero-book back">
              <BookCover
                title={catalog[1].title[locale]}
                art="moon"
                color="#414271"
                language={locale}
              />
            </div>
            <div className="hero-book front">
              <BookCover
                title={catalog[0].title[locale]}
                art="whale"
                color="#e9a08c"
                language={locale}
              />
            </div>
            <span className="hero-sticker">
              {locale === "he"
                ? "שם קטן.\nעולם שלם."
                : "A little name.\nA whole world."}
            </span>
            <span className="spark spark-one" aria-hidden="true">
              ✦
            </span>
            <span className="spark spark-two" aria-hidden="true">
              ✳
            </span>
          </div>
        </div>
      </section>
      <div className="world-nav">
        <div className="container">
          {categories.map((category, i) => (
            <a key={category} href={`#/books?category=${category}`}>
              <span aria-hidden="true">{["☁", "☾", "Aa", "ϟ", "♡"][i]}</span>
              {p[category]}
            </a>
          ))}
        </div>
      </div>
      <section className="section container" id="create">
        <div className="section-title centered">
          <p className="eyebrow">{p.methodsKicker}</p>
          <h2>{p.methodsTitle}</h2>
        </div>
        <div className="method-grid">
          {[
            {
              title: p.ai,
              text: p.aiText,
              cta: p.aiAction,
              href: "#/create/ai",
              icon: "✦",
              className: "ai",
            },
            {
              title: p.template,
              text: p.templateText,
              cta: p.templateAction,
              href: "#/books",
              icon: "▤",
              className: "template",
            },
            {
              title: p.manual,
              text: p.manualText,
              cta: p.manualAction,
              href: "#/studio/new",
              icon: "✎",
              className: "manual",
            },
          ].map((method, i) => (
            <article
              className={`method-card ${method.className}`}
              key={method.href}
            >
              <div className="method-top">
                <span className="method-icon" aria-hidden="true">
                  {method.icon}
                </span>
                <span className="method-number">0{i + 1}</span>
              </div>
              <h3>{method.title}</h3>
              <p>{method.text}</p>
              <a href={method.href} className="inline-link">
                {method.cta}
                <span aria-hidden="true">↗</span>
              </a>
            </article>
          ))}
        </div>
      </section>
      <section className="section featured-section">
        <div className="container">
          <div className="section-title">
            <div>
              <p className="eyebrow">{p.demoCollection}</p>
              <h2>{p.featured}</h2>
              <p>{p.featuredText}</p>
            </div>
            <a href="#/books" className="inline-link">
              {p.allBooks} ↗
            </a>
          </div>
          <div className="book-grid">
            {catalog.slice(0, 4).map((book) => (
              <BookCard key={book.id} book={book} locale={locale} p={p} />
            ))}
          </div>
        </div>
      </section>
      <section className="section container age-section">
        <div className="section-title centered">
          <h2>{p.ageHeading}</h2>
          <p>{p.ageText}</p>
        </div>
        <div className="age-grid">
          {ages.map((age, i) => (
            <a
              href={`#/books?age=${age}`}
              key={age}
              className={`age-card age-${i}`}
            >
              <span className="age-doodle" aria-hidden="true">
                {["☀", "❀", "✧", "☄"][i]}
              </span>
              <h3>{p[age]}</h3>
              <span>{p[ageLabels[age]]}</span>
              <span className="age-arrow" aria-hidden="true">
                ↗
              </span>
            </a>
          ))}
        </div>
      </section>
      <section className="showcase-section">
        <div className="container showcase-grid">
          <div className="showcase-book">
            <BookCover
              title={`${name || p.showcaseDefault}${locale === "he" ? " וגינת הירח" : "’s Moonlight Garden"}`}
              art="garden"
              color="#b7cfc1"
              language={locale}
            />
            <span className="showcase-note" aria-hidden="true">
              {p.showcase} ♡
            </span>
          </div>
          <div>
            <p className="eyebrow">{p.how2}</p>
            <h2>{p.showcase}</h2>
            <p>{p.showcaseText}</p>
            <label htmlFor="showcase-name">{p.showcaseLabel}</label>
            <input
              id="showcase-name"
              value={name}
              maxLength={40}
              dir="auto"
              placeholder={p.showcaseDefault}
              onChange={(e) => setName(e.target.value)}
            />
            <a href="#/personalize/moon-garden" className="button primary">
              {p.personalize} ↗
            </a>
          </div>
        </div>
      </section>
      <section className="section container">
        <div className="section-title centered">
          <p className="eyebrow">STORYFORGE</p>
          <h2>{p.how}</h2>
        </div>
        <div className="how-grid">
          {[
            [p.how1, p.how1Text, "✧"],
            [p.how2, p.how2Text, "♡"],
            [p.how3, p.how3Text, "▤"],
          ].map(([title, text, icon], i) => (
            <article key={title}>
              <span className="how-icon" aria-hidden="true">
                {icon}
              </span>
              <span className="micro-label">0{i + 1}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
