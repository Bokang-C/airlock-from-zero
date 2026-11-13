# 3-minute demo storyboard — record only what actually works

**0:00–0:15 — Hook.** “A webpage can look completely normal to you and still contain instructions for your AI assistant. Airlock shows you the difference.” On screen: innocent rendered page.

**0:15–0:40 — Threat.** In X-Ray, select Opacity 0. Show human screenshot vs extracted hidden red instruction. Mention CSS hiding and JavaScript-inserted text; don't claim all hiding methods are covered.

**0:40–1:10 — Core technical solution.** Show `BLOCK` verdict, reason and segment provenance. Show the inspectable `visibility.js` and backend response in `/docs`: browser DOM, CSS, simple heuristics, allow/sanitize/block.

**1:10–1:55 — Agent Lab.** With your own API key on the server, run the *same* scenario with firewall OFF and then ON. Show actual tool-call trace, fake email outbox, and action gate. If baseline refuses an attack, explain that result honestly and use alternative scenarios; do not script a false hijack.

**1:55–2:20 — False positives.** Show security blog as allow + review flag. Show harmless hidden newsletter as sanitize. Explain that humans can discuss threats without instructing the agent.

**2:20–2:40 — Integration.** Show public URL, API snippet, tests, measured runtime, and any real benchmark rates (if collected).

**2:40–2:58 — Sign-off.** “Most firewalls ask if text sounds suspicious. We also ask if anyone could see it. Airlock carries that answer into what an agent is allowed to do.” Mention limitation: visible attacks still need more sophisticated review, and sensitive tool actions require independent authorization.
