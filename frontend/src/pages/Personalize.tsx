import { useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Language } from "../api/contracts";
import type { Book } from "../domain/book";
import type { BookTemplate } from "../data/catalog";
import {
  personalizeTemplate,
  templateDefaults,
  templateErrors,
} from "../data/catalog";
import type { ProductCopy } from "../i18n/product";
import { locales } from "../i18n/locales";
import { BookCover } from "../components/BookCover";
import { BookSpread } from "../components/BookSpread";
export function Personalize({
  template,
  locale,
  p,
  onSave,
}: {
  template: BookTemplate;
  locale: Language;
  p: ProductCopy;
  onSave: (book: Book) => void;
}) {
  const [values, setValues] = useState(() => templateDefaults(template));
  const [language, setLanguage] = useState<Language>(locale);
  const [errors, setErrors] = useState<Record<string, "required" | "tooLong">>(
    {},
  );
  const [preview, setPreview] = useState<"cover" | "inside">("cover");
  const form = useRef<HTMLFormElement>(null);
  const book = personalizeTemplate(template, values, language, "live-preview");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const result = templateErrors(template, values);
    setErrors(result);
    if (Object.keys(result).length)
      requestAnimationFrame(() =>
        form.current
          ?.querySelector<HTMLElement>("[aria-invalid=true]")
          ?.focus(),
      );
    else onSave(personalizeTemplate(template, values, language));
  };
  return (
    <main className="container personalization-page">
      <a className="inline-link breadcrumb" href={`#/books/${template.id}`}>
        {p.back} / {template.title[locale]}
      </a>
      <div className="personalize-grid">
        <div>
          <p className="eyebrow">{p.template}</p>
          <h1>{p.personalTitle}</h1>
          <p className="intro">{p.personalIntro}</p>
          <form ref={form} onSubmit={submit} noValidate>
            {Object.keys(errors).length > 0 && (
              <p className="error-banner" role="alert">
                {p.personalError}
              </p>
            )}
            <div className="field">
              <label htmlFor="template-language">{p.language}</label>
              <select
                id="template-language"
                value={language}
                onChange={(e) => setLanguage(e.target.value as Language)}
              >
                {template.languages.map((code) => (
                  <option key={code} value={code}>
                    {locales[code].label}
                  </option>
                ))}
              </select>
            </div>
            {template.fields.map((field) => (
              <div className="field" key={field.id}>
                <label htmlFor={`personal-${field.id}`}>{p[field.label]}</label>
                {field.type === "select" ? (
                  <select
                    id={`personal-${field.id}`}
                    value={values[field.id]}
                    onChange={(e) => {
                      setValues({ ...values, [field.id]: e.target.value });
                      setErrors({});
                    }}
                    required={field.required}
                    aria-invalid={!!errors[field.id]}
                  >
                    {field.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {p[option.label]}
                      </option>
                    ))}
                  </select>
                ) : field.type === "textarea" ? (
                  <textarea
                    id={`personal-${field.id}`}
                    rows={3}
                    value={values[field.id]}
                    maxLength={field.maxLength}
                    dir="auto"
                    onChange={(e) => {
                      setValues({ ...values, [field.id]: e.target.value });
                      setErrors({});
                    }}
                    aria-invalid={!!errors[field.id]}
                    aria-describedby={
                      errors[field.id]
                        ? `personal-${field.id}-error`
                        : undefined
                    }
                  />
                ) : (
                  <input
                    id={`personal-${field.id}`}
                    value={values[field.id]}
                    dir="auto"
                    onChange={(e) => {
                      setValues({ ...values, [field.id]: e.target.value });
                      setErrors({});
                    }}
                    required={field.required}
                    aria-invalid={!!errors[field.id]}
                    aria-describedby={
                      errors[field.id]
                        ? `personal-${field.id}-error`
                        : undefined
                    }
                  />
                )}{" "}
                {errors[field.id] && (
                  <p className="field-error" id={`personal-${field.id}-error`}>
                    {p[errors[field.id]]}
                  </p>
                )}
              </div>
            ))}
            <button className="button primary submit" type="submit">
              {p.saveLibrary}
              <span aria-hidden="true">✧</span>
            </button>
            <p className="hint">{p.productNote}</p>
          </form>
        </div>
        <aside className="personal-preview">
          <div className="preview-tabs">
            <button
              aria-pressed={preview === "cover"}
              onClick={() => setPreview("cover")}
            >
              {p.cover}
            </button>
            <button
              aria-pressed={preview === "inside"}
              onClick={() => setPreview("inside")}
            >
              {p.preview}
            </button>
          </div>
          <p className="micro-label">{p.livePreview}</p>
          {preview === "cover" ? (
            <BookCover
              title={book.title}
              art={book.cover}
              color={book.coverColor}
              language={language}
            />
          ) : (
            <BookSpread page={book.pages[0]} language={language} preview />
          )}
          <p className="hint">{p.demoProduct}</p>
        </aside>
      </div>
    </main>
  );
}
