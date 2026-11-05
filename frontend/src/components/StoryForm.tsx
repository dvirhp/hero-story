import { useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import type { Language, StoryRequestV2, StoryType } from "../api/contracts";
import { prepareRequest } from "../domain/brief";
import type { BriefDraft, BriefErrors } from "../domain/brief";
import { locales, storyTypes } from "../i18n/locales";
import type { Copy } from "../i18n/locales";
import { GardenArt } from "./GardenArt";
function Field({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && (
        <p className="hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field-error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}
export function StoryForm({
  draft,
  onChange,
  onSubmit,
  copy: c,
  locale,
}: {
  draft: BriefDraft;
  onChange: (draft: BriefDraft) => void;
  onSubmit: (request: StoryRequestV2) => void;
  copy: Copy;
  locale: Language;
}) {
  const [errors, setErrors] = useState<BriefErrors>({});
  const formRef = useRef<HTMLFormElement>(null);
  const update = <K extends keyof BriefDraft>(key: K, value: BriefDraft[K]) => {
    onChange({ ...draft, [key]: value });
    setErrors({});
  };
  const error = (key: keyof BriefErrors) =>
    errors[key] ? c[errors[key]!] : undefined;
  const described = (key: keyof BriefErrors, hint = false) =>
    [hint ? `${key}-hint` : "", errors[key] ? `${key}-error` : ""]
      .filter(Boolean)
      .join(" ") || undefined;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    const result = prepareRequest(draft);
    setErrors(result.errors);
    if (result.request) onSubmit(result.request);
    else
      requestAnimationFrame(() =>
        formRef.current
          ?.querySelector<HTMLElement>('[aria-invalid="true"]')
          ?.focus(),
      );
  };
  const structured = draft.education || draft.type === "alphabet";
  return (
    <main className="form-layout container">
      <div>
        <p className="eyebrow">{c.formEyebrow}</p>
        <h1 className="form-heading">{c.formTitle}</h1>
        <p className="intro">{c.formIntro}</p>
        <form ref={formRef} onSubmit={submit} noValidate>
          {Object.keys(errors).length > 0 && (
            <p className="error-banner" role="alert">
              {c.invalid}
            </p>
          )}
          <fieldset>
            <legend>{c.childSection}</legend>
            <Field id="name" label={c.name} error={error("name")}>
              <input
                id="name"
                autoComplete="off"
                dir="auto"
                value={draft.name}
                onChange={(e) => update("name", e.target.value)}
                placeholder={c.namePlaceholder}
                required
                aria-invalid={!!errors.name}
                aria-describedby={described("name")}
              />
            </Field>
            <div className="two-columns">
              <Field
                id="age"
                label={c.age}
                hint={c.ageHelp}
                error={error("age")}
              >
                <input
                  id="age"
                  type="number"
                  min="0"
                  step="any"
                  inputMode="decimal"
                  value={draft.age}
                  onChange={(e) => update("age", e.target.value)}
                  required
                  aria-invalid={!!errors.age}
                  aria-describedby={described("age", true)}
                />
              </Field>
              <Field id="age-unit" label={c.unit}>
                <select
                  id="age-unit"
                  value={draft.ageUnit}
                  onChange={(e) =>
                    update("ageUnit", e.target.value as BriefDraft["ageUnit"])
                  }
                >
                  <option value="months">{c.months}</option>
                  <option value="years">{c.years}</option>
                </select>
              </Field>
            </div>
            <Field id="language" label={c.language} hint={c.languageHelp}>
              <select
                id="language"
                value={draft.language}
                aria-describedby="language-hint"
                onChange={(e) => update("language", e.target.value as Language)}
              >
                {Object.entries(locales).map(([code, item]) => (
                  <option key={code} value={code} lang={code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </Field>
          </fieldset>
          <fieldset>
            <legend>{c.storySection}</legend>
            <Field id="theme" label={c.theme} error={error("theme")}>
              <input
                id="theme"
                dir="auto"
                value={draft.theme}
                placeholder={c.themePlaceholder}
                onChange={(e) => update("theme", e.target.value)}
                required
                aria-invalid={!!errors.theme}
                aria-describedby={described("theme")}
              />
            </Field>
            <Field
              id="guidance"
              label={`${c.guidance} (${c.optional})`}
              error={error("guidance")}
            >
              <textarea
                id="guidance"
                rows={3}
                dir="auto"
                value={draft.guidance}
                placeholder={c.guidancePlaceholder}
                onChange={(e) => update("guidance", e.target.value)}
                aria-invalid={!!errors.guidance}
                aria-describedby={described("guidance")}
              />
            </Field>
            <Field id="story-type" label={c.type}>
              <select
                id="story-type"
                value={draft.type}
                onChange={(e) => update("type", e.target.value as StoryType)}
              >
                {Object.entries(storyTypes[locale]).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </fieldset>
          <fieldset>
            <legend>{c.bookSection}</legend>
            <Field
              id="pages"
              label={c.pages}
              hint={c.pagesHelp}
              error={error("pages")}
            >
              <input
                id="pages"
                className="page-input"
                type="number"
                min="1"
                max="32"
                step="1"
                inputMode="numeric"
                value={draft.pages}
                onChange={(e) => update("pages", e.target.value)}
                required
                aria-invalid={!!errors.pages}
                aria-describedby={described("pages", true)}
              />
            </Field>
            <Field id="density" label={c.density} hint={c.densityHelp}>
              <select
                id="density"
                value={draft.density}
                aria-describedby="density-hint"
                onChange={(e) =>
                  update("density", e.target.value as BriefDraft["density"])
                }
              >
                <option value="light">{c.light}</option>
                <option value="standard">{c.standard}</option>
              </select>
            </Field>
            <div className="education-panel">
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={structured}
                  disabled={draft.type === "alphabet"}
                  onChange={(e) => update("education", e.target.checked)}
                  aria-describedby="education-hint"
                />
                {c.education}
              </label>
              <p id="education-hint" className="hint">
                {c.educationHelp}
              </p>
              {structured && (
                <div className="target-fields">
                  {draft.type !== "alphabet" && (
                    <Field id="target-kind" label={c.targetKind}>
                      <select
                        id="target-kind"
                        value={draft.targetKind}
                        onChange={(e) =>
                          update(
                            "targetKind",
                            e.target.value as BriefDraft["targetKind"],
                          )
                        }
                      >
                        <option value="concept">{c.concept}</option>
                        <option value="letter">{c.letter}</option>
                      </select>
                    </Field>
                  )}
                  <Field
                    id="targets"
                    label={c.targets}
                    hint={c.targetsHelp}
                    error={error("targets")}
                  >
                    <textarea
                      id="targets"
                      rows={5}
                      dir="auto"
                      value={draft.targets}
                      placeholder={c.targetPlaceholder}
                      onChange={(e) => update("targets", e.target.value)}
                      aria-invalid={!!errors.targets}
                      aria-describedby={described("targets", true)}
                      required
                    />
                  </Field>
                </div>
              )}
            </div>
          </fieldset>
          <button className="button primary submit" type="submit">
            {c.generate}
            <span aria-hidden="true">✧</span>
          </button>
          <p className="privacy">{c.privacy}</p>
        </form>
      </div>
      <aside className="brief-aside">
        <p className="eyebrow">{c.summary}</p>
        <GardenArt compact />
        <h2>{draft.name ? <bdi>{draft.name}</bdi> : c.summaryText}</h2>
        <div className="summary-pills">
          <span>
            {draft.pages || "—"} {c.pages}
          </span>
          <span lang={draft.language}>{locales[draft.language].label}</span>
          <span>{storyTypes[locale][draft.type]}</span>
        </div>
        <p>{c.demoNote}</p>
      </aside>
    </main>
  );
}
