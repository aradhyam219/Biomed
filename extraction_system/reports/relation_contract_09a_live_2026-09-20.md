# Contract 09A live semantic proof

Date: 2026-09-20
Source: `PMCID: PMC10444909`, abstract sentences `s0009`–`s0011`
Input SHA-256: `0b87e7eeab93f4d44f55e946aed3ac78a6d1610876f7a31aba74ba695302b8ee`

One normal composed invocation completed successfully with real HunFlair2 NER and the unchanged OpenAI Responses configuration: `gpt-5.6-luna`, reasoning `max`, and a `128000` output-token ceiling. It returned 12 entities and 8 relations; all endpoints, evidence, surface forms, and structured fields passed local validation. The exact machine-readable result is in [relation_contract_09a_live_2026-09-20.json](relation_contract_09a_live_2026-09-20.json).

## Exact rich relations

```json
[
  {
    "source": "E1",
    "target": "E2",
    "predicate": "knockdown_in",
    "assertion": "KNTC1 knockdown in SK-Hep-1 significantly inhibited cell viability, migration ability, and invasion ability.",
    "intervention": "KNTC1 knockdown",
    "effects": ["Cell viability was significantly inhibited", "Migration ability was significantly inhibited", "Invasion ability was significantly inhibited"],
    "context": [],
    "negated": false,
    "surface_form": "Knockdown of KNTC1 in SK-Hep-1",
    "evidence": "Knockdown of KNTC1 in SK-Hep-1 and Huh7 significantly inhibited cell viability, migration ability and invasion ability."
  },
  {
    "source": "E1",
    "target": "E3",
    "predicate": "knockdown_in",
    "assertion": "KNTC1 knockdown in Huh7 significantly inhibited cell viability, migration ability, and invasion ability.",
    "intervention": "KNTC1 knockdown",
    "effects": ["Cell viability was significantly inhibited", "Migration ability was significantly inhibited", "Invasion ability was significantly inhibited"],
    "context": [],
    "negated": false,
    "surface_form": "Knockdown of KNTC1 in SK-Hep-1 and Huh7",
    "evidence": "Knockdown of KNTC1 in SK-Hep-1 and Huh7 significantly inhibited cell viability, migration ability and invasion ability."
  },
  {
    "source": "E4",
    "target": "E5",
    "predicate": "involved_in_regulation_of",
    "assertion": "KNTC1 is involved in the regulation of hepatocellular carcinoma through its interaction with cyclin-dependent kinase 1 (CDK1).",
    "intervention": null,
    "effects": [],
    "context": ["The regulation is described as occurring through interaction with cyclin-dependent kinase 1 (CDK1)."],
    "negated": false,
    "surface_form": "involved in the regulation of hepatocellular carcinoma",
    "evidence": "KNTC1 is involved in the regulation of hepatocellular carcinoma through its interaction with cyclin-dependent kinase 1 (CDK1)."
  },
  {
    "source": "E4",
    "target": "E6",
    "predicate": "interacts_with",
    "assertion": "KNTC1 interacts with cyclin-dependent kinase 1 as the interaction through which KNTC1 is involved in the regulation of hepatocellular carcinoma.",
    "intervention": null,
    "effects": [],
    "context": ["The interaction is described in the context of KNTC1 regulation of hepatocellular carcinoma."],
    "negated": false,
    "surface_form": "its interaction with cyclin-dependent kinase 1",
    "evidence": "KNTC1 is involved in the regulation of hepatocellular carcinoma through its interaction with cyclin-dependent kinase 1 (CDK1)."
  },
  {
    "source": "E4",
    "target": "E7",
    "predicate": "interacts_with",
    "assertion": "KNTC1 interacts with CDK1 as the interaction through which KNTC1 is involved in the regulation of hepatocellular carcinoma.",
    "intervention": null,
    "effects": [],
    "context": ["The interaction is described in the context of KNTC1 regulation of hepatocellular carcinoma."],
    "negated": false,
    "surface_form": "its interaction with cyclin-dependent kinase 1 (CDK1)",
    "evidence": "KNTC1 is involved in the regulation of hepatocellular carcinoma through its interaction with cyclin-dependent kinase 1 (CDK1)."
  },
  {
    "source": "E8",
    "target": "E9",
    "predicate": "inhibits_expression_of",
    "assertion": "KNTC1 knockdown inhibited CDK1 expression.",
    "intervention": "KNTC1 knockdown",
    "effects": ["CDK1 expression was inhibited"],
    "context": [],
    "negated": false,
    "surface_form": "Knockdown of KNTC1 inhibited CDK1 expression",
    "evidence": "Knockdown of KNTC1 inhibited CDK1 expression"
  },
  {
    "source": "E10",
    "target": "E11",
    "predicate": "overexpression_rescues_regulation_by",
    "assertion": "CDK1 overexpression was able to rescue the regulation of KNTC1 on the viability, migration, and invasive ability of hepatocellular carcinoma cell lines.",
    "intervention": "CDK1 overexpression",
    "effects": ["Rescued the regulation of KNTC1 on cell viability", "Rescued the regulation of KNTC1 on migration ability", "Rescued the regulation of KNTC1 on invasive ability"],
    "context": ["Hepatocellular carcinoma cell lines"],
    "negated": false,
    "surface_form": "CDK1 overexpression was able to rescue the regulation of KNTC1",
    "evidence": "CDK1 overexpression was able to rescue the regulation of KNTC1 on the viability, migration and invasive ability of hepatocellular carcinoma cell lines."
  },
  {
    "source": "E11",
    "target": "E12",
    "predicate": "regulates_cellular_abilities_in",
    "assertion": "KNTC1 is described as regulating the viability, migration, and invasive ability of hepatocellular carcinoma cell lines; CDK1 overexpression was able to rescue this regulation.",
    "intervention": "CDK1 overexpression",
    "effects": ["The regulation of viability was rescued", "The regulation of migration ability was rescued", "The regulation of invasive ability was rescued"],
    "context": ["Hepatocellular carcinoma cell lines"],
    "negated": false,
    "surface_form": "regulation of KNTC1 on the viability, migration and invasive ability of hepatocellular carcinoma cell lines",
    "evidence": "CDK1 overexpression was able to rescue the regulation of KNTC1 on the viability, migration and invasive ability of hepatocellular carcinoma cell lines."
  }
]
```

The new fields preserved the intervention, three inhibition outcomes, CDK1 expression effect, rescue intervention, three rescued outcomes, and interaction/disease context without adding process endpoints. Interaction relations kept `intervention: null` and `effects: []`. The remaining semantic caveat is intrinsic to the contract: deterministic validation proves structure and textual grounding, not semantic completeness or truth of normalized assertions.

No KNTC1-specific code, demo-only field, demo-derived predicate ontology, or post-live prompt tuning was used.
