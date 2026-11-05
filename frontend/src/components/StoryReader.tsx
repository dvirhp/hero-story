import { readingDirection } from "../i18n/registry";
import { useEffect, useRef, useState } from "react";
import type { Language } from "../api/contracts";
import type { Book } from "../domain/book";
import type { Copy } from "../i18n/locales";
import type { ProductCopy } from "../i18n/product";
import { experience } from "../i18n/experience";
import { BookCover } from "./BookCover";
import { BookSpread } from "./BookSpread";
export function physicalSpread(
  index: number,
  count: number,
  wide: boolean,
): number[] {
  return index < 0
    ? []
    : wide && index > 0
      ? [index, index + 1].filter((i) => i < count)
      : [index];
}
export function StoryReader({
  book,
  copy: c,
  p,
  locale,
  onCreate,
  saved = false,
  onSave,
  onShop,
  onEdit,
}: {
  book: Book | null;
  copy: Copy;
  p: ProductCopy;
  locale: Language;
  onCreate: () => void;
  saved?: boolean;
  onSave?: () => void;
  onShop?: () => void;
  onEdit?: () => void;
}) {
  const e = experience[locale];
  const [index, setIndex] = useState(-1);
  const [wide, setWide] = useState(
    () => window.matchMedia?.("(min-width: 900px)").matches ?? false,
  );
  const [thumbs, setThumbs] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [notice, setNotice] = useState("");
  const host = useRef<HTMLElement>(null);
  const touch = useRef<{ x: number; y: number } | null>(null);
  const rtl = readingDirection(book?.language ?? "en") === "rtl";
  useEffect(() => {
    setIndex(-1);
    setThumbs(false);
  }, [book?.id]);
  useEffect(() => {
    const media = window.matchMedia?.("(min-width: 900px)");
    if (!media) return;
    const update = () => {
      setWide(media.matches);
      if (media.matches)
        setIndex((i) => (i <= 0 ? i : Math.floor((i - 1) / 2) * 2 + 1));
    };
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  const visible = book ? physicalSpread(index, book.pages.length, wide) : [];
  const last = !!book && visible.includes(book.pages.length - 1);
  const next = () =>
    setIndex((i) =>
      !book
        ? i
        : Math.min(
            book.pages.length - 1,
            i < 0 ? 0 : wide ? (i === 0 ? 1 : i + 2) : i + 1,
          ),
    );
  const previous = () =>
    setIndex((i) =>
      Math.max(-1, i === 0 ? -1 : wide ? (i <= 1 ? 0 : i - 2) : i - 1),
    );
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
      if (event.key === (rtl ? "ArrowLeft" : "ArrowRight")) {
        event.preventDefault();
        if (!last) next();
      }
      if (event.key === (rtl ? "ArrowRight" : "ArrowLeft")) {
        event.preventDefault();
        previous();
      }
    };
    window.addEventListener("keydown", keys);
    return () => window.removeEventListener("keydown", keys);
  }, [book, wide, rtl, last]);
  useEffect(() => {
    const update = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", update);
    return () => document.removeEventListener("fullscreenchange", update);
  }, []);
  const toggleFullscreen = async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else if (host.current?.requestFullscreen)
        await host.current.requestFullscreen();
      else setNotice(e.fullscreenUnavailable);
    } catch {
      setNotice(e.fullscreenUnavailable);
    }
  };
  if (!book?.pages.length)
    return (
      <main className="state-screen container">
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
  const start = index + 1,
    end = (visible.at(-1) ?? -1) + 1;
  return (
    <main
      ref={host}
      className={`reader immersive-reader container ${rtl ? "book-rtl" : "book-ltr"}`}
    >
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
        {onEdit && (
          <button className="text-button" onClick={onEdit}>
            {e.editedCopy}
          </button>
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
      <h1 lang={book.language} dir={rtl ? "rtl" : "ltr"}>
        {book.title || p.untitled}
      </h1>
      {book.dedication && (
        <p className="book-dedication" dir="auto">
          {book.dedication}
        </p>
      )}
      <div className="reader-tools">
        <button
          className="text-button"
          aria-expanded={thumbs}
          onClick={() => setThumbs(!thumbs)}
        >
          {thumbs ? e.closeThumbnails : e.thumbnails}
        </button>
        <span className="micro-label">{wide ? e.spread : e.single}</span>
        <button className="text-button" onClick={toggleFullscreen}>
          {fullscreen ? e.exitFullscreen : e.fullscreen}
        </button>
      </div>
      <div
        className={`physical-book ${index < 0 ? "is-closed" : "is-open"}`}
        dir={rtl ? "rtl" : "ltr"}
        data-book-direction={rtl ? "rtl" : "ltr"}
        onTouchStart={(event) => {
          touch.current = {
            x: event.touches[0].clientX,
            y: event.touches[0].clientY,
          };
        }}
        onTouchEnd={(event) => {
          if (!touch.current) return;
          const dx = event.changedTouches[0].clientX - touch.current.x,
            dy = event.changedTouches[0].clientY - touch.current.y;
          touch.current = null;
          if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.4) {
            if ((rtl ? dx > 0 : dx < 0) && !last) next();
            else if (rtl ? dx < 0 : dx > 0) previous();
          }
        }}
      >
        {index < 0 ? (
          <div className="cover-on-table" data-hinge={rtl ? "right" : "left"}>
            <BookCover
              title={book.title || p.untitled}
              art={book.cover}
              color={book.coverColor}
              language={book.language}
              character={book.character}
            />
            <button className="button primary" onClick={next}>
              {p.openBook}
              <span aria-hidden="true">{rtl ? "←" : "→"}</span>
            </button>
          </div>
        ) : (
          <article
            className="physical-spread"
            lang={book.language}
            dir={rtl ? "rtl" : "ltr"}
            aria-label={`${c.page} ${start}${end !== start ? `–${end}` : ""}`}
            aria-live="polite"
            aria-atomic="true"
            key={`${index}-${wide}`}
          >
            {wide && index === 0 && (
              <div
                className="folio-page inside-cover"
                data-physical-side={rtl ? "right" : "left"}
              >
                <span aria-hidden="true">✦</span>
                <span>{e.blankPage}</span>
              </div>
            )}
            {visible.map((pageIndex, position) => (
              <div
                className="folio-page"
                key={book.pages[pageIndex].pageId}
                data-page-number={pageIndex + 1}
                data-physical-side={
                  wide
                    ? index === 0
                      ? rtl
                        ? "left"
                        : "right"
                      : position === 0
                        ? rtl
                          ? "right"
                          : "left"
                        : rtl
                          ? "left"
                          : "right"
                    : "single"
                }
              >
                <BookSpread
                  page={book.pages[pageIndex]}
                  language={book.language}
                />
              </div>
            ))}
            {wide && index > 0 && visible.length === 1 && (
              <div className="folio-page inside-cover">
                <span>{e.end}</span>
              </div>
            )}
          </article>
        )}
      </div>
      <nav
        className="reader-navigation physical-controls"
        dir={rtl ? "rtl" : "ltr"}
        aria-label={p.readerProgress}
      >
        <button
          className="button secondary"
          disabled={index === -1}
          onClick={previous}
        >
          <span aria-hidden="true">{rtl ? "→" : "←"}</span>
          {index === 0 ? p.backCover : c.previous}
        </button>
        <span className="page-counter" role="status">
          {index === -1
            ? p.cover
            : `${c.page} ${start}${end !== start ? `–${end}` : ""} ${c.of} ${book.pages.length}`}
        </span>
        <button className="button secondary" disabled={last} onClick={next}>
          {index === -1 ? p.openBook : c.next}
          <span aria-hidden="true">{rtl ? "←" : "→"}</span>
        </button>
      </nav>
      <progress
        className="reading-progress"
        value={end}
        max={book.pages.length}
        aria-label={p.readerProgress}
      />
      <p className="hint">{e.readerHint}</p>
      {notice && <p role="status">{notice}</p>}
      {thumbs && (
        <div className="reader-thumbnails" dir={rtl ? "rtl" : "ltr"}>
          <button onClick={() => setIndex(-1)} aria-pressed={index === -1}>
            {p.cover}
          </button>
          {book.pages.map((page, i) => (
            <button
              key={page.pageId}
              aria-pressed={visible.includes(i)}
              onClick={() =>
                setIndex(wide && i > 0 ? Math.floor((i - 1) / 2) * 2 + 1 : i)
              }
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
      {onShop && (
        <div className="reader-purchase">
          <p>{e.reviewBook}</p>
          <button className="button primary" onClick={onShop}>
            {e.configure}
            <span aria-hidden="true">→</span>
          </button>
          <span className="hint">{e.formatNote}</span>
        </div>
      )}
      <div className="reader-end">
        <button className="text-button" onClick={onCreate}>
          {c.startOver}
        </button>
      </div>
    </main>
  );
}
