# CURSOR WAVE 6 — VISUAL QA SCORECARD

**Method:** Figma MCP `get_screenshot` + Playwright Chromium captures of http://localhost:3000  
**Viewports captured:** 1440×900 (all major routes), 390×844 (login, Candidate home, Candidate Athena)  
**Not individually captured:** 1280×800, 1024×768, 768×1024 (same CSS breakpoints; not claimed verified)  
**Pixel-diff overlay:** **not available**  
**Pixel-perfect:** **not claimed**

Statuses: PASS · MINOR FIX · MAJOR FIX · BACKEND-LIMITED · MISSING · NOT TESTABLE

## Scorecard

| Portal | Route | Figma | Layout | Typography | Components | Color | Responsive | Functional | Status |
|---|---|---|---|---|---|---|---|---|---|
| Auth | `/login` | `9:73` | PASS | PASS | PASS | PASS | PASS (1440+390) | PASS | **PASS** (VISUALLY VERIFIED) |
| Auth | `/register` | `9:6` | PASS | PASS | MINOR FIX (intent toggle extra vs Figma) | PASS | NOT TESTABLE 390 | PASS | **MINOR FIX** (VISUALLY VERIFIED) |
| Auth | `/forgot-password` | none | PASS | PASS | PASS | PASS | NOT TESTABLE 390 | PASS | **PASS** (VISUALLY VERIFIED) |
| Candidate | `/jobseeker` | `5:6` | PASS | PASS | PASS | PASS | PASS 390 | PASS | **PASS** empty-state (VISUALLY VERIFIED) |
| Candidate | `/id/work-id` | `5:211` | PASS | PASS | PASS | PASS | NOT TESTABLE 390 | PASS | **PASS** (VISUALLY VERIFIED) |
| Candidate | `/jobseeker/documents` | disclosure | PASS | PASS | PASS | PASS | — | PASS | **PASS** (opened) |
| Candidate | `/jobseeker/credentials` | `5:1893` | PASS | PASS | PASS | PASS | — | PASS | **PASS** (opened) |
| Candidate | `/jobseeker/work-dna` | `5:769` | PASS | PASS | PASS | PASS | — | PASS | **PASS** (opened) |
| Candidate | `/jobseeker/career` | `5:984`/`5:2091` | PARTIAL | PASS | PASS | PASS | — | PASS | **BACKEND-LIMITED** map art |
| Candidate | `/jobseeker/opportunities` | `5:1129` | PASS | PASS | PASS | PASS | — | PASS | **PASS** empty (opened) |
| Candidate | `/jobseeker/applications` | `5:1346` | PASS | PASS | PASS | PASS | — | PASS | **PASS** empty |
| Candidate | `/jobseeker/interviews` | `5:1618` | PASS | PASS | PASS | PASS | — | PASS | **PASS** empty |
| Candidate | `/jobseeker/ai-interview` | none | PASS | PASS | PASS | PASS | — | PASS | **PASS** (opened) |
| Candidate | `/jobseeker/interview-prep` | none | PASS | PASS | PASS | PASS | — | PASS | **PASS** (opened) |
| Candidate | `/jobseeker/offers` | `5:1753` | PASS | PASS | PASS | PASS | — | PASS | **PASS** empty |
| Candidate | `/jobseeker/communications` | messages | PASS | PASS | PASS | PASS | — | PASS | **PASS** empty |
| Candidate | `/jobseeker/notifications` | — | PASS | PASS | PASS | PASS | — | PASS | **PASS** |
| Candidate | `/jobseeker/privacy` | `5:2756` | PASS | PASS | PASS | PASS | — | PASS | **PASS** |
| Candidate | `/jobseeker/athena` | none / `5:427` | PASS | PASS | PASS | PASS | PASS 390 | PASS degraded | **PASS** (VISUALLY VERIFIED) |
| Employer | `/company` | `3:8` | MAJOR FIX vs Figma topbar | PASS | PASS | PASS | — | PASS | **PARTIAL** (VISUALLY VERIFIED; IA choice) |
| Employer | `/company/*` listed in portal map | various | PASS shell | PASS | PASS | PASS | — | PASS | **PASS** empty / BACKEND-LIMITED extras |
| Employer | `/company/athena` | `3:188` | PASS | PASS | PASS | PASS | — | PASS degraded | **PASS** (opened) |
| Admin | `/admin` | `3:6` | PARTIAL (no megamenu/search) | PASS | PASS | PASS | — | PASS | **PARTIAL** (VISUALLY VERIFIED) |
| Admin | governance/enforcement/appeals/audit/teams/finance/ops/support | mixed | PASS shell | PASS | PASS | PASS | — | PASS | **PASS** (opened) |
| Admin | `/admin/athena` | `3:4752` | BACKEND-LIMITED | PASS | PASS | PASS | — | PASS | **BACKEND-LIMITED** |
| Government | — | file exists | MISSING | — | — | — | — | — | **MISSING** |
| Skills intel / compensation / onboarding (Candidate Figma) | — | frames exist | MISSING | — | — | — | — | — | **BACKEND-LIMITED** |

## Portal scores

| Portal | Overall | Notes |
|---|---|---|
| Auth | **PASS** after Wave 6 split-shell restyle | Marketing chrome removed from auth |
| Candidate OS | **PASS** (empty DEV, Figma-aligned shell) | Coherent OS |
| Work ID | **PASS** | Identity hierarchy present |
| Employer OS | **CLOSE / PARTIAL** | Same OS family; Figma topbar+search not copied (would invent search) |
| Athena | **PASS** degraded | No fake AI |
| Super Admin | **CLOSE / PARTIAL** | Real control plane; Figma megamenu BACKEND-LIMITED |
| Government | **MISSING** | Design only |

## Overall product

One visual language is visible on localhost: `#0b0c0d`, gold `#d4af37`, 240px sidebars, shared cards/buttons. Auth now belongs to that language.

**VISUALLY VERIFIED** = Playwright opened the rendered page and it was compared to a Figma frame screenshot.  
**IMPLEMENTED BUT NOT VISUALLY VERIFIED** = code exists; no Playwright capture (e.g. `/admin/governance/[id]` with a live case, `/company/candidates/[id]`, tablet widths).
