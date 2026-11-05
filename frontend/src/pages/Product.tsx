import { readingDirection } from "../i18n/registry";
import { useState } from "react";
import type { Language } from "../api/contracts";
import type { ProductCopy } from "../i18n/product";
import type { BookTemplate } from "../data/catalog";
import { ageLabels } from "../data/catalog";
import { BookCover } from "../components/BookCover";
import { experience } from "../i18n/experience";
import { CharacterPreview } from "../personalization/CharacterPreview";
import { defaultCharacter } from "../personalization/character";
export function Product({
  template: t,
  locale,
  p,
}: {
  template: BookTemplate;
  locale: Language;
  p: ProductCopy;
}) {
  const [sample, setSample] = useState(0);
  const [gallery, setGallery] = useState(0);
  const e = experience[locale];
  return (
    <main className="container product-page">
      <a className="inline-link breadcrumb" href="#/books">
        {p.discover} / {p[t.category]}
      </a>
      <div className="product-grid">
        <div className={`product-stage world-${t.art}`}>
          {gallery === 0 ? (
            <BookCover
              title={t.title[locale]}
              art={t.art}
              color={t.color}
              language={locale}
            />
          ) : gallery === 1 ? (
            <img
              className="gallery-art"
              src={`/art/${t.art}.svg`}
              alt={t.title[locale]}
            />
          ) : (
            <CharacterPreview
              character={defaultCharacter}
              label={e.appearanceSummary}
            />
          )}
          <span className="product-sticker">{p.demoProduct}</span>
          <div className="gallery-controls" role="group" aria-label={e.gallery}>
            {[
              e.galleryCover,
              e.galleryInside,
              ...(t.character ? [e.galleryCharacter] : []),
            ].map((label, i) => (
              <button
                key={label}
                aria-pressed={gallery === i}
                onClick={() => setGallery(i)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="product-copy">
          <p className="eyebrow">
            {p[t.category]} · {p.demoCollection}
          </p>
          <h1>{t.title[locale]}</h1>
          <p className="product-description">{t.description[locale]}</p>
          <div className="product-facts">
            <p>{p.ageGuidance}</p>
            <strong>
              {t.ages.map((age) => p[ageLabels[age]]).join(" · ")}
            </strong>
            <p>{e.storyLanguages}</p>
          </div>
          <a className="button primary" href={`#/personalize/${t.id}`}>
            {p.personalize} <span aria-hidden="true">✧</span>
          </a>
          <p className="hint">{p.productNote}</p>
          <a className="inline-link" href={`#/read/sample-${t.id}-${locale}`}>
            {p.preview} ↗
          </a>
        </div>
      </div>
      <section className="sample-section">
        <div className="section-title">
          <h2>{p.samplePages}</h2>
          <div className="sample-buttons">
            <button
              className="icon-button"
              aria-label={p.back}
              disabled={sample === 0}
              onClick={() => setSample(sample - 1)}
            >
              ‹
            </button>
            <button
              className="icon-button"
              aria-label={p.next}
              disabled={sample === t.pages[locale].length - 1}
              onClick={() => setSample(sample + 1)}
            >
              ›
            </button>
          </div>
        </div>
        <div
          className="sample-spread"
          lang={locale}
          dir={readingDirection(locale)}
        >
          <img src={`/art/${t.art}.svg`} alt="" />
          <div>
            <span className="page-ornament" aria-hidden="true">
              ✧
            </span>
            <p>
              {t.pages[locale][sample]
                .replaceAll("{{name}}", p.showcaseDefault)
                .replaceAll("{{companion}}", p.fox)}
            </p>
            <span className="micro-label">
              {sample + 1} / {t.pages[locale].length}
            </span>
          </div>
        </div>
      </section>
    </main>
  );
}
