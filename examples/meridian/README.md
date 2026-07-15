# Example fixture: Meridian Trucks

**Everything in this directory is synthetic.** The brands (Meridian Trucks,
Northstar Motors, Copperline Auto, Vantage Trucks), products, prices, and all
buyer-behavior figures are fictional, constructed to exercise every branch of
the reasoning method:

- **Meridian** - the subject brand: commodity-heavy catalog, thin exterior
  personalization, one rebranded performance SKU priced at near-parity with
  better competitor products, no packs, no curation.
- **Northstar Motors** - the behavior-shifting benchmark: personalization-heavy
  purchase mix, named packs sold in the configurator, bespoke program.
- **Copperline Auto** - the presence ≠ behavior case: a performance sub-brand
  occupying 25% of its catalog while performance is only 7% of its buyers'
  purchases.
- **Vantage Trucks** - a fellow laggard, showing the pattern isn't universal
  excuse-making material.

The brand catalog also carries three deliberately unmappable SKUs (Comfort /
Convenience / Safety categories) to exercise the model-resolution path, and
the comparable-price matcher will surface two false pairs (cargo divider vs
cargo net; bed tent vs rooftop tent) that the model is expected to reject.

## Run it

```bash
# full-diagnostic mode (buyer_behavior.yaml present)
python3 -m whitespace analyze examples/meridian

# public-data mode
mv examples/meridian/buyer_behavior.yaml /tmp/ && python3 -m whitespace analyze examples/meridian
```

Then either invoke the `/whitespace examples/meridian` skill in Claude Code,
or run `python3 -m whitespace prompt examples/meridian` and paste
`out/prompt.md` into the subscription model.

`sample-report.md` is the deliverable this fixture produces when the full
workflow runs - kept in the repo as the reference for what output quality
should look like.
