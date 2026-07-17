# AdSense low value content audit

Date: 2026-07-17

Target site: https://jobcan-automation.onrender.com/

## References

- Google AdSense site approval: https://support.google.com/adsense/answer/10502938?hl=ja
- Google AdSense low value content guidance: https://support.google.com/adsense/answer/10015918?hl=ja
- Search Console manual actions: https://support.google.com/webmasters/answer/9044175?hl=ja
- Google Publisher Policies: https://support.google.com/publisherpolicies/answer/11035931?hl=ja

## Conclusion

The most likely AdSense review risk was not one isolated bug. The site mixed useful tool pages, affiliate-heavy blocks, legal/contact pages, noindex pages, and mojibake text in a way that made the public output look less trustworthy and less original than the actual Jobcan/PDF functionality.

This report does not claim that the site will pass AdSense review. Google does not publish a deterministic checklist for approval. The purpose of this work is to remove clear site-quality blockers and make the review target more coherent.

Search Console manual action status and AdSense site review status must not be treated as the same thing. A clean manual-action state does not imply AdSense approval.

## Root cause candidates

| Severity | Finding | Evidence | Policy relevance | Remediation |
| --- | --- | --- | --- | --- |
| Critical | Mojibake and broken Japanese appeared in public templates and metadata sources. | `templates/landing_v2.html`, `templates/tools/index.html`, `templates/autofill_flow.html`, `templates/tools/pdf_flow.html`, `templates/includes/head_meta.html` | Broken text reduces trust, originality, and page quality signals. | Rewrote active public templates and meta partials with clean Japanese. Added preflight mojibake checks for rendered HTML. |
| Critical | AdSense script could be loaded too broadly through the shared head partial. | `templates/includes/head_meta.html`, `app.py` | Auto ads on low-value, legal, contact, noindex, or operational pages can weaken site review quality. | Added `ADSENSE_ALLOWED` gating. AdSense is limited to core indexable content pages only. |
| High | Affiliate fallback sections could appear on pages where the user intent was legal/contact/trust rather than product discovery. | `templates/includes/footer.html`, `app.py` | Heavy affiliate content on thin or trust pages can make the site look monetization-first. | Added `AFFILIATE_BLOCKED_PATHS`, disabled affiliate fallback on `/about`, `/privacy`, `/terms`, and `/contact`. |
| High | `/recommend` was an affiliate hub and was eligible for sitemap/index treatment. | `app.py`, `lib/seo.py`, `scripts/generate_sitemap_lastmod_manifest.py` | A page whose main purpose is outbound affiliate discovery is a weaker AdSense review target. | Kept `/recommend` available for users, but marked it `noindex,follow` and removed it from sitemap. |
| High | Sitemap did not clearly reflect the current AdSense review target pages. | `SIMPLIFIED_SITEMAP_URLS`, `data/sitemap_lastmod.json` | Sitemap should list canonical, indexable, useful public pages. | Sitemap now contains only `/`, `/autofill`, `/tools`, `/tools/pdf`, `/faq`, and `/about`. |
| Medium | The site lacked a dedicated trust/about page after prior simplification. | `/about` redirected to `/` | Users and reviewers need to understand ownership, scope, data handling, and non-affiliation. | Added `/about` with service scope, data handling, advertisement policy, non-affiliation note, and contact path. |
| Medium | Footer affiliate disclosures and fallback modules were not separated enough from content value. | `templates/includes/footer.html` | Disclosures are needed, but ad modules should not dominate unrelated pages. | Footer now suppresses affiliate fallback where the path is excluded, while keeping disclosure on appropriate pages. |
| Medium | Legacy unused template `templates/tools/pdf.html` still contains mojibake in source comments and old JS text. | `templates/tools/pdf.html` | It is not currently rendered by `/tools/pdf`, but it is a repo hygiene risk. | Not modified in this low-risk pass because `/tools/pdf` uses `templates/tools/pdf_flow.html`; recommend deleting or restoring this old template in a separate cleanup. |
| Low | Amazon theme data still needed clean, Japanese, purpose-based labels. | `lib/amazon_affiliate_map.py`, `lib/products_catalog.py` | Affiliate recommendations should not look like scraped product listings or ranking claims. | Rebuilt the active catalog and theme map around work/PDF/consulting categories without price, stock, ratings, or ranking claims. |
| Not an issue | Search Console manual action status differs from AdSense site approval. | Google Search Console and AdSense are separate review surfaces. | Avoids misleading remediation steps. | Treat AdSense low-value content as a site-quality review problem, not a manual action problem. |

## Pages after remediation

Indexable and sitemap-listed:

- `/`
- `/autofill`
- `/tools`
- `/tools/pdf`
- `/faq`
- `/about`

Available but not index targets:

- `/recommend`
- `/privacy`
- `/terms`
- `/contact`

Operational/non-content endpoints:

- `/robots.txt`
- `/sitemap.xml`
- `/ads.txt`
- `/healthz`
- `/readyz`
- `/ping`

## AdSense and affiliate policy split

AdSense code is allowed only on core content pages with independent value. It is blocked on `/recommend`, legal pages, contact pages, health endpoints, API endpoints, redirects, and error-like pages.

External affiliate links are intentionally concentrated on `/recommend`. Other core pages now link internally to `/recommend` instead of repeatedly rendering external affiliate modules. Legal/contact/about pages do not render affiliate fallback modules.

Amazon links continue to use `rel="nofollow sponsored noopener"` and avoid price, stock, review, star rating, and ranking claims.

## What was not changed

- No guarantee of AdSense approval was made.
- No Product Advertising API or scraping was added.
- No fake product metrics, rankings, testimonials, or usage numbers were added.
- The unused legacy `templates/tools/pdf.html` was not cleaned in this pass because it is not the active PDF route and had a pre-existing dirty status.
- No Render dashboard settings were changed from code.

## Follow-up before requesting review

1. Verify production deploy commit matches the pushed commit.
2. Confirm `/`, `/autofill`, `/tools`, `/tools/pdf`, `/faq`, and `/about` load the AdSense script only when `ADSENSE_ENABLED=true`.
3. Confirm `/recommend`, `/privacy`, `/terms`, `/contact`, error pages, health endpoints, and API endpoints do not load AdSense.
4. Confirm sitemap contains only indexable pages and excludes `/recommend`.
5. Confirm ads.txt returns exactly `google.com, pub-4232725615106709, DIRECT, f08c47fec0942fa0`.
6. Confirm rendered HTML has no mojibake.
7. Confirm no external affiliate modules appear on legal/contact/about pages.
8. Do not press "fixed" or request AdSense review until production output is verified, not just local output.
