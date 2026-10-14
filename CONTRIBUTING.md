# Contributing

Start with a reproducible problem and a test. The useful unit of contribution is a correction plus the cases where it should and should not apply.

Run all tests:

```sh
python3 -B -m unittest discover -s tests -v
```

Keep the runtime standard-library-only. Use real temporary directories and CLI subprocesses for file and integration behavior. A matching test does not prove that a model followed an instruction; label host-protocol tests and live-agent evidence separately.

Before opening a pull request:

1. Reproduce the failure with a test.
2. Make the smallest coherent fix and run the suite.
3. Update usage documentation when behavior changes.
4. Check the full diff for personal or organization data, paths and credentials.

Use synthetic examples. Do not copy workplace runbooks, transcripts, incidents, tokens, private repository history or someone else's lesson collection into this project.

Bug reports should include OS, Python version, Brain version, exact command shape with synthetic data, expected behavior and actual behavior. Do not attach your whole agent settings file.
