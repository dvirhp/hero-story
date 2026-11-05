import { useEffect, useRef, useState } from "react";
import type { Language, StoryRequestV2, StoryService } from "./api/contracts";
import { createMockStoryService } from "./api/mock";
import { initialDraft } from "./domain/brief";
import type { Book } from "./domain/book";
import { bookFromStory, createBlankBook } from "./domain/book";
import { useStory } from "./hooks/useStory";
import { useLibrary } from "./hooks/useLibrary";
import { locales, messages } from "./i18n/locales";
import { productCopy } from "./i18n/product";
import { catalog, sampleBook } from "./data/catalog";
import { go, useRoute } from "./routing/router";
import { Home } from "./pages/Home";
import { Discover } from "./pages/Discover";
import { Product } from "./pages/Product";
import { Personalize } from "./pages/Personalize";
import { Library } from "./pages/Library";
import { Studio } from "./pages/Studio";
import { Info } from "./pages/Info";
import { StoryForm } from "./components/StoryForm";
import { StoryReader } from "./components/StoryReader";
const mockService = createMockStoryService(2200);
export function App({ service = mockService }: { service?: StoryService }) {
  const [locale, setLocale] = useState<Language>("en");
  const [draft, setDraft] = useState(initialDraft);
  const [menuOpen, setMenuOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [transient, setTransient] = useState<Book | null>(null);
  const [working, setWorking] = useState<Book>(() => createBlankBook("en"));
  const { route, key } = useRoute();
  const { books, save, remove } = useLibrary();
  const { generate, cancel } = useStory(service);
  const c = messages[locale];
  const p = productCopy[locale];
  const content = useRef<HTMLDivElement>(null);
  const previousRoute = useRef(key);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButton.current?.focus();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = locales[locale].direction;
  }, [locale]);
  useEffect(() => {
    setMenuOpen(false);
    if (previousRoute.current !== key) content.current?.focus();
    previousRoute.current = key;
    window.scrollTo?.({ top: 0, behavior: "instant" });
    if (route.page !== "loading") {
      cancel();
      setGenerating(false);
    }
    document.title = `StoryForge · ${route.page === "home" ? p.footerLine : route.page === "library" ? p.library : route.page === "editor" ? p.manual : route.page === "create" ? p.ai : p.discover}`;
  }, [key]);
  useEffect(() => {
    if (route.page === "editor" && route.id === "new") {
      const book = createBlankBook(locale);
      setWorking(book);
      history.replaceState(null, "", `#/studio/${book.id}`);
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    }
  }, [key]);
  const create = () => go("/create/ai");
  const run = async (request: StoryRequestV2) => {
    setGenerating(true);
    go("/generating");
    const result = await generate(request);
    if (!result) return;
    setGenerating(false);
    if ("error" in result) go("/generation-error");
    else {
      const book = bookFromStory(result.story, request.display_name);
      setTransient(book);
      go(`/read/${book.id}`);
    }
  };
  const lookup = (id: string): Book | null => {
    if (transient?.id === id) return transient;
    const saved = books.find((book) => book.id === id);
    if (saved) return saved;
    for (const template of catalog)
      for (const language of ["en", "he"] as const)
        if (id === `sample-${template.id}-${language}`)
          return sampleBook(template, language);
    return null;
  };
  const template =
    "id" in route ? catalog.find((book) => book.id === route.id) : undefined;
  const editorBook =
    route.page === "editor"
      ? working.id === route.id
        ? working
        : books.find((book) => book.id === route.id && book.method === "MANUAL")
      : undefined;
  const page = (() => {
    switch (route.page) {
      case "home":
        return <Home locale={locale} p={p} />;
      case "discover":
        return <Discover key={key} locale={locale} p={p} />;
      case "product":
        return template ? (
          <Product
            key={template.id}
            template={template}
            locale={locale}
            p={p}
          />
        ) : (
          <Info page="not-found" p={p} />
        );
      case "personalize":
        return template ? (
          <Personalize
            key={template.id}
            template={template}
            locale={locale}
            p={p}
            onSave={(book) => {
              save(book);
              setTransient(book);
              go(`/read/${book.id}`);
            }}
          />
        ) : (
          <Info page="not-found" p={p} />
        );
      case "create":
        return (
          <StoryForm
            draft={draft}
            onChange={setDraft}
            onSubmit={run}
            copy={c}
            locale={locale}
          />
        );
      case "library":
        return (
          <Library
            books={books}
            locale={locale}
            p={p}
            onRemove={(id) => {
              remove(id);
              if (transient?.id === id) setTransient(null);
            }}
          />
        );
      case "editor":
        return editorBook ? (
          <Studio
            key={editorBook.id}
            book={editorBook}
            p={p}
            locale={locale}
            onChange={setWorking}
            onSave={(book, final) => {
              save(book);
              setWorking(book);
              if (final) {
                setTransient(book);
                go(`/read/${book.id}`);
              }
            }}
            onPreview={(book) => {
              setWorking(book);
              setTransient(book);
              go(`/read/${book.id}`);
            }}
          />
        ) : (
          <Info page="not-found" p={p} />
        );
      case "reader": {
        const book = lookup(route.id);
        return (
          <StoryReader
            book={book}
            copy={c}
            p={p}
            onCreate={create}
            saved={!!book && books.some((item) => item.id === book.id)}
            onSave={book ? () => save(book) : undefined}
          />
        );
      }
      case "loading":
        return generating ? (
          <main className="state-screen container" aria-busy="true">
            <div className="loading-book" aria-hidden="true">
              <span>✦</span>
              <span>✧</span>
            </div>
            <div role="status">
              <p className="eyebrow">{p.ai}</p>
              <h1>{p.loadingTitle}</h1>
              <p>{p.loadingText}</p>
              <ul className="loading-ingredients">
                <li>
                  {p.loading1}: <bdi>{draft.name}</bdi>
                </li>
                <li>
                  {p.loading2}: <bdi>{draft.theme}</bdi>
                </li>
                <li>
                  {p.loading3}: {draft.pages}
                </li>
              </ul>
              <p className="hint">{p.loadingNote}</p>
              <p className="demo-notice">{p.demo}</p>
            </div>
            <button
              className="button secondary"
              onClick={() => {
                cancel();
                setGenerating(false);
                create();
              }}
            >
              {c.cancel}
            </button>
          </main>
        ) : (
          <Info page="not-found" p={p} />
        );
      case "error":
        return (
          <main className="state-screen container">
            <span className="state-symbol" aria-hidden="true">
              ☁
            </span>
            <div role="alert">
              <h1>{c.errorTitle}</h1>
              <p>{c.errorText}</p>
            </div>
            <button className="button primary" onClick={create}>
              {c.edit}
            </button>
          </main>
        );
      default:
        return <Info page={route.page} p={p} />;
    }
  })();
  return (
    <>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          content.current?.focus();
        }}
      >
        {locale === "he" ? "דילוג לתוכן" : "Skip to content"}
      </a>
      <div className="announcement-bar">
        <span>✧ {p.announcement}</span>
        <span className="announcement-demo">{p.demo}</span>
      </div>
      <header className="site-header container">
        <a className="brand" title={c.home} href="#/">
          <span className="brand-icon" aria-hidden="true">
            ✦
          </span>
          <span>
            story<strong>forge</strong>
            <small>{c.tagline}</small>
          </span>
        </a>
        <nav
          className="desktop-nav"
          aria-label={locale === "he" ? "ניווט ראשי" : "Main navigation"}
        >
          <a
            href="#/books"
            aria-current={route.page === "discover" ? "page" : undefined}
          >
            {p.discover}
          </a>
          <a
            href="#/my-books"
            aria-current={route.page === "library" ? "page" : undefined}
          >
            {p.library}
          </a>
          <a href="#/about">{p.about}</a>
        </nav>
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
          <a className="button primary header-cta" href="#/create/ai">
            {p.ai} ✧
          </a>
          <button
            className="menu-toggle icon-button"
            ref={menuButton}
            aria-label={menuOpen ? p.close : p.menu}
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? "×" : "☰"}
          </button>
        </div>
      </header>
      {menuOpen && (
        <nav
          id="mobile-navigation"
          className="mobile-nav"
          aria-label={p.menu}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setMenuOpen(false);
              menuButton.current?.focus();
            }
          }}
        >
          {[
            [p.discover, "/books"],
            [p.ai, "/create/ai"],
            [p.manual, "/studio/new"],
            [p.library, "/my-books"],
            [p.about, "/about"],
            [p.help, "/help"],
          ].map(([label, path]) => (
            <a key={path} href={`#${path}`} onClick={() => setMenuOpen(false)}>
              {label} ↗
            </a>
          ))}
        </nav>
      )}
      <div
        id="main-content"
        ref={content}
        tabIndex={-1}
        className="main-content"
      >
        {page}
      </div>
      <footer className="site-footer">
        <div className="container footer-grid">
          <div>
            <a className="brand footer-brand" href="#/">
              story<strong>forge</strong>
              <span aria-hidden="true">✦</span>
            </a>
            <p>{p.footerLine}</p>
            <p className="hint">{p.footerNote}</p>
          </div>
          <div>
            <h2>{p.footerExplore}</h2>
            <a href="#/books">{p.discover}</a>
            <a href="#/create/ai">{p.ai}</a>
            <a href="#/studio/new">{p.manual}</a>
            <a href="#/my-books">{p.library}</a>
          </div>
          <div>
            <h2>{p.footerKnow}</h2>
            <a href="#/about">{p.about}</a>
            <a href="#/help">{p.help}</a>
            <a href="#/privacy">{p.privacy}</a>
            <details className="demo-controls">
              <summary>{c.demoControls}</summary>
              <a href="#/generation-error">{c.demoError}</a>
              <a href="#/read/missing">{c.demoEmpty}</a>
            </details>
          </div>
        </div>
        <div className="container footer-bottom">
          <span>© 2026 StoryForge · {p.demoCollection}</span>
          <span>{p.demo}</span>
        </div>
      </footer>
    </>
  );
}
