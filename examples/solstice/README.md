# Example fixture: Solstice Espresso (second domain, public-data mode)

**Everything here is synthetic.** This is the tool's second-domain fixture -
espresso-machine accessories instead of vehicles - and it exists to prove two
things:

1. **Domain portability.** The local `taxonomy.yaml` overrides the repo-root
   automotive taxonomy: same bucket *types* (the method reasons over
   commodity vs personalization vs utility vs performance vs lifestyle),
   coffee-domain labels and keyword rules. Nothing in the code changes.
2. **Public-data mode as a real analysis.** There is deliberately no
   `buyer_behavior.yaml`: the analysis runs on catalog + storefront audit
   alone, makes zero behavioral claims, labels its benchmark proxy, and
   proposes kits as hypotheses rather than sized opportunities. See
   `sample-report.md` for the public-mode voice.

The cast: **Solstice Espresso** (subject - credible enthusiast catalog, zero
merchandising), **Barista Culture** (the merchandising benchmark: named kits,
owner-journey storefront, bespoke wood program), **Modena Espresso** (depth
without guidance - a parts counter).

The fixture also carries one deliberately unmappable SKU (Smart Shot Timer,
category "Gadgets") and two comparable-price pairs the model must reject or
caveat (knock boxes of different sizes; a single handle vs a handle-and-knob
set).

## Run it

```bash
python3 -m whitespace analyze examples/solstice   # note: mode comes back public-data
```

Then `/whitespace examples/solstice` in Claude Code, or
`python3 -m whitespace prompt examples/solstice` for the paste seam.
