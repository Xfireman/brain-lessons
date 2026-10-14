# Reproduce the generated-client demo

After installing the current source package:

```sh
brain-lessons demo --scenario generated-client
brain-lessons demo --scenario generated-client --json
```

The demo creates a disposable rule store, checks positive/negative examples, and
feeds two synthetic `apply_patch` events into the real Codex hook handler. It
requires the generated-file patch to return `deny` and the ordinary-file patch
to return no Brain decision. Nothing is edited outside that temporary directory.

The README GIF is a scripted visualization of these actual results. It is not a
recording of a model learning a rule or a live Codex session. No model is called
and no proposed patch is executed. Native Codex enforcement has a separate test:

```sh
python3 -B tests/native_codex.py
```

That test runs actual tools under a disposable Codex configuration with synthetic
loopback model responses. See the README for platform and sandbox boundaries.

## Rebuild the visual assets

Pillow is an optional maintainer dependency; it is not used by the product:

```sh
python3 -m venv /tmp/brain-demo-render
/tmp/brain-demo-render/bin/python -m pip install Pillow
/tmp/brain-demo-render/bin/python scripts/render_demo.py
```

The renderer runs the demo from this checkout, checks its structured results,
then writes `docs/assets/generated-client.gif`, `social-preview.png`, and the
synthetic `demo-result.json`. The GIF has four stages; the PNG is a static share
preview. Frame labels disclose the offline replay.
