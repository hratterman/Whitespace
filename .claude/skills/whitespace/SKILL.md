---
name: whitespace
description: Run the category whitespace analysis end-to-end on a data directory and write the strategic report. Use when the user asks for a whitespace/assortment/merchandising analysis of a brand, or invokes /whitespace <data-dir>.
---

# Whitespace analysis (agent orchestration mode)

You are running the full tool: deterministic compute in code, judgment by
you. The argument is the data directory (default: ask the user; `examples/meridian`
is the synthetic demo fixture).

## Steps

1. **Compute.** Run:

   ```
   python3 -m whitespace analyze <data-dir>
   ```

   Fix input-contract errors by telling the user what's malformed — do not
   silently repair their data. Note the printed unmapped SKUs and data flags.

2. **Read the method.** Read `method/REASONING.md` and `method/OUTPUT_SPEC.md`
   in full, and `<data-dir>/out/analysis.json`. The method is binding — in
   particular: diagnose problem type before size, lead with composition not
   concentration, benchmark behavior not presence, never blend mix % with
   penetration %, merchandise-first sequencing.

3. **Resolve unmapped SKUs.** For each entry in `mapping_audit.unmapped`,
   decide the bucket from the SKU name/category and record SKU → bucket +
   one-line reason. If resolutions materially shift a composition share you
   will cite, adjust the cited figures accordingly (state that you did).
   These resolutions go in the report appendix.

4. **Reason and write.** Apply the method and write the deliverable to
   `<data-dir>/out/report.md`, following `method/OUTPUT_SPEC.md` exactly.
   Invest in the writing: headline-led sections, every claim paired with
   evidence and an action, no orphan statistics.

5. **Deliver.** Send the user the report file and summarize the diagnosis and
   top recommendation in two or three sentences in chat.

## Guardrails

- Public-data mode (no `buyer_behavior.yaml`): never fabricate attach, spend,
  purchase-mix, or channel figures. Say what the behavioral layer would add
  and which sections are proxy-based.
- Carry every `data_flags` entry into the appendix.
- Do not include proprietary or licensed source figures in any version the
  user says will be shared externally — directional statements only.
