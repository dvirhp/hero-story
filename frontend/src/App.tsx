import { useEffect, useRef, useState } from "react";
import type { Language, StoryService } from "./api/contracts";
import { createMockStoryService, makeSample } from "./api/mock";
import { initialDraft } from "./domain/brief";
import { useStory } from "./hooks/useStory";
import { locales, messages } from "./i18n/locales";
import { GardenArt } from "./components/GardenArt";
import { StoryForm } from "./components/StoryForm";
import { StoryReader } from "./components/StoryReader";
const mockService = createMockStoryService();
export function App({ service = mockService }: { service?: StoryService }) {
  const [locale, setLocale] = useState<Language>("en");
  const [draft, setDraft] = useState(initialDraft);
  const { state, navigate, generate } = useStory(service);
  const c = messages[locale];
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locales[locale].direction;
  }, [locale]);
  useEffect(() => {
    content.current?.focus();
    window.scrollTo?.({ top: 0, behavior: "instant" });
  }, [state.screen]);
  const create = () => navigate({ screen: "create" });
  const sample = () =>
    navigate({
      screen: "reader",
      story: makeSample({
        schema_version: "2",
        display_name: locale === "he" ? "נועם" : "Alex",
        age_months: 36,
        language: locale,
        theme: "A moonlit garden",
        page_count: 6,
        story_type: "bedtime",
        text_density: "standard",
      }),
    });
  return (
    <>
      <a className="skip-link" href="#main-content">
        {locale === "he" ? "דילוג לתוכן" : "Skip to content"}
      </a>
      <header className="site-header container">
        <button
          className="brand"
          aria-label={`StoryForge · ${c.home}`}
          onClick={() => navigate({ screen: "landing" })}
        >
          <span className="brand-icon" aria-hidden="true">
            ✧
          </span>
          <span>
            story<span className="brand-forge">forge</span>
            <small>{c.tagline}</small>
          </span>
        </button>
        <div className="header-actions">
          <label className="sr-only" htmlFor="ui-language">
            {c.uiLanguage}
          </label>
          <select
            id="ui-language"
            value={locale}
            onChange={(e) => setLocale(e.target.value as Language)}
          >
            {Object.entries(locales).map(([code, item]) => (
              <option key={code} value={code} lang={code}>
                {item.label}
              </option>
            ))}
          </select>
          {state.screen === "landing" && (
            <button className="button primary header-cta" onClick={create}>
              {c.create} <span aria-hidden="true">✧</span>
            </button>
          )}
        </div>
      </header>
      <div
        id="main-content"
        ref={content}
        tabIndex={-1}
        className="main-content"
      >
        {state.screen === "landing" && (
          <main>
            <section className="hero container">
              <div className="hero-copy">
                <p className="eyebrow">
                  <span className="tiny-star" aria-hidden="true">
                    ✦
                  </span>{" "}
                  {c.eyebrow}
                </p>
                <h1>
                  {c.heroA}
                  <br />
                  <em>{c.heroB}</em>
                </h1>
                <p className="hero-description">{c.heroText}</p>
                <div className="hero-actions">
                  <button className="button primary" onClick={create}>
                    {c.create}
                    <span aria-hidden="true">✧</span>
                  </button>
                  <button className="text-button" onClick={sample}>
                    {c.sample}
                    <span className="directional-arrow" aria-hidden="true">
                      ↗
                    </span>
                  </button>
                </div>
                <p className="demo-label">
                  <span aria-hidden="true">◌</span> {c.demoNote}
                </p>
              </div>
              <div className="hero-art">
                <GardenArt />
                <div className="art-caption">
                  <span aria-hidden="true">✧</span>
                  {c.badge}
                </div>
                <span className="art-side-note" aria-hidden="true">
                  ONCE UPON A YOU
                </span>
              </div>
            </section>
            <section
              className="features container"
              aria-labelledby="features-heading"
            >
              <div className="feature-heading">
                <span aria-hidden="true">✧</span>
                <h2 id="features-heading">{c.scroll}</h2>
              </div>
              <div className="feature-grid">
                {[
                  [c.feature1, c.feature1Text, "01"],
                  [c.feature2, c.feature2Text, "02"],
                  [c.feature3, c.feature3Text, "03"],
                ].map(([title, text, num]) => (
                  <article key={num}>
                    <span className="feature-number">{num}</span>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </article>
                ))}
              </div>
            </section>
          </main>
        )}
        {state.screen === "create" && (
          <StoryForm
            draft={draft}
            onChange={setDraft}
            onSubmit={generate}
            copy={c}
            locale={locale}
          />
        )}
        {state.screen === "loading" && (
          <main className="state-screen container" aria-busy="true">
            <div className="loading-orbit" aria-hidden="true">
              ✧
            </div>
            <div role="status">
              <p className="eyebrow">{c.demo}</p>
              <h1>{c.loadingTitle}</h1>
              <p>{c.loadingText}</p>
              <ul className="loading-steps">
                <li>{c.stage1}</li>
                <li>{c.stage2}</li>
                <li>{c.stage3}</li>
              </ul>
              <p className="hint">{c.loadingNote}</p>
            </div>
            <button className="text-button" onClick={create}>
              {c.cancel}
            </button>
          </main>
        )}
        {state.screen === "error" && (
          <main className="state-screen container">
            <div className="state-symbol" aria-hidden="true">
              ☁
            </div>
            <div role="alert">
              <h1>{c.errorTitle}</h1>
              <p>{c.errorText}</p>
            </div>
            <button className="button primary" onClick={create}>
              {c.edit}
            </button>
          </main>
        )}
        {state.screen === "reader" && (
          <StoryReader story={state.story} copy={c} onCreate={create} />
        )}
      </div>
      <footer className="site-footer container">
        <span>
          storyforge <span aria-hidden="true">✧</span> {c.footer}
        </span>
        <details>
          <summary>{c.demoControls}</summary>
          <div className="demo-controls">
            <button
              className="text-button"
              onClick={() => navigate({ screen: "error" })}
            >
              {c.demoError}
            </button>
            <button
              className="text-button"
              onClick={() => navigate({ screen: "reader", story: null })}
            >
              {c.demoEmpty}
            </button>
          </div>
        </details>
      </footer>
    </>
  );
}
