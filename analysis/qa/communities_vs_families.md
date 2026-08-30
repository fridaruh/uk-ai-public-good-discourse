# INTERNAL QA — not a finding

This is a robustness check on the intertextual network's structure, not a claim about the corpus. It compares communities found by unsupervised graph clustering against two attributes the author already assigned by hand (MoU family, speaker). It lives in `analysis/qa/` and is cited only if the author decides it is useful as a robustness check in the methods section.

**Method:** Leiden (python-igraph, modularity objective), run on the document-document graph built from `analysis/networks/intertextual_v0.json`, **reference-type edges only** (50 reference edges -> 44 unique document pairs after merging duplicate/bidirectional edges and summing counts as weights). "echo" and "supersession" edges are excluded: echo edges exist by construction only within MoU families and would inflate agreement with the family attribute; supersession is a single hand-coded edge. This network does not depend on Round 1 LLM coding, so it is already corpus-complete (all 35 manifest documents, including the CONTEXT document).

## Comparison table

| Metric | Value |
|---|---|
| Documents (nodes) | 35 |
| Reference edges (unique pairs) | 44 |
| Isolated nodes (no reference edge) | 2 |
| Communities detected | 10 |
| Modularity of detected partition | 0.571 |
| MoU family groups (ground truth a) | 6 |
| **ARI vs. MoU family** | **0.153** |
| Speaker groups (ground truth b) | 16 |
| **ARI vs. speaker** | **0.174** |

## Detected communities (audit)

| Community | n docs | Members (doc_id) |
|---|---|---|
| 1 | 11 | 2025-01-12_PRGOV_PMO_BlueprintTurbochargeAI, 2025-01-13_STRAT_DSIT_AIActionPlanGovResponse, 2025-07-21_PRCO_OpenAI_StrategicPartnership, 2025-07-21_PRGOV_DSIT_OpenAIExpandUKOffice, 2025-12-11_PRGOV_DSIT_NationalRenewalDeepMind, 2026-01-27_PRGOV_DSIT_TopBritishAIExpertise, 2026-01-29_STRAT_DSIT_AIActionPlanOneYearOn, 2026-02-18_PRCO_ElevenLabs_UKAISIPartnership, 2026-06-08_MOU_ElevenLabs_AIOpportunities, 2026-06-08_PRCO_ElevenLabs_UKMOUExpansion, CONTEXT_2025-01-13_STRAT_DSIT_AIOpportunitiesActionPlan |
| 0 | 4 | 2024-01-18_STRAT_CDDO_GenerativeAIFramework, 2024-02-06_REG_DSIT_ProInnovationAIRegulation, 2025-02-10_BLOG_GDS_LaunchingAIPlaybook, 2025-02-10_STRAT_GDS_AIPlaybookUKGovernment |
| 2 | 4 | 2025-01-21_STRAT_GDS_BlueprintModernDigitalGov, 2025-01-21_STRAT_GDS_StateOfDigitalGovReview, 2025-01-21_WMS_DSIT_BlueprintMinisterialStatement, 2025-01-27_BLOG_GDS_SameNameNewAmbitions |
| 3 | 4 | 2025-08-18_BLOG_GDS_AIExemplarsProgramme, 2026-01-19_WMS_DSIT_RoadmapMinisterialStatement, 2026-01-20_BLOG_GDS_OurRoadmapLaunch, 2026-01-20_STRAT_GDS_RoadmapModernDigitalGov |
| 4 | 3 | 2025-02-14_MOU_Anthropic_AIOpportunities, 2025-02-14_PRCO_Anthropic_SignsMOUUKGov, 2026-01-27_PRCO_Anthropic_GOVUKPartnership |
| 6 | 3 | 2025-07-21_MOU_OpenAI_AIOpportunities, 2025-09-16_PRCO_OpenAI_StargateUK, 2025-10-22_PRCO_OpenAI_NextChapterSovereignAI |
| 5 | 2 | 2025-06-15_PRCO_Cohere_CanadaUKPartnerships, 2025-06-16_MOU_Cohere_AIOpportunities |
| 7 | 2 | 2025-12-11_MOU_DeepMind_AIOpportunitiesSecurity, 2025-12-11_PRCO_DeepMind_DeepeningAISIPartnership |
| 8 | 1 | 2025-12-10_PRCO_DeepMind_StrengtheningPartnership |
| 9 | 1 | 2025-02-14_PRGOV_DSIT_TacklingAISecurityRisks |

## Honest reading

ARI ranges from ~0 (no better than chance agreement) to 1 (identical partitions); 0.153 against family and 0.174 against speaker should be read against a graph with 2/35 isolated nodes (documents that cite or are cited by no other corpus document) -- Leiden puts every isolated node in its own singleton community, which mechanically depresses agreement with any coarser grouping like family or speaker unless that grouping also isolates the same documents. A high ARI here would mean explicit citation structure alone recovers who-authored-with-whom or which-MoU-family-a-document-belongs-to; a low ARI means citation structure and family/speaker membership are largely independent signals in this corpus -- which is itself informative (it says the intertextual network is not just reproducing the manifest attributes) but should not be read as a validation or invalidation of the family/speaker coding, since the reference graph is sparse and directional by design (a document only gets an edge if it explicitly names another corpus document), not a semantic-similarity graph built to recover those groupings in the first place.
