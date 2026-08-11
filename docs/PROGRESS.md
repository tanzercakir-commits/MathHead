# MathHead reconstruction progress

Append-only history for `MH-RECONSTRUCTION-V1`, newest first. Entries are added
only through the repository-owned status tool after adoption.

---

## 2026-08-11 - P2 cross-layer reference fixtures frozen

**Task.** MH-028 (`done`).

**Changed.** Froze one canonical content-addressed foundation bundle with eight exact proof, refutation, ambiguity, unsupported, timeout, backend-disagreement, invalid-certificate, and replay-mismatch scenarios. Added a closed Draft 2020-12 manifest schema, nine governing contract byte bindings, the MH-027 report binding, forty-three deduplicated independently loaded objects, eighteen real payload/checker/replay/backend attachments, explicit present-versus-absent variants, an acyclic dependency graph, plugin routing and cost outcomes, cross-artifact semantic validation, deterministic regeneration, relocated subprocess replay, documentation, and two fail-closed status checks.

**Learned.** Generating all artifacts through the accepted validators exposed a stale Evidence outcome payload ID before the bundle could pass. Binding attachment bytes rather than placeholder hashes made payload, checker-result, replay-log, and disagreement mutations independently observable. The stable bundle identity is 4132b29b69600f8ff48477515853f66bb748c7337735c00db8e634987f70ddca; dependency-minimal and full-jsonschema profiles reproduce the same bytes.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-THEORY-CONTEXT-001=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d (docs/contracts/MH-C-THEORY-CONTEXT-001.json); MH-C-RESOURCE-BUDGET-001=eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045 (docs/contracts/MH-C-RESOURCE-BUDGET-001.json); MH-C-ENGINE-RESULT-001=6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370 (docs/contracts/MH-C-ENGINE-RESULT-001.json); MH-C-EVIDENCE-001=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3 (docs/contracts/MH-C-EVIDENCE-001.json); MH-C-CERTIFICATE-001=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740 (docs/contracts/MH-C-CERTIFICATE-001.json); MH-C-THEORY-PLUGIN-001=2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8 (docs/contracts/MH-C-THEORY-PLUGIN-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-3babd57dd0b6a94875dbf4dce675a11a3b3eccac772f455334e7107b2fb7c592; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-14a076809498ccf04a8cf59a708dc134bd103839e4b5fb892edd90b8bc8cec96; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-891e52c26cb543b20354b1721c46aea37784df6220188f74ec03c4588c3d2cd1; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f

**Evidence.** tools/validate_reference_fixtures.py=3e4859a04a8301b792d12fcd56a62c1ab3c2453c82971d452cbdeab6de57b3d8; tests/reference_fixtures/test_reference_fixtures.py=bfd27ee369b029958ee5aafb22e8f8a81d23e91bf72b97ba7e29cf1e2a654791; docs/fixtures/foundation-v1/manifest.json=c2d1ba4ed240b46f64d1f67fb75a74240b23886561175c0e37310004ab3a86f3; docs/fixtures/foundation-v1/manifest.schema.json=b35d8688c9b693490fb0289aabceee6af04a57af80d20bf5fbeeb2fc4d47e5e2; docs/fixtures/README.md=b3d885270e7cccf5db20bef336fcedd255319b7fe9aec96fa89501deddcfeca7; .project-status.toml=2f8eb4c0c87381cd64576e306fe522c3d0ca930f933b09eb00837495dc5616e4; docs/project-facts.json=5f9d72fef4477a91d722851c15c05be5bb24ee969e2f1f344bc4512297f6e4ee

**Limitations.** These are wire, replay, failure-state, and authority-boundary fixtures, not production parser, solver, checker, worker, kernel, planner, or plugin implementations. Only the proof and refutation fixtures carry checker-attested authority; all failure fixtures remain non-promoting. The existing P2 validators remain future-target contracts. Same-head GitHub runs 31524045326, 31524045295, 31524045277, 31524039588, and 31524039617 succeeded on commit 3c9cd9bfaf8dae3b6d8ddfa851db35a2889d6eb6.

**Next.** Activate MH-030 and inventory the complete trusted computing base before extracting proof-term and checker implementations.

---

## 2026-08-11 - P2 foundation conformance gate implemented

**Task.** MH-027 (`done`).

**Changed.** Implemented one deterministic conformance report for the eight active P2 contracts, their seven normative schemas, canonical accepted and proposal bytes, manifest and acceptance evidence, explicit dependency hashes, targets, supersession, validator references, representative instances, and future implementation bindings. Added dependency-minimal Draft 2020-12 structural meta-validation with an optional standard meta-validator, ten built-in negative probes, twenty-three isolated-copy tests, source-basis hashing, documentation, and two fail-closed project-status checks.

**Learned.** The first status run exposed an undeclared jsonschema dependency: the full environment passed while the dependency-free status interpreter could not import it. A stdlib fail-closed schema keyword validator now preserves identical report bytes across both environments, while installed full profiles still execute the standard Draft 2020-12 meta-validator. Synthetic binding proved signature, accepted-contract hash, and complete source-basis drift are independently rejected.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-THEORY-CONTEXT-001=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d (docs/contracts/MH-C-THEORY-CONTEXT-001.json); MH-C-RESOURCE-BUDGET-001=eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045 (docs/contracts/MH-C-RESOURCE-BUDGET-001.json); MH-C-ENGINE-RESULT-001=6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370 (docs/contracts/MH-C-ENGINE-RESULT-001.json); MH-C-EVIDENCE-001=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3 (docs/contracts/MH-C-EVIDENCE-001.json); MH-C-CERTIFICATE-001=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740 (docs/contracts/MH-C-CERTIFICATE-001.json); MH-C-THEORY-PLUGIN-001=2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8 (docs/contracts/MH-C-THEORY-PLUGIN-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-1b552357645f3505fa8546a5fa1c70c746991fb7a3ec8753f1542d95d4a9df9a; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-eb5e8af39207945884e0cf5d262c151a28ab50e35e2055f20248cd304b9ac1fe; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe

**Evidence.** tools/validate_contract_conformance.py=175878e0be87e035959ec283d3c1a66bbd70b9968286516371ec010fda13b116; tests/contract_conformance/test_contract_conformance.py=9a1f4e8e1d4a8ada86b1923db55b9b27b1e3a70f59aca70fb43fdff36f202275; docs/contracts/reports/foundation-conformance-v1.json=2cbe77d0b2160294ff3ccdf829ec4b5b7b2ad8482c8ce7a8a73b8a6279fc13e2; docs/contracts/FOUNDATION_CONFORMANCE_V1.md=5445797f07fe6f3b085fec97fbcd4f0835249741f64acdc946de450bb3656d92; .project-status.toml=b9bd13e8042a712c2692bc81efe03d0476415f486c517d88498b9aa8e2f30ef1; docs/project-facts.json=303e4c441c215b256317c79a6f878eb8d4800f1cf53e476f167b732f77e2a47e

**Limitations.** The seven future foundation targets remain not_implemented and therefore have no production runtime behavior to certify. Conformance proves representation, identity, dependency, validator, and implementation binding only; it grants no mathematical truth, checker honesty, solver correctness, runtime isolation, or cross-layer semantic outcome. Golden end-to-end artifacts remain MH-028. Same-head GitHub runs 31521201240, 31521201194, 31521201219, 31521195246, and 31521195216 succeeded on commit 56da7ebbf8cfe92e79b13b9987eed8e0de9696f4.

**Next.** Activate MH-028 and freeze minimal golden cross-layer fixtures for proof, refutation, ambiguity, unsupported input, timeout, backend disagreement, invalid certificate, and replay.

---

## 2026-08-11 - Canonical TheoryPlugin contract accepted

**Task.** MH-026 (`done`).

**Changed.** Accepted a closed canonical TheoryPlugin descriptor covering stable API and implementation identity, separate producer and checker components, exact foundational contract compatibility, bounded capability fragments and format ranges, deterministic planning cost and routing, the fixed plan_cost/solve/check/explain ABI, lifecycle, isolated effects, child budgets, cancellation, replay, and hard limits.

**Learned.** Adversarial review made theory membership and quantifier count explicit routing dimensions, bound the per-quantifier coefficient to quantifier count rather than nesting depth, and made unknown routing kinds fail closed. The resulting descriptor can be negotiated and costed without importing or trusting plugin code, while solve remains producer-only and check remains independently attestable.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-THEORY-CONTEXT-001=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d (docs/contracts/MH-C-THEORY-CONTEXT-001.json); MH-C-RESOURCE-BUDGET-001=eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045 (docs/contracts/MH-C-RESOURCE-BUDGET-001.json); MH-C-ENGINE-RESULT-001=6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370 (docs/contracts/MH-C-ENGINE-RESULT-001.json); MH-C-EVIDENCE-001=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3 (docs/contracts/MH-C-EVIDENCE-001.json); MH-C-CERTIFICATE-001=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740 (docs/contracts/MH-C-CERTIFICATE-001.json); MH-C-THEORY-PLUGIN-001=2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8 (docs/contracts/MH-C-THEORY-PLUGIN-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-dec60251d3793db5054da26578c3ed05dc5d013690620d51d35628414c04a709; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b

**Evidence.** docs/contracts/MH-C-THEORY-PLUGIN-001.json=2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8; docs/contracts/schemas/theory-plugin-v1.schema.json=c3d234f725e2c3f0e6fa02507be83190bde71f8ddae6f5a08cd6395065d77142; tools/validate_theory_plugin_contract.py=ae46fada73138b533149aa20ff32bce03cfabb60637477f8ea19ff21b07a822e; tests/theory_plugin_contract/test_theory_plugin_contract.py=afbe87c55aaa3a6c9b6f49d33c7411c2dda40647fe080fa47b091a2a83956ed0; docs/contracts/reports/verification-v1.json=4043cd8eda800426a3ef609783e9d49b0c22a042f7e3ae8acccb8816b53fe723; docs/project-facts.json=012735b2c7def4601f6706cd5bf0c698e261ee343cd530857fb558da8adde848

**Limitations.** The future target mathhead.plugins:TheoryPlugin is not implemented. Structural conformance and declarative routing do not establish plugin honesty, mathematical truth, runtime isolation, registry conflict handling, or cross-layer byte compatibility; these remain assigned to MH-027, MH-028, MH-040 through MH-047, MH-050 through MH-056, and MH-060 through MH-067. Same-head GitHub runs 31519053882, 31519054184, 31519053936, 31519048268, and 31519048260 succeeded on commit 75dcb6f34d2784bb9c785315fab4e30087310e86.

**Next.** Activate MH-027 and build cross-contract conformance tests for schemas, signatures, hashes, validators, contradictions, and implementation-side drift.

---

## 2026-08-11 - Independent Evidence and Certificate contracts accepted

**Task.** MH-025 (`done`).

**Changed.** Accepted separate canonical Evidence and Certificate envelopes: Evidence records versioned content-addressed producer artifacts without mathematical authority, while Certificate binds independently validated Evidence bytes to a distinct checker, deterministic replay observations, checker-produced artifacts, exact trust closure, explicit verdicts, terminal resource state, and diagnostics.

**Learned.** Sequencing acceptance made the trust boundary enforceable: the Certificate contract binds the already accepted Evidence contract hash, and adversarial tests require independently loaded schema-valid Evidence bytes, reject producer/checker identity or implementation aliasing, and classify replay mismatch as invalid rather than verified.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-THEORY-CONTEXT-001=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d (docs/contracts/MH-C-THEORY-CONTEXT-001.json); MH-C-RESOURCE-BUDGET-001=eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045 (docs/contracts/MH-C-RESOURCE-BUDGET-001.json); MH-C-ENGINE-RESULT-001=6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370 (docs/contracts/MH-C-ENGINE-RESULT-001.json); MH-C-EVIDENCE-001=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3 (docs/contracts/MH-C-EVIDENCE-001.json); MH-C-CERTIFICATE-001=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740 (docs/contracts/MH-C-CERTIFICATE-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-4813a05de8ffa47afd4d9a9edab05f70349a1fcdcf9b95a28e10f2daf982d878; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173

**Evidence.** docs/contracts/MH-C-EVIDENCE-001.json=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3; docs/contracts/MH-C-CERTIFICATE-001.json=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740; docs/contracts/schemas/evidence-v1.schema.json=4f1d0a4438812bdd7b204d0d0fe0098ff06cc274eb2e4ed7fa66a3f3a76b426f; docs/contracts/schemas/certificate-v1.schema.json=cbc8f68469593e1d2b34588b49eaa16e37d597c863457945dd5b9ce5ae138760; tools/validate_evidence_certificate_contracts.py=0557d9efbaae661557d7288580c284e662e9ef6b188a8d737055213ffcee75cd; tests/evidence_certificate_contracts/test_evidence_certificate_contracts.py=bede969b130bfc4b22616f67675fc93091d82f6d507d59a02e17474d058a79b0; docs/contracts/reports/verification-v1.json=8c357f019578abc357cee189030c174902059df3e6f4e0f5790a77353cc66355; docs/project-facts.json=1d5284ce5a80be14d42baf7747667c1c73338060fa48835f3da2e4ddc7ef41ba

**Limitations.** The future targets mathhead.evidence:Evidence and mathhead.certificates:Certificate are not implemented. Structural validation does not establish checker honesty or mathematical truth, and referenced dependency, payload, and checker-artifact bytes are supplied and hash-verified by consumers rather than opened implicitly. Runtime kernels, conformance expansion, cross-layer fixtures, and theory-specific semantics remain in MH-027, MH-028, MH-030 through MH-037, and MH-060 through MH-067. Same-head GitHub runs 31516846941, 31516846913, 31516846909, 31516843150, and 31516843266 succeeded on commit 34c6b25b6100c552a14215d7315f84954b6e7ad7.

**Next.** Activate MH-026 to accept the canonical TheoryPlugin contract.

---

## 2026-08-11 - Canonical EngineResult contract accepted

**Task.** MH-024 (`done`).

**Changed.** Accepted a closed canonical EngineResult envelope that binds ProblemIR, TheoryContext, ResourceBudget, replay identity, provenance, artifacts, ordered assessments, execution outcomes, terminal budget state, and diagnostics while separating execution completion from mathematical verdicts.

**Learned.** Adversarial review corrected refutation support so independently checked proofs of negation do not require counterexamples and allowed verified witnesses to support existential proofs without weakening the independent checker or external verifier trust boundary.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-THEORY-CONTEXT-001=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d (docs/contracts/MH-C-THEORY-CONTEXT-001.json); MH-C-RESOURCE-BUDGET-001=eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045 (docs/contracts/MH-C-RESOURCE-BUDGET-001.json); MH-C-ENGINE-RESULT-001=6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370 (docs/contracts/MH-C-ENGINE-RESULT-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-0a795cd7798d2a725da0b3780cb713a80b43e932f652f501b03d0303b1634ae1; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79

**Evidence.** docs/contracts/MH-C-ENGINE-RESULT-001.json=6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370; docs/contracts/schemas/engine-result-v1.schema.json=4cd26ad69c6528a7553a429d06f224c79ae6b01b7d9cc0fa41ccb7c4d20cc948; tools/validate_engine_result_contract.py=161f4adf9bba750414f4517faf3784b7b8a42dd32e46873e9490b1391a669beb; tests/engine_result_contract/test_engine_result_contract.py=2baae51d8387c478432d649fd92becebab9b45ec8579b35acf0e5a121dc257ce; docs/contracts/reports/verification-v1.json=ad7ec8896741ec3a6feb3e461d5406f2f7986aa92f734f058e689dc17d31941a; docs/project-facts.json=4c8089aafeeb3ca807ed3d5216ec2b154306cc1f411fb456ac8687b04c8fb976

**Limitations.** The target mathhead.results:EngineResult is not implemented yet. Structural validity does not establish truth; cross-artifact byte verification, independent Evidence and Certificate semantics, conformance fixtures, and runtime enforcement remain in MH-025, MH-027, MH-028, and later implementation work. Same-head GitHub runs 31514329850, 31514329789, 31514329802, 31514323122, and 31514323140 succeeded on commit 6f06ac3066a8a4e4fb71825064b7126703134fd1.

**Next.** Activate MH-025 to accept independent Evidence and Certificate contracts.

---

## 2026-08-11 - Canonical ResourceBudget contract accepted

**Task.** MH-023 (`done`).

**Changed.** Accepted the closed ResourceBudget contract and normative Draft 2020-12 schema for exact ten-dimension limits, ordered accounting events, compositional child reservations and reconciliation, monotonic wall, process-tree memory, and nesting observations, and explicit cancellation, exhaustion, and truncation outcomes.

**Learned.** Adversarial review added hard 64 MiB input and four-million-node ceilings before acceptance and separated cumulative resources from observational wall, memory, and nesting dimensions to prevent double accounting under parallel children. Same-head GitHub workflows 31511543232, 31511543233, 31511543254, 31511539927, and 31511539923 concluded success; GitHub left four child wrappers stale in_progress after every child step completed without failure.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-THEORY-CONTEXT-001=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d (docs/contracts/MH-C-THEORY-CONTEXT-001.json); MH-C-RESOURCE-BUDGET-001=eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045 (docs/contracts/MH-C-RESOURCE-BUDGET-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-82bc75f36616c4da97ef5fa018416478c8914f17f545b693d1037c96ef5cfa7e; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae

**Evidence.** docs/contracts/MH-C-RESOURCE-BUDGET-001.json=eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045; docs/contracts/schemas/resource-budget-v1.schema.json=e735dee47394bf50c10ac571dfc8923fd1da851e258b1d9f42e1a66bb9d85e78; tools/validate_resource_budget_contract.py=6abc8eeb31160c32f0ae34ce7c3442482991a72990b2184a47eb14b95ecd3719; tests/resource_budget_contract/test_resource_budget_contract.py=394927868019b7b337cb6549b85502c3f8ea778b2d9b3f3c2a093d87f5b82a4d; docs/contracts/reports/verification-v1.json=6e96bed169e7b4687dfaaf58b57390fabbd69e3078fc1b20d8dbe13b153e515b; docs/project-facts.json=a177c4235a60e7fc5ab842d76269e527726bf5f298af28d04cf633661304af76

**Limitations.** The accepted artifact intentionally targets the not-yet-implemented mathhead.budget:ResourceBudget constructor. Standalone validation structurally binds child budget hashes and usage assertions; independent child-byte verification, runtime enforcement, worker isolation, and cross-layer fixtures remain assigned to MH-027, MH-028, and MH-052.

**Next.** Activate MH-024 and accept the canonical EngineResult contract for verdicts, epistemic tiers, readings, assumptions, witnesses, certificates, provenance, budget consumption, diagnostics, and replay identity.

---

## 2026-08-11 - Canonical TheoryContext contract accepted

**Task.** MH-022 (`done`).

**Changed.** Accepted the closed TheoryContext contract and normative Draft 2020-12 schema for stable context and declaration identities, explicit axiom, definition, lemma, imported-origin, and local-hypothesis authority, content-addressed imports, monotonic revisions, bounded consistency states, canonical identity, and fail-closed resource limits.

**Learned.** Adversarial review caught and closed two pre-acceptance gaps: the consistency basis now binds context and revision identity, and resource accounting now rejects oversized nested mapping keys. Local scope rules also prevent a scoped claim from becoming public or escaping through an unscoped dependent. GitHub same-head runs 31508802990, 31508802977, 31508802962, 31508798025, and 31508797965 all completed successfully: CI 26/26, reproducibility 9/9 on both PR and push, and governance 2/2 on both PR and push.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-THEORY-CONTEXT-001=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d (docs/contracts/MH-C-THEORY-CONTEXT-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-4c78510ed9b96de2ea207638adccca4bd0ba9d070be988f0e70a2a69e7aec209; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c

**Evidence.** docs/contracts/MH-C-THEORY-CONTEXT-001.json=d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d; docs/contracts/schemas/theory-context-v1.schema.json=6a6e40070ba0a3209f5bfcfa0cc912d1ec08359a178611a40d61ffadda5819ec; tools/validate_theory_context_contract.py=e4ad17b3face322da383265aa5885fe809351834d91f5c53b4fa95b44e55a1a9; tests/theory_context_contract/test_theory_context_contract.py=6a28fa03bfde81a5a3bed37a4ed739967d2f78ed9776ce7d49cba8866f148427; docs/contracts/reports/verification-v1.json=7dae94f9feb048e61d404a00a88ed327e719ce1d214bf58a093d16cf1dc25419; docs/project-facts.json=1966eaeb0dc4a43e2a3d06a945edad3dd6e23a380c078a7dea24d4f7e805ec5f

**Limitations.** The accepted artifact intentionally targets a not-yet-implemented mathhead.context:TheoryContext constructor. Parent monotonicity and ProblemIR entity existence require independently hash-verified cross-artifact bytes; implementation binding and golden cross-layer enforcement remain assigned to MH-027 and MH-028. Structural validity makes no theorem-truth or global-consistency claim.

**Next.** Activate MH-023 and accept the canonical resource Budget contract for wall time, CPU, memory, solver calls, generated objects, proof size, cancellation, truncation, nesting, and child-budget accounting.

---

## 2026-08-11 - Canonical ProblemIR contract accepted

**Task.** MH-021 (`done`).

**Changed.** Accepted the closed, solver-neutral ProblemIR contract and normative Draft 2020-12 schema with typed domains, variables, expressions, relations, statements, definitions, assumptions, ordered goals, complete alternative readings, source provenance, canonical identity, and fail-closed resource budgets.

**Learned.** Adversarial review of immutable MH-C-PROBLEM-IR-001 found numeric-literal and nesting budgets that were not fully enforceable; it was preserved and superseded by MH-C-PROBLEM-IR-002. GitHub runs 31505894788, 31505894683, and 31505889060 passed 26/26 CI jobs, 9/9 reproducibility jobs, and 2/2 governance jobs. Pull-request governance run 31505894798 had both jobs succeed but its wrapper remained stale in_progress.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-CONTRACT-ARTIFACTS-002=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750 (docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-a1d76a7cc945d58c43e5fe49d6f5bf99c174032109ff785783af62694282d43f; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68

**Evidence.** docs/contracts/MH-C-PROBLEM-IR-002.json=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286; docs/contracts/schemas/problem-ir-v1.schema.json=dcf871f15ebbae06b0eca285a115f2545defc00cb0befc23e3cc574d8523df2c; tools/validate_problem_ir_contract.py=b110b10aa25075734b1afeb34a9dff8dc8c5a0f0871c68e2d6854e403f7662cb; tests/problem_ir_contract/test_problem_ir_contract.py=77b30b6218f540c241f6a808447812ed2d0ac64db4cfb34b123a2ea12989a85a; docs/contracts/reports/verification-v1.json=aabadb542d11414e8987fd5144385fa84028b3bed3d27d18353e6f18782fb889; docs/project-facts.json=ade3d0953de05826435cad39df38f7698436da1b0b94b588ed62d9d836c2fac2

**Limitations.** The accepted artifact intentionally targets a not-yet-implemented mathhead.ir:ProblemIR constructor; implementation binding and cross-layer fixture conformance remain assigned to MH-027 and MH-028. Representation validity makes no mathematical truth claim.

**Next.** Activate MH-022 and accept the canonical TheoryContext contract for axioms, definitions, imported lemmas, local hypotheses, consistency state, namespaces, revisions, and dependency hashes.

---

## 2026-08-11 - Transactional contract artifact workflow implemented

**Task.** MH-020 (`done`).

**Changed.** Implemented one repository-owned propose, prescreen, accept, verify, and recover command with closed schemas, canonical identities, exact proposal separation, atomic rollback, supersession, AST signature/hash binding, bounded validators, deterministic reports, documentation, and fail-closed status ownership.

**Learned.** The first accepted tool contract exposed a validator that depended on the invoking Python environment; immutable MH-C-CONTRACT-ARTIFACTS-001 was therefore preserved and superseded by portable 002. GitHub runs 31502788917, 31502788907, and 31502790393 passed 26/26 CI jobs, 9/9 reproducibility jobs, and 2/2 governance jobs.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md); MH-C-ENV-002=aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d (docs/contracts/MH-C-ENV-002.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-d66a2549cc20e08070fabe5500fcb30853ac7cede4ea849031911aea2e6d1676; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19

**Evidence.** tools/contract_artifacts.py=7d455490a0ea272a115456aaaba4e330fbb0add150e25d6ee565d2215f596a28; tests/contract_artifacts/test_contract_artifacts.py=af9701819124d64cc82385a1cdc5403848a33470ccdc02248c13a1cf6aa1364e; docs/contracts/MH-C-CONTRACT-ARTIFACTS-002.json=602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750; docs/contracts/reports/verification-v1.json=2e4f7e4fcf80dcfacf70b6e03efd2395e823565e990297dbcb45a46b349e8b3d; .project-status.toml=eaa3db133322972d9f62743a145fa16681a4798f95055fbea94485e85a336dc1; docs/project-facts.json=50acfcef47ff985b95546aeec78a7c8fc4705e6f2410747654ce0efb322785b5

**Limitations.** The consistency pre-screen proves only deliberately decidable syntactic contradictions; semantic intent still depends on the named acceptance authority. Static binding covers top-level Python callables and constructors, while deeper Protocol, dataclass, enum, and Literal conformance remains assigned to MH-021 through MH-027.

**Next.** Activate MH-021 and accept the canonical ProblemIR contract for typed variables, domains, quantifiers, expressions, relations, definitions, goals, source spans, ambiguity, and serialization.

---

## 2026-08-11 - Legacy compatibility corpus frozen with three clean G2 runs

**Task.** MH-017 (`done`).

**Changed.** Accepted MH-C-LEGACY-COMPAT-001 and froze ten source-bound differential cases across success, refuted, unsupported, solver-timeout, and error outcomes; added typed allowlist-only normalization, isolated replay watchdogs, independent mutation validation, and required core/status profile ownership.

**Learned.** The corpus replays unchanged on Linux, macOS, and Windows across Python 3.10 through 3.12 in GitHub. Consecutive clean checkpoints afd31de, 614d495, and 4d7a32e each passed CI, reproducibility, and governance; final runs 31499429684, 31499429739, and 31499429692 were green, with 87.69 percent coverage over 2120 selected tests.

**Contracts.** MH-C-LEGACY-COMPAT-001=53a9e09b58738ccdbb596ec28fa15d989d4cba66cecd46c5c97ca8d1da1f9412 (docs/contracts/MH-C-LEGACY-COMPAT-001.json); MH-C-ENV-002=aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d (docs/contracts/MH-C-ENV-002.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f

**Evidence.** docs/contracts/MH-C-LEGACY-COMPAT-001.json=53a9e09b58738ccdbb596ec28fa15d989d4cba66cecd46c5c97ca8d1da1f9412; docs/reconstruction/legacy-compat-v1.json=b2110dd16283da5c121991c327d7e3d873d75b6708c792bb3dd95610f63f5896; tools/legacy_compat.py=eb052270ac7e08d9e9b0abfe12dcc8cd2bb06255182fdfe414566ed7679b5891; tools/validate_legacy_compat.py=b8125cf5a7a547133a9d5db2eb1d85398db2cbe6c531095eeb237dccf2882f03; tests/compatibility/test_legacy_compat.py=554a9560fb0b757c89d74438e479b1c144c19f76475611d92d0e014c1be472cb; tools/dev_profiles.json=57d268df3358d37598e7a008d8ae9f2bd22bf189dde5c59a74343601a2fc7a42; .github/workflows/ci.yml=1ba54d9d4847b7566b1058a0cc88bf9c4ffe5d98dc4a9d1ce0318859f0c58b02; docs/project-facts.json=7869ac7ad62254b3e64ea54ff421f966f74a3dcbc4b592a77e165a337a172e23

**Limitations.** The corpus is deliberately representative rather than exhaustive, and MH-ADR-0004 continues to exclude backend versions, raw timing, explanations, witnesses, and incidental ordering from compatibility unless a case explicitly freezes them. Direct legacy internal imports remain outside the SemVer surface.

**Next.** Activate MH-020 and implement strict contract artifact proposal, pre-screen, acceptance, hash, signature-binding, and deterministic-report tooling under MH-C-WORKFLOW-001.

---

## 2026-08-11 - Full supported CI matrix made portable and green

**Task.** MH-016 (`done`).

**Changed.** Centralized every untrusted expression parse behind MH-C-AST-PARSE-001, normalized Python 3.10 NUL rejection without weakening caller grammars, and made canonical discovery proof selection independent of host speed under MH-C-DISCOVERY-PORTFOLIO-002.

**Learned.** CPython 3.10 raised ValueError for embedded NUL where newer interpreters raised SyntaxError; after that fix, macOS ARM alone exposed a timeout-dependent proof label in the generated discovery report. Clean GitHub runs 31496709716, 31496709637, and 31496709688 finished 26/26 product jobs, 9/9 reproducibility jobs, and 2/2 governance jobs green; coverage was 87.69 percent over 2107 tests.

**Contracts.** MH-C-AST-PARSE-001=69884d482ed38e34ea0b1cd1c6d3349d2dca389704ddbd385d8e493b30886965 (docs/contracts/MH-C-AST-PARSE-001.json); MH-C-DISCOVERY-PORTFOLIO-002=247534720fe49f89a9961196701cc12a954f5e95e12bd7b8b8c5a07318b3bf7b (docs/contracts/MH-C-DISCOVERY-PORTFOLIO-002.json); MH-C-ENV-002=aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d (docs/contracts/MH-C-ENV-002.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e

**Evidence.** src/mathhead/parsing.py=b0a3f36f0a3850f3be1b9b99fe18a5454949fd27bdb28969da812ea877d2ac1b; tests/parsing/test_ast_parse_contract.py=5e923d736e76dd1a9e2a38dddc4320257cdd996c5675ba3e8d6b19b283d685b3; tools/validate_ast_parse.py=fad7cfb7828417d257637e616ad18804c306b8f03f4a846e65b5eda8d512ac96; src/mathhead/discovery/arithmetic.py=0eaa02b5100fe3b5cb960beec92b29eec9f0a6f78cecfe4ebe758224dde40cd0; tests/test_discovery_portfolio_contract.py=bc3a471e914a1344be3f904e87fd4dd06fd672bfa5b0d5b33d0d82a1a84794b1; tools/validate_discovery_portfolio.py=7e3da4de228e6f186ca3658fd05a59a2c6c3c95acdf13543ebdc6df7b4dd3749; .github/workflows/ci.yml=1ba54d9d4847b7566b1058a0cc88bf9c4ffe5d98dc4a9d1ce0318859f0c58b02; docs/project-facts.json=9dbbafcf6e1eee78b1bd68d5eaf2cfe82bf1df8ddbdd60d5a2dcf600ae643190

**Limitations.** The local host provides only CPython 3.14, so solver and slow profiles declared for Python 3.10 through 3.13 rely on the clean supported GitHub run. The initially accepted portfolio 001 artifact is preserved immutably and explicitly superseded by corrected 002 before implementation.

**Next.** Activate MH-017 and freeze representative legacy compatibility outputs for differential migration.

---

## 2026-08-11 - Generated project facts and executable docs ownership

**Task.** MH-015 (`done`).

**Changed.** Moved package SemVer to one source, bound Hatch dynamically, generated canonical live facts and README claims, classified 45 published snippets, and attached exact validator nodes to governed profiles.

**Learned.** A legacy discovery packaging test still assumed static project.version; GitHub caught it and the test now verifies dynamic Hatch metadata. The current generated boundary resolves package 1.2.0, 171 MCP tools, 2115 collected tests, and all nine ENV-002 profiles.

**Contracts.** MH-C-PROJECT-FACTS-001=701a5f99a41f3f2226859fac98c5a8050915d88fb83111a53e5172a2b2760aad (docs/contracts/MH-C-PROJECT-FACTS-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-4570c9d4eb4bd3cd2232aa97513c55bfbcb1e30b2b992265c1ff844bc4311134; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0

**Evidence.** docs/contracts/MH-C-PROJECT-FACTS-001.json=701a5f99a41f3f2226859fac98c5a8050915d88fb83111a53e5172a2b2760aad; src/mathhead/_version.py=23474a0d501f6e7f041e155baa1edad622b90e0018a741ff4cbf6332c0294e8b; tools/project_facts.py=3b0ffe3ce75a7d920eb8b5b2e03ccb6159badf8c9137e2d2942f277c34855879; tools/validate_project_metadata.py=93e43add58d99b58b6d7af692f8de108d3e370692e2d832798cd07b494f24eb1; docs/examples.toml=bcbb6afb3889dad63455f9bff4fbdfbe98bb08ec2bec123b857203d9e7705a5f; docs/project-facts.json=390c3f0219a44af45f0ab257d3ae2baccc5d9592f2e9838f6d79d5cdf20972d4; README.md=238555c7be34d0f087fd56a9a46a5145788e30ac611a3a0ec3676021b372a96c; tests/project_metadata/test_project_metadata.py=cdf2125777b77fb5cabb5d96505f3c85683fb653ad2f152b0731f4259265c0c3

**Limitations.** Frozen legacy status records retain historical numeric claims by design; current README claims are generator-owned. Python 3.10 arbitrary-NUL fuzz failures are outside this task and remain assigned to MH-016.

**Next.** Activate MH-016 and normalize portable parser exceptions without weakening malformed-input rejection.

---

## 2026-08-11 - Governed test profiles split and verified

**Task.** MH-014 (`done`).

**Changed.** Bound all 2,108 collected tests to disjoint core, solver, discovery, docs, live-MCP, or explicit slow ownership; removed auxiliary monolithic commands; routed CI through bounded profile gates with full-history baseline checkout and retained the explicit coverage gate.

**Learned.** GitHub run 31491575410 proved the separated slow, solver, discovery, docs, live-MCP, core 3.11/3.12, build, tracker, and reproducibility work independently; coverage job 93779084468 passed 2,073 selected tests at 87.65 percent in 268.45 seconds, while Python 3.10 consistently exposed the pre-existing NUL parser defect assigned to MH-016.

**Contracts.** MH-C-ENV-002=aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d (docs/contracts/MH-C-ENV-002.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-26517e19fadb8780a96151632a25c7026ca11f064cceec96d9e319e440330112; reconstruction-plan=passed/exit-0/output-33d28b548fc5dc6ec67f83247ce1954ae62de6a2d106a0461bd0737f15928981; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-78474777d43a75e8915d7f07da2d995d075a90bc6a947821f0e1d3bec64eb087; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-f84e4ac87ba5e41a9545a9a3a962007e06b4731eec24383ccdf24759e4feebbd; dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-51f85123db48543345fbdac4843f2cc4d991172277b12aa8d709c144559d613c; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312

**Evidence.** docs/contracts/MH-C-ENV-002.json=aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d; tools/dev_profiles.json=dde1cf64f0419a27a93cd8e96d993d4ec53f3b45be9b3b0d48d45b4b05e39026; tools/validate_dev_environment.py=91c3de90650e7269414d29548a25f54234e325af35187f9b6c020b4fb08e8966; tests/conftest.py=8ce9fa538cc600f6509b8e85de8301a9d0104edb23693c118c898dd646bff8a7; .github/workflows/ci.yml=1ba54d9d4847b7566b1058a0cc88bf9c4ffe5d98dc4a9d1ce0318859f0c58b02; pyproject.toml=8ad7a34a14634a68d7309dfb2faa99e87c6fa2cb96d05c260e07f5217ba7f811

**Limitations.** The CI run remains red only on the three Python 3.10 core jobs because four arbitrary-NUL fuzz paths leak ValueError; this is product compatibility work for MH-016, not a profile ownership, timeout, coverage-floor, or workflow-routing failure.

**Next.** Activate MH-015, centralize version and generated project facts, and bind every published executable example to a declared profile.

---

## 2026-08-11 - Portable live MCP semantics verified across supported hosts

**Task.** MH-013 (`done`).

**Changed.** Bound live test selection to accepted MH-C-LIVE-MCP-001, proved stdio capability with an independent fixed child, allowed skips only for explicit OS denials, kept every server and protocol defect red, and added bounded terminate-kill-wait-stream cleanup.

**Learned.** GitHub run 31488731351 jobs 93769993963 (macOS 3.11), 93769993976 (Ubuntu 3.11), and 93769993905 (Windows 3.12) each completed with 2,082 passing and 22 skipped tests. Relative to the prior suite, the nine new contract tests passed and only the three deliberately backend-gated real-geng tests were added to skips, proving all five live MCP assertions executed rather than skipped.

**Contracts.** MH-C-LIVE-MCP-001=3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143 (docs/contracts/MH-C-LIVE-MCP-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-affd66a226354fa8ebd14da134061139ec204ac944aff9bc0bf8958db3eecb09; reconstruction-plan=passed/exit-0/output-33d28b548fc5dc6ec67f83247ce1954ae62de6a2d106a0461bd0737f15928981; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-534f70123265827d7ec95d4d80095b3bef9666812cecec8c84a6dbbb2bb45e37; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-55b5802b273d56ed40f6f3f890e9e7f948f859c1e42897e2be4ee823516ba779; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-51f85123db48543345fbdac4843f2cc4d991172277b12aa8d709c144559d613c; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312

**Evidence.** docs/contracts/MH-C-LIVE-MCP-001.json=3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143; src/mathhead/server/live.py=983cd93b2917bb5b6b17828ce90dc735914583d24a339eb8c63e84772dd73168; tests/live_mcp/test_live_mcp_contract.py=d554bc42fd6a727aa7fb0e7650beb5928c0151aca9396dda2fd0eba44aebb44a; tests/test_mcp_live.py=2492cdeebedb9afb8e137b5017e464fb566728477f8ccab52e6781ddfacceea0; tools/validate_live_mcp.py=c827a339cddd88dd2d66d651a13a9cde590de532dc850de6339c0ece481775c9; docs/mcp-api.md=1516b078e7cac530dc805c36f94e8eaef3723f18647dbab21635a8d0196e938b

**Limitations.** The only local interpreter is CPython 3.14, where MCP 1.x starts the server but stalls during handshake; the independent probe reports supported and the application test remains red rather than being mislabeled unsupported. Supported CI Python 3.10-3.12 is green for the live assertions; interpreter claim alignment belongs to MH-014 and MH-015.

**Next.** Activate MH-014, supersede the environment contract, split core, solver, discovery, docs, live-mcp, slow, and release profiles, and preserve coverage as an explicit bounded gate.

---

## 2026-08-11 - Finite graph enumeration bounded and independently verified

**Task.** MH-011 (`done`).

**Changed.** Bounded pure graph search to order 6 and 2,000 objects, bounded nauty search to order 8 and 20,000 objects, refused unsafe requests before enumeration, made scans incremental and first-witness stopping, bounded geng subprocesses, and added real fast-backend CI evidence.

**Learned.** GitHub CI run 31488731351 job 93769993769 completed the dedicated real-nauty graph-budget step successfully after solver bootstrap. The prior cross-platform run 31486792484 completed core legacy-full on Linux, Windows, and macOS in roughly two to three minutes without the former graph timeout.

**Contracts.** MH-C-GRAPH-BUDGET-001=3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794 (docs/contracts/MH-C-GRAPH-BUDGET-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-ae625f9cbe04a6b1f6c6f001f3f57776ebfb3c7c1485391cf6bb20e2a95ac982; reconstruction-plan=passed/exit-0/output-3d49650537d551b9ee8a5c7d59991b71238d12aab5e316a78eac065a8452112f; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-2edc2b69e0fd5ec0dc44a4b303f3ffc05aa4025db78fe17a9436fa636f72f83e; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-55b5802b273d56ed40f6f3f890e9e7f948f859c1e42897e2be4ee823516ba779; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-51f85123db48543345fbdac4843f2cc4d991172277b12aa8d709c144559d613c; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312

**Evidence.** docs/contracts/MH-C-GRAPH-BUDGET-001.json=3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794; src/mathhead/discovery/product.py=d9098f1082af22f1d65e2e440aa2c815c3daad8003c4bcfad74f98532bfc911a; src/mathhead/discovery/formalize.py=033ae47cc116a83dc2baaf03090bf6b61947b5e5926e1da3422919758f0f4aac; src/mathhead/discovery/nauty_scale.py=988c6030ae525608bcff2388d6954d3e4194a1a8acacc548ea44e9e11abf6c3f; tests/graph_budget/test_graph_budget.py=3fbc911028bffe564805c87ace8a29cbeb26fda545537b44a10e1f0a49992ba5; tests/graph_budget/test_fast_backend.py=d05d7e9fb3a30d6ae4a3f1c7ef848f707c991f22960eb896ea62a43356a7593e; tools/validate_graph_budget.py=3d77f7f3333905c838630555415f3573246aeafc30139f7b0a27f3a3c03b9f7e; tools/dev_profiles.json=1c7bfede267921f5b90fe1123e3f9cab9d807e0083ccf3bb0bcfd26dac865418; .github/workflows/ci.yml=e42fcff4ac3b73931562570fc923f8fa757c56511ad5a2a2ef6e1f4282c62442

**Limitations.** The all-tests solver coverage command remains a separate monolithic 1,200-second gate and is assigned to MH-014 profile splitting; the dedicated capability and real-nauty graph-budget steps are independently green and no graph completion claim relies on that oversized aggregate.

**Next.** Finish MH-013 on the supported live-MCP matrix, then split the oversized test profiles under MH-014 without deleting coverage.

---

## 2026-08-11 - Accepted live MCP semantics implemented pending supported CI

**Task.** MH-013 (`partial`).

**Changed.** Accepted MH-C-LIVE-MCP-001 byte-identically; added a frozen independent stdio capability probe with an allow-listed unsupported boundary, bounded terminate-kill-wait cleanup, strict live-test selection, a live_mcp marker, deterministic EOF cleanup, and a dependency-free validator.

**Learned.** The managed local Python 3.14 environment can complete the independent fixed-child stdio probe and start the MathHead server, but MCP 1.x then stalls during handshake; the accepted semantics correctly classify this as an application or SDK compatibility failure rather than a pipe-capability skip.

**Contracts.** MH-C-LIVE-MCP-001=3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143 (docs/contracts/MH-C-LIVE-MCP-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-7b3a3c7be87541f4cc598dcd2c5987799b258a37bec02f641d42557ea29e2e55; reconstruction-plan=passed/exit-0/output-3d49650537d551b9ee8a5c7d59991b71238d12aab5e316a78eac065a8452112f; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-353cae0d901addfc670a73216f8c3b4a07cc617d7ee4b5c58b6d573e730efef1; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-55b5802b273d56ed40f6f3f890e9e7f948f859c1e42897e2be4ee823516ba779; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-51f85123db48543345fbdac4843f2cc4d991172277b12aa8d709c144559d613c; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312

**Evidence.** docs/contracts/MH-C-LIVE-MCP-001.json=3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143; src/mathhead/server/live.py=983cd93b2917bb5b6b17828ce90dc735914583d24a339eb8c63e84772dd73168; tests/live_mcp/test_live_mcp_contract.py=d554bc42fd6a727aa7fb0e7650beb5928c0151aca9396dda2fd0eba44aebb44a; tests/test_mcp_live.py=2492cdeebedb9afb8e137b5017e464fb566728477f8ccab52e6781ddfacceea0; tools/validate_live_mcp.py=c827a339cddd88dd2d66d651a13a9cde590de532dc850de6339c0ece481775c9; docs/mcp-api.md=1516b078e7cac530dc805c36f94e8eaef3723f18647dbab21635a8d0196e938b

**Limitations.** Nine contract tests, Ruff, the dependency-free live-MCP validator, and all 13 status checks pass. The exact real MCP tests cannot pass on the only local CPython 3.14 interpreter and must be observed on the project-supported GitHub Python 3.10-3.12 matrix before DONE.

**Next.** Commit and push, require the new Windows/Linux/macOS jobs to execute rather than skip every live MCP assertion, and record MH-013 DONE only after those supported-platform logs are clean.

---

## 2026-08-11 - Command surfaces made encoding-safe

**Task.** MH-012 (`done`).

**Changed.** Bound every command-facing renderer to accepted MH-C-ENCODING-001; added deterministic safe_text and safe_print behavior, canonical ASCII-safe JSON, and non-UTF/redirected-stream coverage for CLI, discovery, MCP diagnostics, and developer commands.

**Learned.** GitHub run 31486792484 completed the encoding contract suite inside legacy-full on Windows 3.10, 3.11, and 3.12 and on Linux/macOS without an encoding failure; run 31486792597 independently passed the command-encoding status validator on Ubuntu and Windows.

**Contracts.** MH-C-ENCODING-001=b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210 (docs/contracts/MH-C-ENCODING-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-51aaf59a88555fc59f4afba8f2f0fa280feb423d15a7dedde5e973faa7f2321e; reconstruction-plan=passed/exit-0/output-3d49650537d551b9ee8a5c7d59991b71238d12aab5e316a78eac065a8452112f; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-5f31e7ee396f537eb635e742dd78f79bb851da09d4760ece7c998e8e40794dca; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-841cc3b0118eab212055b25ce1ba7ee1d684e67eb1f6108d735401ff6ebd585c; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-db72c3d44d0d9925a07e3f4ce554f231a8867c8ed3d6d0a955b547ad57f18e07; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7

**Evidence.** docs/contracts/MH-C-ENCODING-001.json=b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210; src/mathhead/output.py=c6d4dd4c2ffe276041cfacd69caa3fc76c495be1d2de4406def3327f7bce63f9; src/mathhead/cli.py=67c84affb6c5c8810f1d3ccac18233f3a8f77f93c0f5bc4f8163e06844fed07e; src/mathhead/discovery/cli.py=9e2b0bd008b885160f468bebd99c2341659546a8b46afb716fed20c1db6489ed; src/mathhead/server/mcp_server.py=593755c168b66fb3816a8a565a3ec05a5a6b8a927ccd2c79df27bce0126aa56a; tools/dev.py=0c532acff4c9567cfa5c1615171ca1be98531b2f06f2a49caf9ff05971c01d1d; tools/validate_command_encoding.py=847dc71453c55599c5eec70e3210d8350d591ff064346839c7e7d40f6b11dcec; tests/encoding/test_command_encoding.py=45422843d2619f2d1c56027603d564820a63ba13ccacd5858b2232530d3c3233

**Limitations.** The overall legacy-full jobs remain red for separately classified shallow-checkout baseline replay, Python 3.10 arbitrary-null parser hardening, and environment-sensitive discovery sample isolation; no observed failure is in the accepted encoding boundary.

**Next.** Complete MH-011 with the solver backend result, then activate MH-013 through MH-015 and isolate live-MCP, test-profile, and version/documentation drift.

---

## 2026-08-11 - Accepted encoding boundary implemented pending platform CI

**Task.** MH-012 (`partial`).

**Changed.** Accepted MH-C-ENCODING-001 byte-identically; added contract-bound safe_text and safe_print, routed main CLI, discovery CLI, MCP startup stderr, and the developer dispatcher through it, and made command JSON explicitly ASCII-safe.

**Learned.** cp1254 preserves Turkish and its representable punctuation exactly while arrows, mathematical minus signs, Greek letters, and emoji fall back to deterministic backslash escapes; replacing only unencodable code points keeps human output readable and JSON data-equivalent.

**Contracts.** MH-C-ENCODING-001=b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210 (docs/contracts/MH-C-ENCODING-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-82639b5edf9919d7aab91c4359ad17d328ffc0c0f23d8b74629b61db1e59dfe6; reconstruction-plan=passed/exit-0/output-3d49650537d551b9ee8a5c7d59991b71238d12aab5e316a78eac065a8452112f; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-d93d32daab77026629a1e41c2822e6ee96deaa59e11ee9efad696d0772c4c66f; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-841cc3b0118eab212055b25ce1ba7ee1d684e67eb1f6108d735401ff6ebd585c; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-db72c3d44d0d9925a07e3f4ce554f231a8867c8ed3d6d0a955b547ad57f18e07; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7

**Evidence.** docs/contracts/MH-C-ENCODING-001.json=b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210; src/mathhead/output.py=c6d4dd4c2ffe276041cfacd69caa3fc76c495be1d2de4406def3327f7bce63f9; src/mathhead/cli.py=67c84affb6c5c8810f1d3ccac18233f3a8f77f93c0f5bc4f8163e06844fed07e; src/mathhead/discovery/cli.py=9e2b0bd008b885160f468bebd99c2341659546a8b46afb716fed20c1db6489ed; src/mathhead/server/mcp_server.py=593755c168b66fb3816a8a565a3ec05a5a6b8a927ccd2c79df27bce0126aa56a; tools/dev.py=0c532acff4c9567cfa5c1615171ca1be98531b2f06f2a49caf9ff05971c01d1d; tools/validate_command_encoding.py=847dc71453c55599c5eec70e3210d8350d591ff064346839c7e7d40f6b11dcec; tests/encoding/test_command_encoding.py=45422843d2619f2d1c56027603d564820a63ba13ccacd5858b2232530d3c3233

**Limitations.** Twelve encoding contract tests, 229 focused CLI/MCP/dev tests, Ruff, and all 12 status checks pass. Live MCP subprocess tests are blocked only in this managed sandbox by the known pipe restriction assigned to MH-013; independent Windows/Linux CI has not yet been observed.

**Next.** Commit and push, require Windows and Linux command/JSON/MCP checks to cross the former locale boundary, then record MH-012 DONE without relabeling MH-013 pipe restrictions.

---

## 2026-08-11 - Accepted graph budget implemented pending independent CI

**Task.** MH-011 (`partial`).

**Changed.** Accepted MH-C-GRAPH-BUDGET-001 byte-identically; added the contract-bound GraphSearchPlan, pure 6/2000 and nauty 8/20000 limits, pre-enumeration refusal, bounded subprocesses, incremental order consumption, first-counterexample stopping, and graph/formalization regression tests.

**Learned.** The dependency-minimal full legacy run now completes instead of timing out: 2059 passed and 18 skipped in 340.35 seconds; its seven residual failures are two solver-capability selections, one managed multiprocessing socket restriction, and five live-MCP pipe restrictions, with no graph timeout.

**Contracts.** MH-C-GRAPH-BUDGET-001=3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794 (docs/contracts/MH-C-GRAPH-BUDGET-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-c2355937df92d84abea3111b963b41544accf92fb1bef8aed0d3d6ec57e5a974; reconstruction-plan=passed/exit-0/output-3d49650537d551b9ee8a5c7d59991b71238d12aab5e316a78eac065a8452112f; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-eda54bb6ba7902582146537aac304c6a27e72be608c77236f40e940d13a225fd; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-841cc3b0118eab212055b25ce1ba7ee1d684e67eb1f6108d735401ff6ebd585c; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-db72c3d44d0d9925a07e3f4ce554f231a8867c8ed3d6d0a955b547ad57f18e07; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7

**Evidence.** docs/contracts/MH-C-GRAPH-BUDGET-001.json=3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794; src/mathhead/discovery/product.py=d9098f1082af22f1d65e2e440aa2c815c3daad8003c4bcfad74f98532bfc911a; src/mathhead/discovery/formalize.py=033ae47cc116a83dc2baaf03090bf6b61947b5e5926e1da3422919758f0f4aac; src/mathhead/discovery/nauty_scale.py=988c6030ae525608bcff2388d6954d3e4194a1a8acacc548ea44e9e11abf6c3f; src/mathhead/discovery/cli.py=9e2b0bd008b885160f468bebd99c2341659546a8b46afb716fed20c1db6489ed; tools/validate_graph_budget.py=3d77f7f3333905c838630555415f3573246aeafc30139f7b0a27f3a3c03b9f7e; tests/graph_budget/test_graph_budget.py=3fbc911028bffe564805c87ace8a29cbeb26fda545537b44a10e1f0a49992ba5; docs/manual/api.md=27550b57916e879f4b888bd62b8afa841b578e912e34a9e3e646a4432400c81b

**Limitations.** Local graph contract, 11 negative/budget tests, 125 related legacy tests, Ruff, and all 12 status checks pass; independent Windows/Linux CI on the pushed implementation has not yet been observed.

**Next.** Commit and push the accepted implementation, then require GitHub core and solver jobs to cross the former graph timeout before recording MH-011 DONE.

---

## 2026-08-11 - Optional dependency test contracts corrected

**Task.** MH-010 (`done`).

**Changed.** Separated core and solver extras, added fail-closed capability markers and validation, accepted both nauty-geng and geng executable names, and placed the solver capability preflight before full coverage.

**Learned.** GitHub CI run 31484119142 solver job 93755486401 completed system nauty installation and solver bootstrap; the ordered 30-second capability preflight necessarily completed before the job continued into the long solver-full-coverage command. Core independently passes 314 tests without Python-SAT.

**Contracts.** MH-C-ENV-001=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87 (docs/contracts/MH-C-ENV-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-3aa8dda973dcde29856dbc5f96268a7b96b2aced758d5127514aa193aeba3a2d; reconstruction-plan=passed/exit-0/output-3d95cb5b504df6fad0bba4fe2ef2beea63a5748081806758f904cc980ea2a837; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-137ef8eb66ff29e4f0692377158e99052e6b7add2aab2f18763638b53ea3bbef; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-841cc3b0118eab212055b25ce1ba7ee1d684e67eb1f6108d735401ff6ebd585c; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-a2b56fcfbb06e2c76085ea5a82dd74bdaad1e231a37521584d1503c6a11ac84f

**Evidence.** tools/dev.py=70b03cb64b6aa9b9e3ab04bd37acfa95169cf5381bc3c6a7a92fd8969d8fbee8; tools/dev_profiles.json=ec0aa7b9dfc7bcf4d90d795699c148ce6adfa5e33ae144cfa37ab419c8274ae9; tools/validate_optional_dependencies.py=08d8295bb90cf14987a37284d88caad4dd0012a0edbaf75d1d5970df335f8c80; tests/devtool/test_optional_dependencies.py=1d1fe5ec5eeb23580ac1ba478c05399afc780450a5813f961c0cc637ad274d48; pyproject.toml=f1f7e1d795c3412f8e17fbf9b4a3d5ab7d4da0fdbed71d58c97a75b6a2456189; README.md=c6a527eb6641b3493304377200b9864826b8d43d378e0b2840179db0a8e2308e

**Limitations.** The same solver job remains inside the legacy full-coverage product command because unsafe graph enumeration is still open as MH-011; that product failure is not an optional-dependency selection failure.

**Next.** Obtain exact owner acceptance of the proposed MH-011 and MH-012 contracts, then implement their bounded graph and encoding-safe behavior.

---

## 2026-08-11 - Command encoding contract proposed

**Task.** MH-012 (`partial`).

**Changed.** Defined a content-addressed safe-text boundary for exact Unicode preservation, deterministic reversible escaping, ASCII-safe JSON, redirected streams, and stdout/stderr protocol separation without changing product output code.

**Learned.** The main CLI emits Unicode JSON with ensure_ascii disabled, the discovery CLI prints arrows and long dashes directly, and MCP startup diagnostics also contain an arrow; constrained Windows streams therefore need one shared non-global boundary.

**Contracts.** MH-C-ENCODING-001=b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210 (docs/contracts/proposed/MH-C-ENCODING-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-2fea89b346393f29f6a056b4bf80cd6e6f15122d52d1cda67d89e5eb22432e77; reconstruction-plan=passed/exit-0/output-3d95cb5b504df6fad0bba4fe2ef2beea63a5748081806758f904cc980ea2a837; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-47583c5aa2699a1cce44d8feaaa4b6017654a016303bb60a0790f2eb9ef973d8; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-841cc3b0118eab212055b25ce1ba7ee1d684e67eb1f6108d735401ff6ebd585c; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-a2b56fcfbb06e2c76085ea5a82dd74bdaad1e231a37521584d1503c6a11ac84f

**Evidence.** docs/contracts/proposed/MH-C-ENCODING-001.json=b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210; docs/contracts/manifest.toml=87e2ce953d42e1b5d45c271e15f3719b19ad175f537a61e1984ff2a9422e1ce3; docs/TODO.md=d78d82e535d20475bb6741c38dbc63d232daebf9461c929058d38c94751042ef

**Limitations.** Pre-screen and all status checks pass, but MH-C-ENCODING-001 is proposed rather than owner-accepted; no command output implementation is authorized to change.

**Next.** Obtain explicit owner acceptance at SHA-256 b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210 before implementing MH-012.

---

## 2026-08-11 - Graph budget contract proposed

**Task.** MH-011 (`partial`).

**Changed.** Defined a content-addressed graph search policy for pure and nauty backends, explicit generated-object limits, safe max_n=6 defaults, deterministic streaming, and honest refusal without touching product behavior.

**Learned.** The frozen failure is caused by the dependency-minimal max_n=7 path reaching pure-Python labeled graph generation and canonicalization; order 6 remains inside the observed test budget while larger orders require an explicit fast capability.

**Contracts.** MH-C-GRAPH-BUDGET-001=3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794 (docs/contracts/proposed/MH-C-GRAPH-BUDGET-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-43bc0e91f3c0cead9aa05179a06f8c5c3aef70132baa619e9de9f27d387bf8f6; reconstruction-plan=passed/exit-0/output-3d95cb5b504df6fad0bba4fe2ef2beea63a5748081806758f904cc980ea2a837; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-a48dd392b12d155fef87becce7f7a13acd654d1ad77299759ed25032122bec84; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-841cc3b0118eab212055b25ce1ba7ee1d684e67eb1f6108d735401ff6ebd585c; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-a2b56fcfbb06e2c76085ea5a82dd74bdaad1e231a37521584d1503c6a11ac84f

**Evidence.** docs/contracts/proposed/MH-C-GRAPH-BUDGET-001.json=3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794; docs/contracts/manifest.toml=87e2ce953d42e1b5d45c271e15f3719b19ad175f537a61e1984ff2a9422e1ce3; docs/TODO.md=d78d82e535d20475bb6741c38dbc63d232daebf9461c929058d38c94751042ef

**Limitations.** Pre-screen and all status checks pass, but MH-C-GRAPH-BUDGET-001 is proposed rather than owner-accepted; no graph product code is authorized to change.

**Next.** Obtain explicit owner acceptance at SHA-256 3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794 before implementing MH-011.

---

## 2026-08-11 - Optional dependency boundary fixed pending solver CI

**Task.** MH-010 (`partial`).

**Changed.** Added explicit core/solver dependency validation, a requires_solver test capability marker, fail-closed Python-SAT and nauty preflight, and portable nauty-geng-or-geng executable resolution under the accepted environment contract.

**Learned.** Ubuntu installs the nauty generator as nauty-geng while the previous dispatcher required only geng; core remains Python-SAT-free and now proves that boundary across 113 product modules and 10 marker contracts.

**Contracts.** MH-C-ENV-001=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87 (docs/contracts/MH-C-ENV-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-c4b78f92453a473ecbe5b88e4261c2ce8562c9cfe6d4a90ad375fee17baef074; reconstruction-plan=passed/exit-0/output-3d95cb5b504df6fad0bba4fe2ef2beea63a5748081806758f904cc980ea2a837; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-ff0ac8c1501466f6a1c6b4a1e6ef05382486bbe570b5d267bbf910e5dc5d13b8; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-c93c2c2c0c09e3fed366c80a9af7724993ad35dea57898f56755bc33acc5a946; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-a2b56fcfbb06e2c76085ea5a82dd74bdaad1e231a37521584d1503c6a11ac84f

**Evidence.** tools/dev.py=70b03cb64b6aa9b9e3ab04bd37acfa95169cf5381bc3c6a7a92fd8969d8fbee8; tools/dev_profiles.json=ec0aa7b9dfc7bcf4d90d795699c148ce6adfa5e33ae144cfa37ab419c8274ae9; tools/validate_optional_dependencies.py=08d8295bb90cf14987a37284d88caad4dd0012a0edbaf75d1d5970df335f8c80; tests/devtool/test_optional_dependencies.py=1d1fe5ec5eeb23580ac1ba478c05399afc780450a5813f961c0cc637ad274d48; pyproject.toml=f1f7e1d795c3412f8e17fbf9b4a3d5ab7d4da0fdbed71d58c97a75b6a2456189; README.md=c6a527eb6641b3493304377200b9864826b8d43d378e0b2840179db0a8e2308e

**Limitations.** Local core without python-sat passes 314 tests and all 10 status checks; the pushed Ubuntu solver bootstrap and capability preflight have not yet been observed.

**Next.** Commit and push MH-010, verify the Ubuntu solver job crosses bootstrap and preflight, then record DONE without conflating later product failures.

---

## 2026-08-11 - Immutable legacy baseline captured and replayed cross-platform

**Task.** MH-004 (`done`).

**Changed.** Bound the accepted MH-C-BASELINE-001 contract to a fail-closed CLI; froze canonical source, package, dispatcher, 379-file inventory, 1546-test collection, CI, benchmark, failure, platform, and hot-spot evidence; and added offline replay plus negative validation.

**Learned.** GitHub Project Status run 31483412187 replayed the exact artifact successfully on Ubuntu job 93753254827 and Windows job 93753254747; the separate product CI remains honestly red and is now a stable differential input for P1.

**Contracts.** MH-C-BASELINE-001=3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2 (docs/contracts/MH-C-BASELINE-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-bd34bb2fe0a3c260b26bc5a13a23d52e2a43c4cb426f6a16ec3052cc5b326ace; reconstruction-plan=passed/exit-0/output-f7eab44091d6f4b79273cfd70add6f5ed9b59084c2eb1c399b10b29b0843ad8e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-4fb9820a078e9340227e1a992fd47253b9bc874f4780d9846b76c460c44cbbbe; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-c93c2c2c0c09e3fed366c80a9af7724993ad35dea57898f56755bc33acc5a946; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2

**Evidence.** docs/contracts/MH-C-BASELINE-001.json=3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2; docs/reconstruction/legacy-baseline-v1.json=b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a; docs/reconstruction/legacy-observations-v1.json=69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903; tools/capture_legacy_baseline.py=0d20bff37ddd0f3f2d005419c144d5869d3bd7dee4cd6fa363a149336f221d3a; tools/validate_legacy_baseline.py=0717538244bfa4b9a3084c1fab1c37170fef4857360209853bf17f36dec7dea9; tests/baseline/test_capture_legacy_baseline.py=12731cb597c14171aec841465f14e39d056f78cd98f7c328085b9e5ec3322e67

**Limitations.** The artifact is an immutable oracle input, not a claim that the legacy product suite is green; graph enumeration, test reporting, and solver executable detection failures remain assigned to P1.

**Next.** Activate MH-010, MH-011, and MH-012 and restore the portable legacy product baseline without changing the frozen oracle.

---

## 2026-08-11 - Accepted baseline capture awaiting independent CI

**Task.** MH-004 (`partial`).

**Changed.** Accepted MH-C-BASELINE-001 and implemented canonical source capture, strict observation normalization, offline replay, frozen artifact validation, negative tests, and status-owned cross-platform CI execution.

**Learned.** The immutable pre-migration source has 379 tracked files and 1546 unique static test identities; environment and governance runs are green while legacy product evidence remains explicitly failed, timed_out, unsupported, and not_run where applicable.

**Contracts.** MH-C-BASELINE-001=3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2 (docs/contracts/MH-C-BASELINE-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-b7baf5627450d638c4462dabb5f0ffbf2f81d5fd0e880f3fb710d5f92fb4c1b0; reconstruction-plan=passed/exit-0/output-f7eab44091d6f4b79273cfd70add6f5ed9b59084c2eb1c399b10b29b0843ad8e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-f13850431fa7fb34c4b6aab3e3173c61b6e926ab71720b1f08bc1e0d54a1bfaa; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-c93c2c2c0c09e3fed366c80a9af7724993ad35dea57898f56755bc33acc5a946; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2

**Evidence.** docs/contracts/MH-C-BASELINE-001.json=3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2; docs/reconstruction/legacy-baseline-v1.json=b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a; docs/reconstruction/legacy-observations-v1.json=69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903; tools/capture_legacy_baseline.py=0d20bff37ddd0f3f2d005419c144d5869d3bd7dee4cd6fa363a149336f221d3a; tools/validate_legacy_baseline.py=0717538244bfa4b9a3084c1fab1c37170fef4857360209853bf17f36dec7dea9; tests/baseline/test_capture_legacy_baseline.py=12731cb597c14171aec841465f14e39d056f78cd98f7c328085b9e5ec3322e67

**Limitations.** Local schema, replay, negative, lint, and nine status checks pass; Ubuntu and Windows replay on the pushed commit is still pending, so MH-004 remains in TODO Now.

**Next.** Commit and push the baseline checkpoint, require the independent Project Status matrix to pass on Ubuntu and Windows, then record MH-004 DONE automatically.

---

## 2026-08-11 - Legacy baseline contract proposed

**Task.** MH-004 (`partial`).

**Changed.** Moved MH-004 into TODO Now and created the strict MH-C-BASELINE-001 proposal for canonical, fail-closed capture and offline replay of the pre-migration legacy source, package, tests, CI, benchmark, platform-failure, and hot-spot evidence.

**Learned.** The baseline is a persistent serialization and differential-oracle boundary, so MH-C-WORKFLOW-001 requires a content-addressed owner acceptance before capture tooling or the artifact itself may be implemented.

**Contracts.** MH-C-BASELINE-001=3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2 (docs/contracts/proposed/MH-C-BASELINE-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-43f225e0f334602c5bf03da44a30396264ec6cadbab19134c6a1a55c867d4698; reconstruction-plan=passed/exit-0/output-f7eab44091d6f4b79273cfd70add6f5ed9b59084c2eb1c399b10b29b0843ad8e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-cbac67ce69d4963cdf28df5eaa7d9214b50edb7ce3c7295a48492666b527d041; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-c93c2c2c0c09e3fed366c80a9af7724993ad35dea57898f56755bc33acc5a946; dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6

**Evidence.** docs/contracts/proposed/MH-C-BASELINE-001.json=3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2; docs/contracts/manifest.toml=7e24f94b614b5f510ed818bcd653af53df7433c8523cdb2fc9dcad2a07acb04a; docs/TODO.md=81f6de7d76944383737b09b22bb2a817d04ca029802c3fc28e62f02aa3824e70

**Limitations.** Pre-screen and all status validators pass, but the proposal is not accepted and therefore authorizes no MH-004 implementation.

**Next.** Obtain explicit project-owner acceptance of MH-C-BASELINE-001 at SHA-256 3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2, then implement capture, replay, schema validation, and the immutable artifact.

---

## 2026-08-11 - Reproducible environment contract completed

**Task.** MH-003 (`done`).

**Changed.** Completed the accepted environment boundary: one contract-bound dispatcher now owns status, runtime, core, solver, docs, and release profiles; local and CI install, check, build, and smoke behavior use the same pinned definitions on Windows and Linux.

**Learned.** Independent GitHub Actions run 31480711266 passed every environment job, including Ubuntu and Windows CPython 3.10 through 3.12, dependency-free status, clean runtime installs, and the clean release wheel smoke; governance run 31480711277 also passed on both operating systems.

**Contracts.** MH-C-ENV-001=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87 (docs/contracts/MH-C-ENV-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6

**Evidence.** docs/contracts/MH-C-ENV-001.json=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87; tools/dev.py=1daccf5b3a823924edcba392646f96930e3929b001300e0ff3df1bbe485d7efa; tools/dev_profiles.json=dc1cc8c8bcd4d2e3d9f2e30be7d48348f7874a8eaff3d1275908af4cf07bcd3d; tools/validate_dev_environment.py=ff224d991a8f6202641a7848fbde05bfb2a51f7f40cb82cbb3a6fbe0617f43d2; tests/devtool/test_dev.py=3f4f4f7b13d2c391d081226cd3476e5dfc94e9f49b584126c9ea8b2a61c68a07; constraints.txt=9460693124a486cca758ddaba84bf71956ca76e4c91d448b97a69a8c1055c29f; pyproject.toml=f79758b92e6ea7f8f08d69917f6be6582f446e1d8f1ff27a2a8756e9981efcdd; .github/workflows/environment-contract.yml=0134e18f06c23e11e2d4dea5c86d7b478422eff368572666c9272d4d3ba0c93f

**Limitations.** The environment contract is green; the intentionally separate legacy full-product graph-enumeration failures remain assigned to P1 tasks and are not represented as MH-003 success.

**Next.** Activate MH-004 and capture the immutable machine-readable legacy baseline before changing legacy algorithms.

---

## 2026-08-11 - Python 3.10 profile-policy test corrected

**Task.** MH-003 (`partial`).

**Changed.** Made the status-bootstrap no-install unit test independent of the executing interpreter by mocking only profile support; the production support policy remains unchanged and the test still proves pip is never invoked.

**Learned.** GitHub environment run 31480370760 passed Ubuntu 3.11/3.12, Windows 3.11/3.12, both dependency-free status jobs, and release smoke; Ubuntu and Windows 3.10 failed only because a status-profile test incorrectly assumed that status itself supports Python 3.10 while running inside the supported core 3.10 matrix.

**Contracts.** MH-C-ENV-001=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87 (docs/contracts/MH-C-ENV-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6

**Evidence.** tests/devtool/test_dev.py=3f4f4f7b13d2c391d081226cd3476e5dfc94e9f49b584126c9ea8b2a61c68a07; tools/dev_profiles.json=dc1cc8c8bcd4d2e3d9f2e30be7d48348f7874a8eaff3d1275908af4cf07bcd3d

**Limitations.** The focused fix passes locally; replacement Ubuntu and Windows Python 3.10 jobs are pending a new push.

**Next.** Commit and push the focused test-policy fix, require the replacement environment matrix to pass, then record MH-003 done.

---

## 2026-08-11 - Reproducible environment implemented locally

**Task.** MH-003 (`partial`).

**Changed.** Accepted MH-C-ENV-001 at the owner-approved hash; implemented the contract-bound dispatcher, six pinned profiles, Python 3.10 TOML compatibility, UTF-8 and bounded subprocess handling, clean runtime/release smokes, governed developer documentation, and dispatcher-owned CI workflows.

**Learned.** Python 3.14 exposed an unescaped argparse percent sign, and an unpinned build backend produced Core Metadata 2.5 that Twine 6.2 rejected; escaping the help literal and pinning Hatchling 1.32.0 with Twine 7.0.0 restored portable CLI and release validation without weakening gates.

**Contracts.** MH-C-ENV-001=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87 (docs/contracts/MH-C-ENV-001.json); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a3fb6217e4522c482532a0d520f4821cd78f528c4b27f83fa0fa4d9a656db5e6

**Evidence.** docs/contracts/MH-C-ENV-001.json=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87; tools/dev.py=1daccf5b3a823924edcba392646f96930e3929b001300e0ff3df1bbe485d7efa; tools/dev_profiles.json=dc1cc8c8bcd4d2e3d9f2e30be7d48348f7874a8eaff3d1275908af4cf07bcd3d; tools/validate_dev_environment.py=ff224d991a8f6202641a7848fbde05bfb2a51f7f40cb82cbb3a6fbe0617f43d2; tests/devtool/test_dev.py=8a4ddd708203cf4e3d7611d63110775bf0486e476dcf7faae90c8fa4b0bae4fa; constraints.txt=9460693124a486cca758ddaba84bf71956ca76e4c91d448b97a69a8c1055c29f; pyproject.toml=f79758b92e6ea7f8f08d69917f6be6582f446e1d8f1ff27a2a8756e9981efcdd; .github/workflows/environment-contract.yml=0134e18f06c23e11e2d4dea5c86d7b478422eff368572666c9272d4d3ba0c93f

**Limitations.** Local status, core, docs, runtime clean-smoke, and release clean-smoke validators pass on Linux CPython 3.14.3; independent Ubuntu and Windows matrix evidence for this commit is still pending.

**Next.** Commit and push the MH-003 checkpoint, require the draft PR environment workflow to pass on Ubuntu and Windows, then record MH-003 done and activate MH-004.

---

## 2026-08-11 - Reconstruction architecture decisions frozen

**Task.** MH-006 (`done`).

**Changed.** Accepted five reconstruction ADRs for boundary, package ownership, vertical-slice migration, compatibility, and trust language; added an immutable hash index, fail-closed validator, negative tests, and repository authority links.

**Learned.** Local validation passed 42 tests and 7 checks, exact Ruff 0.15.11 passed, and GitHub governance run 31477390994 passed on Ubuntu and Windows for commit c820346.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-a037876519b91c465b05085fa1e4cb090072290ce33c93d108f3d63e6956c595; reconstruction-plan=passed/exit-0/output-75c65a1fa12bc546468c81af15c4ac60bad8054087dd868b43d029b52846adc6; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-9ddf515e2c3f01528d8384aff65f23bf73af741a83b280407a3573e23f098ef5; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** docs/reconstruction/adrs/INDEX.toml=413fd65b396bacaa72b40778397721c2e2116230b8fdb3e3c1002f614a25fdc5; docs/reconstruction/adrs/README.md=e75635f7c7eef5fd09af111b2227a01d5a9f152705eac5892c852d94994c9b2c; tools/validate_reconstruction_adrs.py=f58e8bb797aefe71e8ad781dcb414c77508f4452f09baaecc3ca1d713eb4dc8a; tests/project_status/test_reconstruction_adrs.py=de7d08b1f3bb2a4ee2e9f82ae852cee4be00e6ed0b1a62ac63b5c93630c0b323; docs/reconstruction/README.md=895d209dbfa24c92768a8030bca1922bd9410d956a16e6fbbb62ac4da6a6760a

**Limitations.** The product CI baseline remains red in legacy discovery and reproducibility paths; environment contract MH-C-ENV-001 is still proposed, so dependency and product CI changes remain gated.

**Next.** Obtain explicit acceptance of MH-C-ENV-001, then execute MH-003 and capture the immutable machine-readable legacy baseline in MH-004.

---

## 2026-08-11 - PR lint gate restored

**Task.** MH-006 (`partial`).

**Changed.** Removed the stale unused os import reported by PR CI and completed the immutable reconstruction ADR index, validator, tests, and authority links.

**Learned.** PR CI run 31476398634 proved the governance control plane was green cross-platform while the product matrix stopped first at Ruff F401; exact Ruff 0.15.11 now passes locally.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-8f7694606fb0a253ccaef39850965c26b80a4ee994589293d387006b908522d3; reconstruction-plan=passed/exit-0/output-75c65a1fa12bc546468c81af15c4ac60bad8054087dd868b43d029b52846adc6; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-2dd76f884d4d894434a2ace72ff68529d3bdefebd6ae041df6d64e95315e9ba8; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** tests/project_status/test_project_status.py=f9aa34891acfd2c3f101c6b5705493d3f1a1acf6c68ffb7f6ab184f46fcee084; docs/reconstruction/adrs/INDEX.toml=413fd65b396bacaa72b40778397721c2e2116230b8fdb3e3c1002f614a25fdc5; tools/validate_reconstruction_adrs.py=f58e8bb797aefe71e8ad781dcb414c77508f4452f09baaecc3ca1d713eb4dc8a; tests/project_status/test_reconstruction_adrs.py=de7d08b1f3bb2a4ee2e9f82ae852cee4be00e6ed0b1a62ac63b5c93630c0b323

**Limitations.** Full product CI still has known legacy test and reproducibility failures; the proposed environment contract is not accepted, so no product dependency, profile, timeout, or CI-runtime changes were made.

**Next.** Commit and push the ADR freeze checkpoint, then require Ubuntu and Windows governance validation before closing MH-006.

---

## 2026-08-11 - Reconstruction ADR set frozen locally

**Task.** MH-006 (`partial`).

**Changed.** Accepted five immutable reconstruction ADRs for preserve/rebuild boundaries, target package ownership, verified vertical-slice migration, compatibility, and trust terminology; added a complete hash-stable machine index and negative validators.

**Learned.** The legacy decisions contain useful domain choices, but the reconstruction needs a separate authority that constrains ownership and epistemic claims without rewriting that history.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-71cdee1f7daa5f171e924cd84b599cc3f5c78857beed39c9c42b659f65dc5ceb; reconstruction-plan=passed/exit-0/output-75c65a1fa12bc546468c81af15c4ac60bad8054087dd868b43d029b52846adc6; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-4dbb2728ad122e52048dac11edf07b5bffb1f373b75b2d8a2c53a8305e3fc395; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; reconstruction-adrs=passed/exit-0/output-25c13053a243d31dcda50ce73cffacd0981d46eef52b3273cc3bf6c06ccee6dd; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** docs/reconstruction/adrs/INDEX.toml=413fd65b396bacaa72b40778397721c2e2116230b8fdb3e3c1002f614a25fdc5; docs/reconstruction/adrs/README.md=e75635f7c7eef5fd09af111b2227a01d5a9f152705eac5892c852d94994c9b2c; tools/validate_reconstruction_adrs.py=f58e8bb797aefe71e8ad781dcb414c77508f4452f09baaecc3ca1d713eb4dc8a; tests/project_status/test_reconstruction_adrs.py=de7d08b1f3bb2a4ee2e9f82ae852cee4be00e6ed0b1a62ac63b5c93630c0b323

**Limitations.** All 42 local status tests and 7 checks pass; independent Linux and Windows validation of the new ADR check is still pending.

**Next.** Commit and push the ADR checkpoint, then require cross-platform governance CI before recording MH-006 done.

---

## 2026-08-11 - Immutable legacy reconstruction index

**Task.** MH-005 (`done`).

**Changed.** Classified 14 root and discovery status/architecture records by authority, historical role, conflicts, and reconstruction phase while freezing each source path and SHA-256 without rewriting legacy content.

**Learned.** The legacy trackers contain valuable evidence but conflicting completion authority; the reconstruction index preserves them as searchable inputs rather than live project state.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-fda7348ea11a5a61672aa7491955acac4c72a1ccb5b9a0432a79c20e8be81beb; reconstruction-plan=passed/exit-0/output-11fd6818a1811a1f8b824a5b74248838d4d78d3fc3f38ebe777d9f55f2aed851; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-9e8ca261526bdf785b1d140f768b77054083ebb49068c084ccd6ff082b6ae61c; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** docs/reconstruction/LEGACY_INDEX.toml=dc624b79b9ed4adc63cd6b0a71cbe45423ebbc578673b748b5c612bea7b40a56; docs/reconstruction/README.md=77b4bd94adbf2dfc8c2973ccf2122b8bc11d69428c5090abdd7af768a2f4d67f; tools/validate_legacy_index.py=85035f5d414c9ba5ce4a3ea4c6cd3211e84b87d7ca9c9fa349e0c0f11ef11c44; tests/project_status/test_legacy_index.py=625b2b34adc4623b8efaf23eb9918a5321a9b0683a8654cb97e24a873a11b9cc

**Limitations.** The index classifies governance and architecture records; the full machine-readable source/test/benchmark baseline remains MH-004 after environment acceptance.

**Next.** Activate MH-006 ADR work while MH-003 waits for explicit environment-contract acceptance.

---

## 2026-08-11 - Repository-owned status automation

**Task.** MH-001 (`done`).

**Changed.** Installed and validated the vendored status CLI, black-box and integration tests, pre-commit hook, cross-platform governance workflow, exact-case configuration, init/adopt/upgrade paths, and idempotent adoption behavior without rewriting legacy trackers.

**Learned.** Dry-run adoption selects only docs/PLAN.md, docs/TODO.md, and docs/PROGRESS.md and proposes no changes after installation; GitHub run 31475928877 confirms Linux and Windows behavior.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-107f20936cdf5a505e184d25be8e1991d6bec71427e7af277f3f624109e98ccc; reconstruction-plan=passed/exit-0/output-fffc2b11c3663db55769ce20991c78c87848105d50c8f963fa40ea54a6b80f82; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-5874290e4e0dca19bae29244722c1a8ca31d07d993ade05416e4c45bbcf7cd07; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** tools/project_status.py=d9076683d2ec544a2438004cbbac42abbc91d76dabe74b21e81b39bdbca72787; tests/project_status/test_project_status.py=1eb12b373b272fed43239a79709ddd358a2e7d864378f5c2f1b8b302a0085a99; tests/project_status/test_status_integration.py=06b80bf9fc253d960a3bbf127f2e038b3c735699616e914d95f123b6d068f53a; .githooks/pre-commit=58868a286322182887fc0d72a405d5b5a0a7d7bc685ad9df08c7da8587341b78; .github/workflows/project-status.yml=1535aab4adad7e26b8b00623f317f079fe704aa3a2c28b016e2badcd1707659b

**Limitations.** Repository-local hook enforcement depends on core.hooksPath being enabled in each clone; CI provides the shared enforcement path.

**Next.** Finish immutable legacy indexing, then activate the next eligible P0 work.

---

## 2026-08-11 - Governed reconstruction baseline

**Task.** MH-000 (`done`).

**Changed.** Established the authoritative 93-task reconstruction plan, bounded live TODO, append-only PROGRESS ledger, frozen status and workflow contracts, exact-case repository configuration, and transactional status integration.

**Learned.** The governed baseline is reproducible and idempotent locally and in independent GitHub Actions run 31475928877 on Ubuntu and Windows.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-b3af949207831c0432e05883c196c07968318db1f59af57ced210b0573866dce; reconstruction-plan=passed/exit-0/output-cd01d12fc7d306b387d8b1c4f2208f55e31b1993927aa828d50f6c74464dc13d; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-d001c27b10264e368e6411e571e5fa629933864b910a8fd6a32978666eca9636; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** docs/PLAN.md=1835e86700fbc70de10f033c965fcffaba7420d85d52aa5eb13c5b061924d375; docs/TODO.md=fabd0cb801d70b201a7b0611a88a0fd7aa7be62085a2f8d6681aa636d267b9e7; docs/PROGRESS.md=b035d8cff28ba0c4c5c6b964f4349bd29987f43de727d859f9696c3402a11941; .project-status.toml=a86a8208a3e7847e149fa51091aa145a610e9e4ad33fe23c2c627755c30d34a1; docs/contracts/manifest.toml=5bdf4a74cc09af362d660c24aad37255257015ee85864612fc4234ce893b8e3a

**Limitations.** This baseline governs execution and evidence; it does not itself make legacy product tests green.

**Next.** Complete repository-owned adoption evidence and immutable legacy indexing.

---

## 2026-08-11 - Task-aware fail-closed transitions

**Task.** MH-002 (`done`).

**Changed.** Implemented Now-only atomic status transitions with accepted-contract verification, task-specific validator requirements, evidence hashing, timeout and missing/skipped/inconclusive rejection, append-only PROGRESS enforcement, cross-platform LF evidence, branch-creation baseline handling, and isolated CI validator contexts.

**Learned.** Independent GitHub Actions run 31475928877 passed on Ubuntu and Windows after earlier runs 31475257794 and 31475680721 exposed and bound the platform assumptions.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-c36d491e161254bb6b8ad76ffdcdfea0dfbb55a9f5c1f89d88cd462e0f2ea6a8; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-1e195daf25cbc843351b09b1c7ab97a2781bacd4022b3cb6f543fe4e07d45a65; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** tools/project_status.py=d9076683d2ec544a2438004cbbac42abbc91d76dabe74b21e81b39bdbca72787; tests/project_status/test_task_aware_status.py=09ef2203cb7aff56f7d2edfef3c69647d5237a53b5e1ee8bd29e66b441079f4a; .github/workflows/project-status.yml=1535aab4adad7e26b8b00623f317f079fe704aa3a2c28b016e2badcd1707659b; docs/contracts/manifest.toml=5bdf4a74cc09af362d660c24aad37255257015ee85864612fc4234ce893b8e3a

**Limitations.** This proves the governance/status control plane only; it does not claim product-health or environment-profile completion.

**Next.** Close the governed baseline, adoption, and legacy-index tasks, then proceed to the separately accepted environment contract.

---

## 2026-08-11 - CI validator environment isolation

**Task.** MH-002 (`partial`).

**Changed.** Removed inherited PROJECT_STATUS_BASE from temporary-repository test subprocesses, retained explicit baseline injection for dedicated cases, and upgraded governance workflow templates to the current Node 24 action majors.

**Learned.** GitHub Actions run 31475680721 proved that validators launched under the status check inherit its environment unless tests explicitly isolate repository-scoped variables.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-0819f0e628f2b84605b37dea008749c84515f36ba133d282009f4c036eaec752; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-cbb8c7f4d1a96b9b592b0e7a0786b33d17a65bd4285d6b8a274c37cefffa169f; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** tests/project_status/test_task_aware_status.py=09ef2203cb7aff56f7d2edfef3c69647d5237a53b5e1ee8bd29e66b441079f4a; .github/workflows/project-status.yml=1535aab4adad7e26b8b00623f317f079fe704aa3a2c28b016e2badcd1707659b; tools/project_status.py=d9076683d2ec544a2438004cbbac42abbc91d76dabe74b21e81b39bdbca72787

**Limitations.** The exact CI baseline scenario passes locally; a third independent Linux and Windows run remains required.

**Next.** Commit, push, and require run 3 to be green before recording MH-002 done.

---

## 2026-08-11 - Cross-platform CI failure closed locally

**Task.** MH-002 (`partial`).

**Changed.** Handled zero-SHA branch creation without weakening append-only history checks, enforced LF checkout bytes across platforms, propagated the policy through init/adopt templates, and added positive and negative regression tests.

**Learned.** GitHub Actions run 31475257794 exposed two independent assumptions: initial push before-SHA may be all zeroes, and Windows checkout conversion changes byte hashes unless EOL is repository-controlled.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-8694cf72c09ea4e7cd7b8d46a43a2257932454da26dff6d20aec24bb2efc1ac9; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-a92f5f35690de7aa3c463b6b3d3906ed60bdeb1770b25b5b5a649322e878432c; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** .gitattributes=ebae14b52c7a72ca06bd62baa0679741a94a6ffed051449e595f342b6f1d8ce7; tools/project_status.py=820c525205d756b20212c759f821ac5d1c18bdee35d48c9da65bb8390557d242; tests/project_status/test_task_aware_status.py=c576fba9f7e7f48d7bbf47ffc2b731bdbfbf6fb7ad93c77c442e5c5870b9cda4; tests/project_status/test_status_integration.py=e1750df3d908f52ef5e32fb656056ae6a72169623152b889f34814942a811860

**Limitations.** Local 38-test status suite is green; independent Linux and Windows rerun is still required before MH-002 can be done.

**Next.** Commit and push the CI hardening, then require both GitHub matrix jobs to pass.

---

## 2026-08-11 - Frozen Markdown whitespace policy

**Task.** MH-002 (`partial`).

**Changed.** Repository attributes now permit Markdown hard-break whitespace without changing accepted contract bytes; the reconstruction validator's real trailing EOF blank line was removed.

**Learned.** Generic Git whitespace checks must distinguish intentional Markdown rendering syntax from implementation whitespace defects.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-4fa74ddf0af2e40a56749e250d303c3014fcc83a45020cc235b3d301d7123abf; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-ffdc1c01c74a04b2d619aaa682176f284f22bba5d0b3ae83d2eba0958a68f725; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** .gitattributes=70d7a81fac55bd59d0864e6b144c73a706a63c4a8d0b740b94cbae97135fa988; docs/contracts/manifest.toml=5bdf4a74cc09af362d660c24aad37255257015ee85864612fc4234ce893b8e3a

**Limitations.** The exception applies only to Markdown files; non-Markdown whitespace remains strict.

**Next.** Restage, verify accepted hashes, and create the first governed checkpoint.

---

## 2026-08-11 - Branch CI trigger coverage

**Task.** MH-002 (`partial`).

**Changed.** Project-status governance workflow and embedded adoption template now run on pushes to every branch, enabling Linux and Windows validation before mainline integration.

**Learned.** A main-only push filter cannot validate the reconstruction branch before merge.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-4202767f38f77f3af2d795e4151278615956c4bd20533a34140f13b15a7e36cc; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-c828d0fb9f9eb82fd6fcbb56b82b56c99981e986c9b0e87efe2f40e73cfc1ea6; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** .github/workflows/project-status.yml=de3cc010b7df5642e5294a7aa041173617edd3cc9255877444472a40994aa824; tools/project_status.py=ebc3134b621e8fcb77f3fb0f1f6f0822602cc304939e09faab39f7374c38f0bc

**Limitations.** Product-health CI remains separate; this workflow proves only the governance/status control plane.

**Next.** Commit and push codex/reconstruction-plan, then observe both matrix jobs.

---

## 2026-08-11 - Contract manifest made an always-on status gate

**Task.** MH-002 (`partial`).

**Changed.** Added an always-on manifest validator that checks exact paths, SHA-256 identities, state-directory agreement, strict proposed-contract fields, TODO contract registration, and positive/negative fixtures; the status suite now runs 35 tests and six configured checks.

**Learned.** Contract hash enforcement only at record time leaves ordinary checks blind to intent drift; accepted and proposed artifacts must be verified on every status invocation.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-a6091b387561eec8fdad1120900483b41bb5c6e42de1ee855c907526f2b86675; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-32f101d69682e1d60745665da917f89572b327968035b6ea84aeae9e6841a347; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083; contract-manifest=passed/exit-0/output-70ee30d12006a0d9172abe4bb68e8de1e0a1b94ce9cc6b372bd6810e234cbb02

**Evidence.** tools/validate_contract_manifest.py=f463b743f60b3bd32c0307a611ccefe61dac961e850450a220247f3e3900e4c2; tests/project_status/test_contract_manifest.py=59ca970053a7be55458e92fefd7b422d7e0615a54132a20754e4196b0e4dfade; .project-status.toml=a86a8208a3e7847e149fa51091aa145a610e9e4ad33fe23c2c627755c30d34a1

**Limitations.** Local Linux evidence is green; remote Windows evidence and the user-approved environment contract remain outstanding.

**Next.** Use the authorized remote branch to execute cross-platform governance, then accept or revise MH-C-ENV-001 explicitly.

---

## 2026-08-11 - All declared validator outcomes fail closed

**Task.** MH-002 (`partial`).

**Changed.** Added deterministic missing-command and inconclusive classifications, tests for failed/skipped/missing/inconclusive/timed-out DONE rejection, positive committed-history prepend coverage, and proof that status transitions leave PLAN byte-identical.

**Learned.** Shell return codes alone are not cross-platform evidence for a missing command; Windows and POSIX diagnostic text must be normalized into the same logical missing result.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-c09bf4af6d9d509b6f1fda89cb9e03fa8ab2613c4da2549cc6f2ed4b2425aafc; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-66f3f08aab019516fe29d54a26d6454670b6b62189234105370aee2056033c12; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083

**Evidence.** tools/project_status.py=fd37d76ae267a5b550a96dad421593449fb98931792afe06c7370277c1a6f53f; tests/project_status/test_task_aware_status.py=232be17ab297dd204f8f2c36315cf9a3f6a3ebb6f05e4eb71296dec3e2e1b615

**Limitations.** Thirty-one local tests pass; real Windows runner execution and remote append-only comparison remain unverified until publication is authorized.

**Next.** Publish the branch after authorization, observe both governance jobs, and retain PARTIAL on any non-green result.

---

## 2026-08-11 - Status integration bypasses closed

**Task.** MH-002 (`partial`).

**Changed.** Aligned the vendored workflow template with the repository Windows/Linux matrix, made governance-only scope explicit, converted plan tests into discoverable unittest cases, and added executable hook bypass and workflow contract tests.

**Learned.** A test file existing under the status directory was not evidence that unittest executed it; discovery semantics and generated integration templates must themselves be tested.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-305015a4d56fdd326a65c8a555958e7d65ec7f2344a2fe42a4c209c55737a6fc; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-cf5eb21f639729496df0f22fe96278e7507a9fde8e11d0586af4a81c27000604; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083

**Evidence.** tools/project_status.py=f6ffe84d10830dc81d0ae6f38ca68507bcf3d65d48d0af7547de44833e6cf4fc; tests/project_status/test_status_integration.py=2d4b2543bea656c83d85240caec4c0193b928e9684c00b50df86b73ae3a2e0a4; .github/workflows/project-status.yml=f455dc848bc8b1d10c962438104b6209369540621d490e99d8305eae7b64a3bf

**Limitations.** Twenty-nine local status tests pass, but the Windows job remains unexecuted until the branch is published with permission.

**Next.** Run the unchanged suite in GitHub's Windows and Linux runners, then use record-done only if both are green.

---

## 2026-08-11 - Legacy authority index implemented

**Task.** MH-005 (`partial`).

**Changed.** Added a 14-record machine-readable legacy index, authority classifications, audited SHA-256 preservation fences, exact-case validation, and positive/negative structural tests without editing any indexed legacy source.

**Learned.** The root and discovery trackers mix valuable historical evidence with stale health and completion claims; only docs/PLAN.md, docs/TODO.md, and docs/PROGRESS.md can be current reconstruction authorities.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-509077af4031c320574a200e35b6e543ea3d32ceac2a64d91749a617835dd6f9; reconstruction-plan=passed/exit-0/output-e253c14ecac60a1b06293261654eafe7638b2845336bd5b9fb38ae6cae358c6e; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-5d2462a73067eca9b490da606691f5eee4a2c8d7ec0056110ec11430db0fd948; legacy-index=passed/exit-0/output-d5278694b6bdc968cb46849b59fda229c69ba51347373475ff44ec1514f9f083

**Evidence.** docs/reconstruction/LEGACY_INDEX.toml=dc624b79b9ed4adc63cd6b0a71cbe45423ebbc578673b748b5c612bea7b40a56; tools/validate_legacy_index.py=85035f5d414c9ba5ce4a3ea4c6cd3211e84b87d7ca9c9fa349e0c0f11ef11c44; tests/project_status/test_legacy_index.py=cf2b402b89db84efa2b6407d7a6eddc7d6f2ad48d0b32912a0ff309944301451

**Limitations.** Local validators pass, but record-done remains globally disabled until MH-002 has cross-platform evidence.

**Next.** After the status gate is accepted on Windows and Linux, record MH-005 done and start MH-006 reconstruction ADRs.

---

## 2026-08-11 - Portable environment contract proposed

**Task.** MH-003 (`partial`).

**Changed.** Proposed MH-C-ENV-001 with explicit status, runtime, core, solver, docs, and release profiles; deterministic dependency rules; platform refusal semantics; budgets; UTF-8 output; and a single repository-owned dispatcher boundary.

**Learned.** The current host has neither ruff nor pytest installed, while CI and documentation duplicate installation commands; profile semantics must be centralized before environment changes.

**Contracts.** MH-C-ENV-001=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87 (docs/contracts/proposed/MH-C-ENV-001.json)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-f42af0bfaba5f9bcaad97b1f23b28fb6b2e512299b976081d2b51bc4cf5de257; reconstruction-plan=passed/exit-0/output-48bf12bb8a910b9f5b472b7755111ac8b4c9d24cb3b344677739554eae9ef7c0; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-34aab2047be3e078dedc3ceaca24ec19687cb61240492f5521213ceb28f9835b

**Evidence.** docs/contracts/proposed/MH-C-ENV-001.json=63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87; pyproject.toml=40c27aeb289ac9e9a25b2b0fe94976ae0126cb0e415c6dc573f993cd866c443c; constraints.txt=fa62f96dc475fdbea0248d33849c61c04dcd76dee95bc82aa1d448e2d0c44e95

**Limitations.** The contract is proposed, not accepted. No environment, dependency, CI product command, or tools/dev.py implementation has been changed.

**Next.** Obtain explicit project-owner acceptance of MH-C-ENV-001 hash 63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87, then implement it without alteration.

---

## 2026-08-11 - Task-aware fail-closed transitions implemented locally

**Task.** MH-002 (`partial`).

**Changed.** Upgraded status automation to task-aware profiles and checks; bound transitions to accepted contract hashes and file evidence; added validator output digests, Now-only enforcement, timeout/skip/red rejection, exact-case paths, append-only Git history checks, and atomic rollback.

**Learned.** PARTIAL must collect and preserve red validator output without invoking the all-green completion path, while DONE must execute rather than trust claimed validator results.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-af3752122447cefd8945c1db14157cbce87298474bb9c09a7153e87362727861; reconstruction-plan=passed/exit-0/output-48bf12bb8a910b9f5b472b7755111ac8b4c9d24cb3b344677739554eae9ef7c0; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-2286933caf39d8a342b34b29dde641184789cf2f5e13cfedef9415dd2f496811

**Evidence.** tools/project_status.py=80ccd9de7ede9e890283bf356fa8b14f16d0e0ccc75cce2f4e3c310dc2394572; tests/project_status/test_task_aware_status.py=53092dbf81774eafdf8683ec9e468507769d8d5340b455753c2329e415bd8ae2; docs/contracts/manifest.toml=587cafba85c9a4078cfcb30bc6212fd91ddf3587b25576c95e05a5ef57a57080

**Limitations.** All Linux-local contract tests pass; the Windows CI job is defined but unexecuted, so the cross-platform acceptance criterion remains open.

**Next.** Establish MH-003's pinned environment and run the status suite on both supported operating systems before recording DONE.

---

## 2026-08-11 - Repository status automation adopted

**Task.** MH-001 (`partial`).

**Changed.** Installed the repository-owned project_status 2.0 CLI, 19-test status suite, reconstruction validator, exact-case configuration, executable pre-commit hook, Windows/Linux status workflow, accepted-contract manifest, and activated the local hooksPath.

**Learned.** A generic status tool was insufficient: task-specific checks, accepted contract hashes, evidence paths, validator output digests, queue enforcement, and append-only Git comparison are required to prevent false DONE records.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-482b6a1809b0028655a2979ec64a69b1d4264a0288a9075ebfa2ff62430c02cd; reconstruction-plan=passed/exit-0/output-48bf12bb8a910b9f5b472b7755111ac8b4c9d24cb3b344677739554eae9ef7c0; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-ee4c4df946ac9ff921885779bf7a528deb2f2117007f07d73625d98750d4a01d

**Evidence.** tools/project_status.py=80ccd9de7ede9e890283bf356fa8b14f16d0e0ccc75cce2f4e3c310dc2394572; tests/project_status/test_project_status.py=d7b9f42b700f546d8e97887567d664b7e51a417d504642887fa5349fdb08453c; .github/workflows/project-status.yml=4cb3682c3b2a3f97ef1b5ee253743590039707300b2bf2b664d9e8f87886916b

**Limitations.** The workflow definition is present but has not yet executed remotely; no commit or push has been made.

**Next.** Complete the MH-002 cross-platform gate, then move to the reproducible developer environment.

---

## 2026-08-11 - Governed reconstruction baseline restored

**Task.** MH-000 (`partial`).

**Changed.** Restored the complete 93-task P0-P12 programme, authoritative TODO and append-only PROGRESS records, frozen status and contract-first workflows, exact-case paths, and the audited 6927033 source baseline on codex/reconstruction-plan.

**Learned.** The prior Windows work was never committed and therefore did not survive the workspace move; the recovered patch also proved why path case and separators must be validated cross-platform.

**Contracts.** MH-C-STATUS-001=b4293b653ad3d30112ac284934b562091ba287b669f8a2b8d020d7a86edb0b2d (docs/contracts/PROJECT_STATUS_CONTRACT_V1.md); MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md)

**Validator profile.** status.

**Validators.** project-status-unit-tests=passed/exit-0/output-82b327abfb532817d274cb51c5c039b07dfe7aa89f83680abdc7f2950627b903; reconstruction-plan=passed/exit-0/output-48bf12bb8a910b9f5b472b7755111ac8b4c9d24cb3b344677739554eae9ef7c0; adoption-idempotence=passed/exit-0/output-b1438d61c0cb83f92cb3d7bcd6599896638a5e7292551d5570faaffae4196bdc; task-aware-status-contract=passed/exit-0/output-f1ac681aea062a686bb8d8515cc8e5e13d7e9ff0536467050a63c604aee9074a

**Evidence.** docs/PLAN.md=1835e86700fbc70de10f033c965fcffaba7420d85d52aa5eb13c5b061924d375; docs/TODO.md=0ce6b1c086c5ca48bbcd8452159e7a1e3b297bf7b7150741b1dd728ac82a1e4e; docs/contracts/manifest.toml=587cafba85c9a4078cfcb30bc6212fd91ddf3587b25576c95e05a5ef57a57080

**Limitations.** Linux status checks pass, but Windows CI has not run in this branch and the product environment is not yet reproducible.

**Next.** Finish MH-001 and MH-002 evidence, then implement MH-003 reproducible environments.

---

