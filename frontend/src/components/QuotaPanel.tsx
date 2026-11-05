import type { DailyUsage } from "../api/productPorts";
import type { Language } from "../api/contracts";
import { experience } from "../i18n/experience";
/** No invented remaining balance: only a future server response may provide it. */
export function QuotaPanel({
  locale,
  usage,
}: {
  locale: Language;
  usage?: DailyUsage;
}) {
  const e = experience[locale];
  return (
    <details className="quota-panel">
      <summary>{e.quotaTitle}</summary>
      <p>{e.quotaNote}</p>
      {usage ? (
        <dl>
          <dt>{e.stories}</dt>
          <dd>
            {usage.capabilities.story_generation.remaining} /{" "}
            {usage.capabilities.story_generation.limit}
          </dd>
          <dt>{e.images}</dt>
          <dd>
            {usage.capabilities.image_generation.remaining} /{" "}
            {usage.capabilities.image_generation.limit}
          </dd>
        </dl>
      ) : (
        <p className="hint">{e.quotaUnavailable}</p>
      )}
    </details>
  );
}
