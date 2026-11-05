import { useEffect, useState } from "react";
import type { StoryV2 } from "../api/contracts";
import type { Copy } from "../i18n/locales";
export function StoryReader({
  story,
  copy: c,
  onCreate,
}: {
  story: StoryV2 | null;
  copy: Copy;
  onCreate: () => void;
}) {
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [story]);
  if (!story?.pages.length)
    return (
      <main className="state-screen container">
        <div className="state-symbol" aria-hidden="true">
          ✧
        </div>
        <h1>{c.emptyTitle}</h1>
        <p>{c.emptyText}</p>
        <button className="button primary" onClick={onCreate}>
          {c.create}
        </button>
      </main>
    );
  const page = story.pages[index];
  return (
    <main className="reader container">
      <p className="eyebrow">{c.readerEyebrow}</p>
      <h1 lang={story.language} dir={story.direction}>
        {story.title}
      </h1>
      <p className="reader-note">{c.readerNote}</p>
      <article
        className="story-sheet"
        lang={story.language}
        dir={story.direction}
        aria-label={`${c.page} ${index + 1}`}
        aria-live="polite"
        aria-atomic="true"
      >
        <div className="page-ornament" aria-hidden="true">
          ✧
        </div>
        <div className="story-text" key={page.page_id}>
          {page.sentence_units.map((text, i) => (
            <p key={i}>{text}</p>
          ))}
        </div>
        <span className="printed-page" aria-hidden="true">
          {index + 1}
        </span>
      </article>
      <nav className="reader-navigation" aria-label={c.readerEyebrow}>
        <button
          className="button secondary"
          disabled={index === 0}
          onClick={() => setIndex(index - 1)}
        >
          {c.previous}
        </button>
        <span className="page-counter" role="status">
          {c.page} {index + 1} {c.of} {story.pages.length}
        </span>
        <button
          className="button secondary"
          disabled={index === story.pages.length - 1}
          onClick={() => setIndex(index + 1)}
        >
          {c.next}
        </button>
      </nav>
      <div className="reader-end">
        <button className="text-button" onClick={onCreate}>
          {c.startOver} <span aria-hidden="true">✧</span>
        </button>
      </div>
    </main>
  );
}
