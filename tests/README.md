# Integrity Tests

The repository tests validate truth provenance and reusable artifacts; they do not make live paid OpenAI API calls.

- `schema-integrity/` — upstream hash and derived-schema consistency.
- `artifact-integrity/` — compile/static checks for reusable artifacts.
- `fixture-validation/` — confirms fixtures are explicitly marked synthetic.
