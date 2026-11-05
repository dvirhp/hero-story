# Agent 2: independent frontend QA handoff

Reviewed immutable `bd40358` against earlier delivered `1647d71`, then reran against
your committed expanded revision `b09f54b`, all in QA-only exports. Your later
uncommitted session/recovery changes were not modified or tested.
No backend/provider/payment requests were made.

Fix/revalidate in this order:

1. **P1 UX-01:** mirror the Hebrew BookCover spine, binding corners/shadows and
   gradient according to **book** direction. Current spine is left despite right
   hinge. Test actual coordinates; page-spread coordinate checks already pass.
2. **P1 UX-06:** give all cover-title lines a contrast-safe background. Current
   moon cover's dark title crosses dark art at ~1.24:1; changing text from the solid
   cover color alone is insufficient. Test both languages, colors and long titles.
3. **P2 UX-02:** pass reactive UI locale to StoryReader; reading document.lang during
   render leaves new tool labels in the previous locale. Keep book direction separate.
4. **P2 UX-03:** preserve dedication literally; substitute only authored template
   text. `{{name}}`/`{{companion}}` in dedication currently change in preview/save.
5. **P2 UX-04:** keep dirty/saved revision state outside the remounting Studio.
   Preview→Continue editing currently removes the unsaved beforeunload guard.
6. **P3 UX-05:** make the selected companion's affected page inspectable in live
   preview. Only book.pages[0] is exposed, often the dedication instead.
7. **P2 UX-07:** correct the new header bag link's accessible name/visible-label
   mismatch. Axe reports `label-content-name-mismatch` in all 22 latest scans;
   the original product browser tests fail because of it. Do not disable the rule.
8. **P3 UX-08:** document what presentation means or make the offered choice affect
   its intended output. Neutral→Girl currently changes only metadata/selection;
   SVG is identical. QA prescribes no stereotyped gender rendering.

All reproduction steps/screenshots: [report](FRONTEND_UX_QA_REPORT.md).
Character, commerce, reader, localization and accessibility acceptance cases:
[matrix](FRONTEND_E2E_TEST_MATRIX.md).

Evidence: older frontend 74 unit/12 browser passes; reader revision 75 unit/14
browser passes. Latest b09f54b: 87 unit tests and build pass; upstream full browser
run 5 pass/13 fail (12 header axe failures, one transient mobile reader connection
failure; isolated reader rerun passes). Another full rerun was blocked before tests
by occupied port 5186; its owner was left untouched.

Latest independent results: `docs/qa-screenshots/frontend-ux-latest/results.json`:
17 functional passes, eight finding probes inspected/present, one axe sweep inspected,
zero harness failures or unverified probes. All 22 axe scenarios report UX-07.
Real browser simulation now covers avatar state/save, format/cart/quantity/promo,
fictional checkout/decline/retry/confirmation and Hebrew order detail. No real purchase.

Latest QA runner: `node qa/e2e/frontend-regression.mjs` against the documented QA-owned
local preview on 4197, with STORYFORGE_UX_URL set accordingly. It reports each finding
present/resolved/unverified and preserves failures rather than asserting defects must
remain. The older frontend-ux-review runner is historical characterization only.
Preserve counts/order/key/touch,
opposite UI/book languages, reduced motion, fullscreen and responsive checks.

Format/cart/checkout/confirmation and deterministic avatar now work as local demos;
account/secure anonymous session, persistent cart/books/orders and server integration
remain gaps. Keep mock/demo copy honest, and do not treat local receipt idempotency
as durable payment/order idempotency.
Provide a committed expanded revision and updated handoff for independent rerun;
real browser→API→PostgreSQL remains a separate integration phase.
