# Example fixture: Harborline Fitness (custom premise)

**Everything here is synthetic.** This is the fixture that proves the premise
system: a boutique fitness studio analyzed with a **derived premise**
(`premise.yaml`, key `studio-schedule`) - not a shipped preset - plus a fully
domain-native taxonomy with its own bucket keys.

What it demonstrates:

1. **The four canonical questions, renamed:** participation (members booking
   anything), frequency (visits/member/month), mix (booking mix by class
   type), booking capture (own app vs aggregators).
2. **Custom channel keys and labels** flowing into the deck's stacked chart
   ("Own app & front desk / Aggregator platforms / Walk-in & other").
3. **Custom bucket keys** (`strength_progression`, `mind_body`, …) - the
   taxonomy cross-check still catches typos against the buyer file.
4. The method's traps in a new world: Pulse Collective is the
   presence≠behavior case (flashiest specialty menu, basic-cardio bookings);
   the Run Club has a deliberately missing price; Open Gym Block is the
   unmapped entity for model resolution.

Run `python3 -m whitespace analyze examples/harborline`, then the skill or
paste seam as usual. `sample-report.md`, `sample-report.json`,
`sample-deck.html`, and `sample-onepager.html` are the reference deliverables.
