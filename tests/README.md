# Test conventions

The project uses CPython `unittest` tests under `tests/`.

Naming conventions:

- Test files: `tests/test_<module>.py`
- Test classes: `Test<ClassOrModuleName>`
- Test methods: `test_<function_name>__<expected_behavior>`
- Hardware-only or fixture-pending coverage: `@unittest.skip(...)` stubs

Run from the repository root with either:

```bash
python -m unittest discover -s tests
```

or:

```bash
python tests/run_tests.py
```

Implementation must stay aligned with rtl_433. Tests may be more explicit or
more exhaustive than rtl_433 as long as they do not change implementation logic.
