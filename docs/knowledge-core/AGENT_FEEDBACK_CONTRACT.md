# Agent Knowledge Feedback Contract

A successful execution may contribute reusable knowledge through `Run.output_metadata.knowledge`.

Example:

```json
{
  "knowledge": [
    {
      "namespace": "agrolog.market",
      "statement": "A reusable factual or analytical conclusion produced by the run.",
      "confidence": 0.82,
      "source_name": "source-or-run-name",
      "source_uri": "https://example.com/source",
      "evidence": [
        {
          "source": "primary-source",
          "locator": "table/row/page/record identifier",
          "uri": "https://example.com/source"
        }
      ]
    }
  ]
}
```

Rules:

1. Contributions from operational agents are always ingested as RAW.
2. The originating project, task, run and execution kind are attached automatically.
3. Duplicate statements in the same namespace are merged by fingerprint and evidence is deduplicated.
4. Confidence supplied by an operational agent does not promote a claim.
5. Promotion follows the independent Knowledge IA / Auditor IA lifecycle.
6. Predictions and hypotheses should later receive outcome feedback so calibration can be measured instead of relying on static memory.
