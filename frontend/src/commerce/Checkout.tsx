import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { Language } from "../api/contracts";
import { experience, money } from "../i18n/experience";
import { newId } from "../domain/book";
import {
  checkoutErrors,
  createPaymentSimulation,
  emptyDetails,
  quote,
  unitPrice,
} from "./model";
import type {
  CartLine,
  CheckoutDetails,
  Delivery,
  DemoOrder,
  PaymentSimulation,
} from "./model";
const simulator = createPaymentSimulation();
export function Checkout({
  lines,
  locale,
  onComplete,
  payment = simulator,
}: {
  lines: CartLine[];
  locale: Language;
  onComplete: (order: DemoOrder) => void;
  payment?: PaymentSimulation;
}) {
  const e = experience[locale];
  const [step, setStep] = useState(0),
    [details, setDetails] = useState(emptyDetails),
    [errors, setErrors] = useState<ReturnType<typeof checkoutErrors>>({}),
    [delivery, setDelivery] = useState<Delivery>("standard"),
    [promo, setPromo] = useState(""),
    [applied, setApplied] = useState(""),
    [promoError, setPromoError] = useState(false),
    [pending, setPending] = useState(false),
    [failed, setFailed] = useState(false),
    [decline, setDecline] = useState(false);
  const physical = lines.some((line) => line.format !== "digital"),
    totals = quote(lines, applied, delivery),
    controller = useRef<AbortController | null>(null),
    intent = useRef(newId()),
    form = useRef<HTMLFormElement>(null),
    heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => heading.current?.focus(), [step]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const found = checkoutErrors(details, step, physical);
    setErrors(found);
    if (Object.keys(found).length) {
      requestAnimationFrame(() =>
        form.current
          ?.querySelector<HTMLElement>("[aria-invalid=true]")
          ?.focus(),
      );
      return;
    }
    if (step < 3) {
      setStep(step + 1);
      return;
    }
    if (controller.current) return;
    const active = new AbortController();
    controller.current = active;
    setPending(true);
    setFailed(false);
    try {
      const result = await payment.run(
        { intentId: intent.current, quote: totals, decline },
        active.signal,
      );
      if (!active.signal.aborted)
        onComplete({
          id: result.receiptId,
          createdAt: new Date().toISOString(),
          status: "simulated",
          lines: structuredClone(lines),
          quote: totals,
        });
    } catch {
      if (!active.signal.aborted) setFailed(true);
    } finally {
      if (!active.signal.aborted) setPending(false);
      controller.current = null;
    }
  };
  const field = (key: keyof CheckoutDetails, required = true) => (
    <div className="field" key={key}>
      <label htmlFor={`checkout-${key}`}>{e[key]}</label>
      <input
        id={`checkout-${key}`}
        type={key === "email" ? "email" : "text"}
        value={details[key]}
        maxLength={key === "email" ? 254 : 120}
        autoComplete="off"
        required={required}
        dir="auto"
        aria-invalid={!!errors[key]}
        aria-describedby={errors[key] ? `checkout-${key}-error` : undefined}
        onChange={(event) => {
          setDetails({ ...details, [key]: event.target.value });
          setErrors({});
        }}
      />
      {errors[key] && (
        <p className="field-error" id={`checkout-${key}-error`}>
          {e[errors[key]!]}
        </p>
      )}
    </div>
  );
  if (!lines.length)
    return (
      <main className="state-screen container">
        <h1>{e.bagEmpty}</h1>
        <a href="#/books" className="button primary">
          {e.keepShopping}
        </a>
      </main>
    );
  return (
    <main className="container commerce-page">
      <p className="eyebrow">{e.demoCommerce}</p>
      <h1>{e.checkoutTitle}</h1>
      <p className="demo-notice">
        {e.paymentNote} {e.demoDetails}
      </p>
      <div className="commerce-grid">
        <form ref={form} onSubmit={submit} noValidate>
          <ol className="checkout-steps">
            {[e.contact, e.address, e.delivery, e.payment].map((label, i) => (
              <li key={label} aria-current={step === i ? "step" : undefined}>
                <span>{i + 1}</span>
                {label}
              </li>
            ))}
          </ol>
          <h2 ref={heading} tabIndex={-1}>
            {[e.contact, e.address, e.delivery, e.payment][step]}
          </h2>
          {Object.keys(errors).length > 0 && (
            <p className="error-banner" role="alert">
              {e.checkoutError}
            </p>
          )}
          {step === 0 && (
            <>
              <div className="two-columns">
                {field("firstName")}
                {field("lastName")}
              </div>
              {field("email")}
              <p className="hint">{e.accountNote}</p>
            </>
          )}
          {step === 1 &&
            (physical ? (
              <>
                {field("street")}
                {field("apartment", false)}
                <div className="two-columns">
                  {field("city")}
                  {field("postcode")}
                </div>
                <div className="field">
                  <label htmlFor="checkout-country">{e.country}</label>
                  <select
                    id="checkout-country"
                    value={details.country}
                    onChange={(event) =>
                      setDetails({
                        ...details,
                        country: event.target
                          .value as CheckoutDetails["country"],
                      })
                    }
                  >
                    {[
                      ["IL", e.israel],
                      ["US", e.usa],
                      ["GB", e.uk],
                    ].map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            ) : (
              <p className="demo-notice">
                {e.digital} · {e.savedInTab}
              </p>
            ))}
          {step === 2 && (
            <fieldset>
              <legend>{e.delivery}</legend>
              {(["standard", "express"] as const).map((value) => (
                <label className="delivery-option" key={value}>
                  <input
                    type="radio"
                    name="delivery"
                    checked={delivery === value}
                    onChange={() => setDelivery(value)}
                  />
                  <span>
                    {value === "standard"
                      ? e.standardDelivery
                      : e.expressDelivery}
                  </span>
                  <bdi>
                    {money(
                      physical ? (value === "standard" ? 500 : 1200) : 0,
                      locale,
                    )}
                  </bdi>
                </label>
              ))}
              <p className="hint">{e.deliveryNote}</p>
            </fieldset>
          )}
          {step === 3 && (
            <section className="payment-simulation">
              <span aria-hidden="true">◇</span>
              <h3>{e.mockPayment}</h3>
              <p>{e.paymentNote}</p>
              <p className="demo-notice">{e.confirmationNote}</p>
              <label className="check-label">
                <input
                  type="checkbox"
                  checked={decline}
                  onChange={(event) => setDecline(event.target.checked)}
                  disabled={pending}
                />
                {e.simulateFailure}
              </label>
              {failed && (
                <p className="error-banner" role="alert">
                  {e.paymentFailure}
                </p>
              )}
            </section>
          )}
          <div className="checkout-actions">
            {step > 0 && (
              <button
                type="button"
                className="button secondary"
                disabled={pending}
                onClick={() => setStep(step - 1)}
              >
                {e.back}
              </button>
            )}
            <button type="submit" className="button primary" disabled={pending}>
              {pending ? e.processing : step === 3 ? e.simulate : e.next}
            </button>
          </div>
        </form>
        <aside className="order-summary">
          <h2>{e.review}</h2>
          {lines.map((line) => (
            <div className="summary-line" key={line.id}>
              <div>
                <strong dir="auto">{line.book.title}</strong>
                <span>
                  {e[line.format]} × {line.quantity}
                </span>
              </div>
              <bdi>{money(unitPrice(line.format) * line.quantity, locale)}</bdi>
            </div>
          ))}
          <div className="promo-box">
            <label htmlFor="promo-code">{e.promo}</label>
            <div>
              <input
                id="promo-code"
                value={promo}
                maxLength={30}
                onChange={(event) => setPromo(event.target.value)}
                disabled={pending}
              />
              <button
                type="button"
                className="button secondary"
                disabled={pending}
                onClick={() => {
                  try {
                    quote(lines, promo, delivery);
                    setApplied(promo);
                    setPromoError(false);
                  } catch {
                    setPromoError(true);
                  }
                }}
              >
                {e.apply}
              </button>
            </div>
            <p className={promoError ? "field-error" : "hint"} role="status">
              {promoError
                ? e.promoInvalid
                : applied
                  ? e.promoApplied
                  : e.promoHint}
            </p>
          </div>
          <dl className="quote-totals">
            {[
              [e.subtotal, totals.subtotalCents],
              [e.discount, -totals.discountCents],
              [e.shipping, totals.shippingCents],
              [e.total, totals.totalCents],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>
                  <bdi>{money(Number(value), locale)}</bdi>
                </dd>
              </div>
            ))}
          </dl>
          <p className="hint">{e.demoPrices}</p>
        </aside>
      </div>
    </main>
  );
}
