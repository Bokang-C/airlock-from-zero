# Devpost submission draft (replace placeholders with verified facts)

**Project name:** Airlock — Visibility-Aware AI Agent Firewall

**Tagline:** Other firewalls ask if a page sounds malicious. Airlock also asks if a human could see the text.

**Inspiration**
AI agents read webpage content as context, which can include instructions intentionally hidden from human users. A human may see a normal travel guide while a naive text extractor reveals invisible agent-directed commands. We wanted to make that trust boundary understandable, visual, and testable.

**What it does**
Airlock renders pasted HTML in a real Chromium browser, compares the human-visible screenshot against text extracted from the DOM, and labels text as visible, hidden or nonvisual. The backend flags suspicious instructions, returns `allow`, `sanitize`, or `block`, and provides segment-level evidence. A separate Agent Lab runs a real LLM with a fake email tool and an action gate that denies commands not authorized by the user.

**How we built it**
Python, FastAPI, Playwright/Chromium, JavaScript DOM APIs, heuristic content rules, React, Vite and TypeScript. Public URL fetching is opt-in, with restricted HTTP(S) access; browser rendering blocks external network access. Fake tool calls are never sent through real email. Tests cover CSS-hidden, JavaScript-inserted, quoted visible and benign hidden text.

**Challenges**
Determining visibility is not as simple as regex: class-based CSS, DOM mutation, geometry and contrast require rendering. Browser isolation and authorization are difficult to secure in a deployable demo. The LLM might refuse attacks by itself, which means baseline success must be measured rather than assumed.

**What we learned**
Visibility is an additional risk signal, not a proof of malicious intent. Visible malicious text remains dangerous, and an instruction detector is not a substitute for action authorization.

**What's next**
Add a model-based reviewer for visible but suspicious content, improve accessible-content preservation, conduct a genuine benchmark with real LLMs, and isolate browser workers more strongly.

**Credits and AI disclosure (REQUIRED)**
**Significant project scaffolding/code/documentation were AI-assisted** (ChatGPT, plus any Cursor-generated frontend changes). We reviewed [describe what you personally reviewed], tested [real test count and environment], and independently implemented [your actual contributions]. We used Playwright, React and other libraries. Do not claim work you did not do yourself.

**Links (fill in before submission)**
- GitHub: [public URL]
- Live demo: [verified working URL]
- Demo video: [public under-three-minute URL]
- Test results: [real output]
- Benchmark: [actual ON and OFF counts, or “not measured”]
