import type { ProductCopy } from "../i18n/product";
export function Info({
  page,
  p,
}: {
  page: "about" | "help" | "privacy" | "not-found";
  p: ProductCopy;
}) {
  return (
    <main className="info-page container">
      <p className="eyebrow">STORYFORGE · ✦</p>
      {page === "about" ? (
        <>
          <h1>{p.aboutTitle}</h1>
          <img className="about-art" src="/art/family.svg" alt="" />
          <p>{p.aboutText}</p>
          <p>{p.aboutSecond}</p>
          <a href="#/books" className="button primary">
            {p.browse} ↗
          </a>
        </>
      ) : page === "help" ? (
        <>
          <h1>{p.helpTitle}</h1>
          {[
            [p.faq1, p.answer1],
            [p.faq2, p.answer2],
            [p.faq3, p.answer3],
            [p.faq4, p.answer4],
            [p.faq5, p.answer5],
          ].map(([question, answer]) => (
            <details className="faq-item" key={question}>
              <summary>{question}</summary>
              <p>{answer}</p>
            </details>
          ))}
        </>
      ) : page === "privacy" ? (
        <>
          <h1>{p.privacy}</h1>
          <p>{p.privacyText}</p>
        </>
      ) : (
        <>
          <h1>{p.notFound}</h1>
          <a href="#/" className="button primary">
            {p.goHome}
          </a>
        </>
      )}
    </main>
  );
}
