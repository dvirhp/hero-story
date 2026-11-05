import type { Book } from "../domain/book";
import { canFinalize, newId } from "../domain/book";
export type Format = "softcover" | "hardcover" | "digital";
export type Delivery = "standard" | "express";
export interface Offer {
  id: string;
  currency: "USD";
  demo: true;
  formats: { id: Format; unitCents: number }[];
  maxQuantity: number;
}
/** Explicit sample policy, not backend prices, inventory or product availability. */
export const demoOffer: Offer = {
  id: "demo-keepsake-v1",
  currency: "USD",
  demo: true,
  formats: [
    { id: "softcover", unitCents: 2900 },
    { id: "hardcover", unitCents: 3900 },
    { id: "digital", unitCents: 900 },
  ],
  maxQuantity: 10,
};
export interface CartLine {
  id: string;
  configuration: string;
  book: Book;
  format: Format;
  quantity: number;
  offerId: string;
}
export interface Quote {
  currency: "USD";
  demo: true;
  subtotalCents: number;
  discountCents: number;
  shippingCents: number;
  totalCents: number;
  promo: string | null;
  delivery: Delivery;
  taxCalculated: false;
}
export interface DemoOrder {
  id: string;
  createdAt: string;
  status: "simulated";
  lines: CartLine[];
  quote: Quote;
}
export interface CommerceState {
  lines: CartLine[];
  orders: DemoOrder[];
}
export function eligible(book: Book) {
  return book.status === "ready" && canFinalize(book);
}
function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, value]) => [key, stable(value)]),
    );
  return value;
}
export function configurationKey(book: Book, format: Format): string {
  return JSON.stringify(
    stable({
      method: book.method,
      title: book.title,
      language: book.language,
      childName: book.childName,
      character: book.character,
      cover: book.cover,
      coverColor: book.coverColor,
      dedication: book.dedication,
      template: book.template,
      pages: book.pages.map(({ pageId: _id, pageNumber, ...content }) => ({
        pageNumber,
        ...content,
      })),
      format,
    }),
  );
}
export function addLine(
  lines: CartLine[],
  book: Book,
  format: Format,
  quantity: number,
): CartLine[] {
  if (
    !eligible(book) ||
    !demoOffer.formats.some((item) => item.id === format) ||
    !Number.isInteger(quantity) ||
    quantity < 1 ||
    quantity > demoOffer.maxQuantity
  )
    throw new Error("INVALID_CONFIGURATION");
  const configuration = configurationKey(book, format),
    existing = lines.find((line) => line.configuration === configuration);
  if (existing && existing.quantity + quantity > demoOffer.maxQuantity)
    throw new Error("INVALID_QUANTITY");
  return existing
    ? lines.map((line) =>
        line.id === existing.id
          ? { ...line, quantity: line.quantity + quantity }
          : line,
      )
    : [
        ...lines,
        {
          id: newId(),
          configuration,
          book: structuredClone(book),
          format,
          quantity,
          offerId: demoOffer.id,
        },
      ];
}
export function unitPrice(format: Format) {
  const offer = demoOffer.formats.find((item) => item.id === format);
  if (!offer) throw new Error("INVALID_FORMAT");
  return offer.unitCents;
}
export function quote(
  lines: CartLine[],
  promo = "",
  delivery: Delivery = "standard",
): Quote {
  if (
    lines.some(
      (line) =>
        line.offerId !== demoOffer.id ||
        !Number.isInteger(line.quantity) ||
        line.quantity < 1 ||
        line.quantity > 10,
    )
  )
    throw new Error("INVALID_CART");
  const subtotalCents = lines.reduce(
      (sum, line) => sum + unitPrice(line.format) * line.quantity,
      0,
    ),
    code = promo.trim().toUpperCase();
  if (code && code !== "STORY10") throw new Error("INVALID_PROMO");
  const discountCents = code ? Math.round(subtotalCents / 10) : 0,
    shippingCents =
      lines.length && lines.some((line) => line.format !== "digital")
        ? delivery === "express"
          ? 1200
          : 500
        : 0;
  return {
    currency: "USD",
    demo: true,
    subtotalCents,
    discountCents,
    shippingCents,
    totalCents: subtotalCents - discountCents + shippingCents,
    promo: code || null,
    delivery,
    taxCalculated: false,
  };
}
export interface CheckoutDetails {
  firstName: string;
  lastName: string;
  email: string;
  street: string;
  apartment: string;
  city: string;
  postcode: string;
  country: "IL" | "US" | "GB";
}
export const emptyDetails: CheckoutDetails = {
  firstName: "",
  lastName: "",
  email: "",
  street: "",
  apartment: "",
  city: "",
  postcode: "",
  country: "IL",
};
export function checkoutErrors(
  details: CheckoutDetails,
  step: number,
  physical: boolean,
) {
  const errors: Partial<
    Record<keyof CheckoutDetails, "required" | "emailError">
  > = {};
  const fields: (keyof CheckoutDetails)[] =
    step === 0
      ? ["firstName", "lastName", "email"]
      : step === 1 && physical
        ? ["street", "city", "postcode", "country"]
        : [];
  for (const field of fields)
    if (
      !details[field].trim() ||
      details[field].length > (field === "email" ? 254 : 120)
    )
      errors[field] = "required";
  if (step === 0 && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(details.email))
    errors.email = "emailError";
  if (step === 1 && !["IL", "US", "GB"].includes(details.country))
    errors.country = "required";
  return errors;
}
export interface PaymentSimulation {
  run(
    input: { intentId: string; quote: Quote; decline: boolean },
    signal: AbortSignal,
  ): Promise<{ status: "simulated"; receiptId: string }>;
}
export function createPaymentSimulation(delay = 500): PaymentSimulation {
  const receipts = new Map<string, string>();
  return {
    run(input, signal) {
      return new Promise((resolve, reject) => {
        if (signal.aborted) {
          reject(new DOMException("Aborted", "AbortError"));
          return;
        }
        const abort = () => {
          clearTimeout(timer);
          reject(new DOMException("Aborted", "AbortError"));
        };
        const timer = setTimeout(() => {
          signal.removeEventListener("abort", abort);
          if (input.decline) {
            reject(new Error("DEMO_DECLINED"));
            return;
          }
          const receiptId = receipts.get(input.intentId) || newId();
          receipts.set(input.intentId, receiptId);
          resolve({ status: "simulated", receiptId });
        }, delay);
        signal.addEventListener("abort", abort, { once: true });
      });
    },
  };
}
