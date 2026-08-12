# MathHead reconstruction progress

Append-only history for `MH-RECONSTRUCTION-V1`, newest first. Entries are added
only through the repository-owned status tool after adoption.

---

## 2026-08-12 - Deterministic alternative-reading analysis closed

**Task.** MH-041 (`done`).

**Changed.** Accepted and bound replay-complete MH-C-READING-ANALYSIS-002 after preserving v1 as immutable superseded history; implemented a dependency-minimal byte-oriented analyzer that revalidates accepted intake results, projects complete typed reading closures, independently derives exact structural deltas and choice state, enforces canonical identities and finite budgets, fails closed on false metadata or invalid/exhausted input, and added adversarial tests, an independent validator and frozen report, documentation, clean-wheel coverage, trust inventory updates, and exact-head cross-platform evidence.

**Learned.** A reading artifact is replayable only when it binds the complete accepted intake bytes and independently recomputes both projection closure and structural differences. Difference labels cannot carry authority: paths, fragments, affected entities, classifier rules, candidate topology, and choice state must all be derived and revalidated, while notation and parse changes require source-backed spans.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-PROBLEM-INTAKE-001=855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc (docs/contracts/MH-C-PROBLEM-INTAKE-001.json); MH-C-READING-ANALYSIS-002=0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70 (docs/contracts/MH-C-READING-ANALYSIS-002.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-54a614e9fbf19aee94a5922215e88f27df595194ab22e93dc4af2e9a9877f2e5; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-68a39a630ccd88d0924623d79b946cf11f1d30404f2f983b43e8c9d0968e4bdc; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-04f2cfa8131d656e6390569f598315bbb7751f17b5ae9b5fa4d92b4999e527e9; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-0fd2ab9f9f729e710f332aa836753f6c980b0740a132ddf650395a5d1ca709e6; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-02fdd81b8e5047206caa31e6caf7a66cb856023aa923cd606723015cf73262e3; trust-base-inventory=passed/exit-0/output-db1119b30dd1761c3eb8b44ab4638fdbf47eb107a60329b207fb93430d09e51f; proof-term-tests=passed/exit-0/output-657b02841d00755830116f9687287da37e549bd215291cfd15212b94a3a6a452; proof-term-contract=passed/exit-0/output-522c4468acc7b7e573a150b18f0509f5a0bce8dff4b1b7a48562669a5919c598; kernel-checker-tests=passed/exit-0/output-bbfaef4f0460cceb357b26f3765a143f0d742ae41f6ec06de1272ebe6b808e44; kernel-checker-validator=passed/exit-0/output-03f0dd57c8581539f7572fa371e04b54f24692c5c58c8eed16600a425fef91c4; kernel-checker-contract=passed/exit-0/output-a3c1c766d41b80b06e12d8723947085a3ae3263594de65b08f8e0d3c676a64c9; kernel-checker-v2-contract=passed/exit-0/output-c232e1fef9730f811c0e5471a72fb9f19d2fc4e3d854ace91ae9b3e3a8068841; sat-replay-tests=passed/exit-0/output-8ea4ec3eb2bfd4ccb12e903382c501d0d2bd1219aeddce9789745265b6b7f3c2; sat-replay-validator=passed/exit-0/output-c1baff3976224979af3b6a37bde3443caff210dbb247dea145116e55d6ece93f; sat-replay-contract=passed/exit-0/output-0946fa77006d4f69160e4714990d040c534706d026c15baef13b36f1a280b161; provenance-replay-tests=passed/exit-0/output-43365f348501c5f21d5588e7cdc3cabf254d3b5f0ea35d3f6ebfbafa88084828; provenance-replay-validator=passed/exit-0/output-4dfd49f520a72243ace5fdd8c538c4ee2c2ca03b61e58b7b004de69c7f3476c9; provenance-replay-contract=passed/exit-0/output-623a9ee3caea8bbeca35e31e0092217ec51863838543000af5639382e7efb8bd; lean-verification-tests=passed/exit-0/output-74d175ff6a4c0f32a759d99d3e21a434b7ae555f73e9f139eb7794fc57c7d2d8; lean-verification-validator=passed/exit-0/output-a2402006f15aae97c561c2a257025d1bcd6a99fda70b4519be750fe58e350058; lean-verification-contract=passed/exit-0/output-ae1aa5d10c3b950bc9b708ef7f79ed034a58b963ed643d1eea2048b7872137f4; lean-legacy-adapter-tests=passed/exit-0/output-0602abc7101da276f83e933dee8ec48f4d2b035b87cdd8051d23dfb2b6f63fb6; trust-transition-tests=passed/exit-0/output-14aa668f4824ef07108db167d7f85de7cac7fa54b69728fd335e670e32810fa8; trust-transition-validator=passed/exit-0/output-e3ffde0e4fa98219306ac8e9ae33367c3b0d64fb4fbad8d76102b33b36feb569; trust-transition-contract=passed/exit-0/output-8dcd593f2616d0886f5d90d508b011ca5d3c213036723a3632eac64f2da49415; problem-intake-tests=passed/exit-0/output-3d1f3207cb14afa600a6c3f794c49e47f76f12dccae581fdb4748ea1c6392c3a; problem-intake-validator=passed/exit-0/output-acc7a71a4fb1a751cb62d8de7c7d2a7040e283e483fc367275934b33a0c89e3c; problem-intake-contract=passed/exit-0/output-156fdd08b3facb48dbc337c19c28f4da7bf1852f3648e3e8ed6b071be414dfb9; problem-readings-tests=passed/exit-0/output-487805fc9686f340382549dfcad57b17c6aa1e608dbb403663258d231edab3e5; problem-readings-validator=passed/exit-0/output-2ca501055410cdb1f4aaeff763b5d399fe5ca15707ad64af675dd6f4f07dd27f; problem-readings-contract=passed/exit-0/output-60ee1ab9b5a4472bbef5aee6470fc334ae3902066bb69b6dc709730e1df3a0ea

**Evidence.** docs/contracts/MH-C-READING-ANALYSIS-002.json=0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70; docs/contracts/schemas/reading-projection-v2.schema.json=99ce60e50472e4c9d8026e9af361e4d7b11c776e577aa57de46794998fb26241; docs/contracts/schemas/problem-readings-result-v2.schema.json=b05b16d280260ac7854477274852f0273e0a6cb011d740ae827ca172dad72894; docs/contracts/reports/MH-C-READING-ANALYSIS-002.acceptance.json=84bc33049605d3ba29e8ec2cd3fa4a4933e45942bf2c4b01d8d75ec5f1399e8b; src/mathhead/problem_readings.py=d02d5d273d3dea21e4c94c74c37ea76f8668d0dd1cc373492b981b65858e7e94; tools/validate_problem_readings.py=03c8b7fe27ca705716579c7e01f7e72d70c2e6dec3f5c6f0047b2515fb954b1b; tests/problem_readings/test_problem_readings.py=99c2bee3dcfac6481a2785ac3f8d7261ec48337e50be0f81191f9a8f7eb9c26d; docs/readings/reports/problem-readings-v2.json=11a950c71acf506c287452ff63766e610d52f831ce4e002322ca205cf645e6f9; docs/PROBLEM_READINGS_V2.md=9acdc5c68b5e0b492e999e4fc73ca16579c40dc69c5849a91ec2c171c91c1d23; docs/trust/reports/trust-base-v1.json=a75cf1c718eaaeac87097f124bf2374ef897d6e1646392ae0012c19f2aeaffda; docs/trust/reports/trust-transition-g3-v1.json=b0d662c530477a423d76ff97f00f3fbdb69d06467da4f74a546d1f558897c6e6

**Limitations.** The boundary analyzes only readings already declared in accepted syntax-neutral intake bytes and intentionally performs no prose or LaTeX parsing, domain equivalence, assumption normalization, alpha-renaming, commutative normalization, solver or checker call, alternative synthesis, implicit selection, or mathematical-authority transition. Exact-head GitHub runs 31560089534, 31560089541, 31560089516, 31560087370, and 31560087324 all passed on commit f6f0dfdefacb44973d83f401e60df1eac6a8d2b4 across CI, coverage, solver, slow, clean-wheel, pinned Lean, governance, environment, Linux, macOS, and Windows matrices.

**Next.** Activate MH-042 and define the contract-first domain and assumption normalization boundary over accepted reading projections without erasing distinctions or claiming semantic equivalence beyond the contracted rules.

---

## 2026-08-12 - Syntax-neutral problem intake boundary closed

**Task.** MH-040 (`done`).

**Changed.** Accepted and bound MH-C-PROBLEM-INTAKE-001; implemented a dependency-minimal structured Python intake API that canonicalizes exact built-in declarations into independently valid ProblemIR bytes, returns immutable closed accepted/invalid/exhausted results, enforces complete structural, semantic, reference, scope, cycle, ambiguity, canonicalization, mutation, and resource checks, and added adversarial tests, an independent validator and frozen report, clean-wheel coverage, documentation, trust inventory updates, and exact-head cross-platform evidence.

**Learned.** A syntax-neutral intake boundary must reject more than unsupported syntax: it must own canonical copy semantics, semantic-order preservation, complete independent ProblemIR validation, validation-work ceilings, result anti-forgery, and canonical result revalidation. Treating representation validity as explicitly non-authoritative prevents a valid declaration from being mistaken for a proof or solver verdict.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-PROBLEM-IR-002=6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286 (docs/contracts/MH-C-PROBLEM-IR-002.json); MH-C-PROBLEM-INTAKE-001=855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc (docs/contracts/MH-C-PROBLEM-INTAKE-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-efe2dfd10b85ff362d296deeacc49616bc369d96a368b64b7fda5143b4928ea7; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-52a007613cc08091514eba27cbbf7d97d5ba675a97f04ac2b37abc2c718eb08f; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-32da53cd0a0c94f664139f6bb58d884252eb6d051f44508792aa8721b322b110; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-d257bd39227a739b8feb4492aceae8e8d94902058100bb97ab08745436622d43; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-5f77ee0148cb5e59b97a9b07dd30c3661c3c56311cef7f7239be31e573c936e2; trust-base-inventory=passed/exit-0/output-4c7c0dab2c2d90d374111fb2dbd2b636f5d710b0d9af93f8ca553974426c123c; proof-term-tests=passed/exit-0/output-c9edf7515b5e7444fa99276c954c8199db6c584ee520a22e6b0e087f77de7357; proof-term-contract=passed/exit-0/output-b1ee4e1dcdc7483f160f9c759afbde2900a494f8cae10108eb6aac1336369ca7; kernel-checker-tests=passed/exit-0/output-a368415910289a0bd7169921a5cfe5f1de30e6cf32750bacd36e1a4b94665863; kernel-checker-validator=passed/exit-0/output-03f0dd57c8581539f7572fa371e04b54f24692c5c58c8eed16600a425fef91c4; kernel-checker-contract=passed/exit-0/output-8b2cc41b20cfdeaa6d6d5b65921a4ed93a5e0f63bd32ffe50f2485f170f8cf17; kernel-checker-v2-contract=passed/exit-0/output-d56123d3fe96446f0216bcc6ee60b2567413fef9a54c1e82a44439ce13670e1a; sat-replay-tests=passed/exit-0/output-8ea4ec3eb2bfd4ccb12e903382c501d0d2bd1219aeddce9789745265b6b7f3c2; sat-replay-validator=passed/exit-0/output-c1baff3976224979af3b6a37bde3443caff210dbb247dea145116e55d6ece93f; sat-replay-contract=passed/exit-0/output-4971fce424f348eceffcfe135cdaed290dfb5d1ae5d3cf8fd4a9ceba31342c7c; provenance-replay-tests=passed/exit-0/output-b9dbc773fc989f44584ced6d33ec0090ec2e2206a9a45ae5bf263791efcbf718; provenance-replay-validator=passed/exit-0/output-4dfd49f520a72243ace5fdd8c538c4ee2c2ca03b61e58b7b004de69c7f3476c9; provenance-replay-contract=passed/exit-0/output-011dc28c1aaaf18b514e5f9bb096d8c4f15b2ad3eac8d746ab2ec72d103bdf3c; lean-verification-tests=passed/exit-0/output-74d175ff6a4c0f32a759d99d3e21a434b7ae555f73e9f139eb7794fc57c7d2d8; lean-verification-validator=passed/exit-0/output-a2402006f15aae97c561c2a257025d1bcd6a99fda70b4519be750fe58e350058; lean-verification-contract=passed/exit-0/output-42a2e2b29902b8e82c2652a63bb6f224fc66c971a99e62e7da64c4e4b8b1ccca; lean-legacy-adapter-tests=passed/exit-0/output-0602abc7101da276f83e933dee8ec48f4d2b035b87cdd8051d23dfb2b6f63fb6; trust-transition-tests=passed/exit-0/output-5efb20217643f02e32cd85579cabf677b536534c41b255651ce6183263c41b2a; trust-transition-validator=passed/exit-0/output-e3ffde0e4fa98219306ac8e9ae33367c3b0d64fb4fbad8d76102b33b36feb569; trust-transition-contract=passed/exit-0/output-a080f2091b8962e1f7a769ea427ee5ddd07be7c3a66adcf667be54e16c376c5e; problem-intake-tests=passed/exit-0/output-5b0ce0b622897cd7db80adef2f475df871467f699e68172dcd9a915da0300d85; problem-intake-validator=passed/exit-0/output-acc7a71a4fb1a751cb62d8de7c7d2a7040e283e483fc367275934b33a0c89e3c; problem-intake-contract=passed/exit-0/output-41410727281a876ff5900dacdf163dfe6cec628967fe39b80cec493493b8b0f1

**Evidence.** docs/contracts/MH-C-PROBLEM-INTAKE-001.json=855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc; docs/contracts/schemas/problem-intake-v1.schema.json=e109d5a664849b8122eed13eeb87d73bc47e2d2989b3298e06a697989fb51c04; docs/contracts/schemas/problem-intake-result-v1.schema.json=0ea174a09391dd7f690bba9df7dfd08d8f1253032c472ca60d45eaf9f47101d3; docs/contracts/reports/MH-C-PROBLEM-INTAKE-001.acceptance.json=e2992a0c901109b1a3e23496a72179d7dea16283e75608c71f1357bdd35d34de; src/mathhead/problem_intake.py=73badb23a9dbb65fefa95c80128f9403fa4abd69a3ebe2c9046c7799b1f5d9c5; tools/validate_problem_intake.py=a5b9123a71451a088559bffb2a8c4c798f94a0084b6e9ccfddb885cf14b8d82f; tests/problem_intake/test_problem_intake.py=ce7f9434e40981543ee3f80620bea27ccabee10e9aaf61a7b9fda287077312c4; docs/intake/reports/problem-intake-v1.json=5aea9aeb9a460d00f367d6b02ab699cd22c5f8514fc9497a71f8a3cc60a3c90f; docs/PROBLEM_INTAKE_V1.md=4b23fff79437188b0d3b9263ee2778d4f88f93f73d174c4b57ffdc45f9130d42; docs/trust/reports/trust-base-v1.json=8e4604c36fb17c854cdc35d8c3d25e904676c10e02afa16ed5646174454985f0; docs/trust/reports/trust-transition-g3-v1.json=e2e4db6ab285759244a29d5c306064d76848f2b5ed3526f127552860317aba4b

**Limitations.** The boundary accepts explicit structured declarations only and intentionally does not parse prose, LaTeX, MathML, Python expressions, SymPy, CLI, MCP, files, or network input; it does not infer domains or assumptions, normalize semantics, generate or select alternative readings, solve goals, or grant mathematical authority. Exact-head GitHub runs 31556884557, 31556884558, 31556884591, 31556882783, and 31556882785 all passed on commit 113a98caa0200699401b1e1adc88949f6bae44a9, including coverage, solver, slow, clean-wheel, pinned Lean, governance, environment, and Linux, macOS, and Windows matrices.

**Next.** Activate MH-041 and implement contract-first stable alternative-reading analysis over accepted intake results, with explicit machine-readable differences and required user choices but no silent inference or selection.

---

## 2026-08-12 - Trust-tier transition red team closes P3 G3

**Task.** MH-037 (`done`).

**Changed.** Accepted and bound MH-C-TRUST-TRANSITION-001; implemented a dependency-minimal pure transition auditor, canonical catalogue and G3 report, exact authority-issuer and effect-surface inventory, 11 permitted-edge positive controls, 45 normative mutants with a 100-percent kill rate, strict catalogue identity binding, bounded malformed-input handling, hardened report writes, and complete local plus exact-head remote validation.

**Learned.** A transition auditor is not independent if callers can substitute its allowlist catalogue; the production boundary must bind the exact reviewed catalogue identity. Size and nesting budgets must also be enforced before expensive hashing or recursive validation, and every high-tier issuer must be enumerated alongside every effect surface that could otherwise smuggle authority.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json); MH-C-PROOF-TERM-001=20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac (docs/contracts/MH-C-PROOF-TERM-001.json); MH-C-KERNEL-CHECKER-002=1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e (docs/contracts/MH-C-KERNEL-CHECKER-002.json); MH-C-SAT-REPLAY-001=0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50 (docs/contracts/MH-C-SAT-REPLAY-001.json); MH-C-PROVENANCE-REPLAY-001=31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67 (docs/contracts/MH-C-PROVENANCE-REPLAY-001.json); MH-C-LEAN-VERIFICATION-001=b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a (docs/contracts/MH-C-LEAN-VERIFICATION-001.json); MH-C-TRUST-TRANSITION-001=7b32e2db85c8aa8c98b9a9c5404d562a909f9ae2435310a79dad04b6c6ed4796 (docs/contracts/MH-C-TRUST-TRANSITION-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-d8ffb8b25db1fed9b38543e318267de4d50ae47b0c905c6df677acf71eab262a; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-fd97dee66cc70b2db1b5ebafd756d5b4f49fed00797f16f620c7a2d731c33efa; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-f8d986de607423398fbce33bc4976a49825378e804cb71197ca0e81d6b5fbc5f; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-d52c4d6935b0343bf9c9a0f76b85c476a555dce37041d2ed06800f4930b4a9d3; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-0ec32b9dc09f134c3c4134c53d71bddb823b124548c6eff759ab9bd05052e12c; trust-base-inventory=passed/exit-0/output-2622794552b6531914d59e3f06638d153ac71d07142fc72a203c7491f8e84bed; proof-term-tests=passed/exit-0/output-657b02841d00755830116f9687287da37e549bd215291cfd15212b94a3a6a452; proof-term-contract=passed/exit-0/output-4c2eaff66c75a33bc268199b6926da6e6c46c3f1243a0272349624280ece3ecf; kernel-checker-tests=passed/exit-0/output-a368415910289a0bd7169921a5cfe5f1de30e6cf32750bacd36e1a4b94665863; kernel-checker-validator=passed/exit-0/output-03f0dd57c8581539f7572fa371e04b54f24692c5c58c8eed16600a425fef91c4; kernel-checker-contract=passed/exit-0/output-df930e222935d8d0fe0b7b3f58e40b413a32b42bd4ecdb00125ae2c70d9b92bd; kernel-checker-v2-contract=passed/exit-0/output-7e012bf9d7481f47604aac585c897d8da981fd2c711996cad213adefb5e640bc; sat-replay-tests=passed/exit-0/output-dcd79764e17d98d675d94b6580847be56bd2f0881b854c36d20714ff44c85e9d; sat-replay-validator=passed/exit-0/output-c1baff3976224979af3b6a37bde3443caff210dbb247dea145116e55d6ece93f; sat-replay-contract=passed/exit-0/output-ffe88ea8cb0a94ccfa9f6660471288a466c686ce5bf3a4b0f450524ede9a1a7e; provenance-replay-tests=passed/exit-0/output-b9dbc773fc989f44584ced6d33ec0090ec2e2206a9a45ae5bf263791efcbf718; provenance-replay-validator=passed/exit-0/output-4dfd49f520a72243ace5fdd8c538c4ee2c2ca03b61e58b7b004de69c7f3476c9; provenance-replay-contract=passed/exit-0/output-87c5314a43b7bfea33f67efecb5735869087922cd3ebd043f05d8be1c47a7242; lean-verification-tests=passed/exit-0/output-74d175ff6a4c0f32a759d99d3e21a434b7ae555f73e9f139eb7794fc57c7d2d8; lean-verification-validator=passed/exit-0/output-a2402006f15aae97c561c2a257025d1bcd6a99fda70b4519be750fe58e350058; lean-verification-contract=passed/exit-0/output-5a83b9357d6d5269cc14d5bf1d1a48b4fd809ad74be6aad0422e3ae39ea156ca; lean-legacy-adapter-tests=passed/exit-0/output-0602abc7101da276f83e933dee8ec48f4d2b035b87cdd8051d23dfb2b6f63fb6; trust-transition-tests=passed/exit-0/output-57ff934299dcb1bcce0fb710e69d82239d76559ec2092db00f3879caaf6a303c; trust-transition-validator=passed/exit-0/output-e3ffde0e4fa98219306ac8e9ae33367c3b0d64fb4fbad8d76102b33b36feb569; trust-transition-contract=passed/exit-0/output-1518815b37b5d210bee6b7efcf950a72212a09c967197fe1fe4082224f171334

**Evidence.** docs/contracts/MH-C-TRUST-TRANSITION-001.json=7b32e2db85c8aa8c98b9a9c5404d562a909f9ae2435310a79dad04b6c6ed4796; docs/contracts/schemas/trust-transition-attempt-v1.schema.json=570ff6ed9905b9b3c39b45f51693e3f2b157d3f9ce93a12ce7a4cc3a8e4ca29a; docs/contracts/schemas/trust-transition-audit-result-v1.schema.json=8b8b48110d7a2c429b18eec52427e9878bd7c8dde05fb8c9b29dac1a061b89bf; docs/contracts/schemas/trust-transition-catalogue-v1.schema.json=205dfc544f130203ef092dbda050c763b93cbd92b9d2d4606fe95516843f2e1e; docs/contracts/schemas/trust-transition-report-v1.schema.json=e043d8f6c3425f9806512ced28daaa3a66da080388c0e6a37e6f649eaf74d2f3; docs/contracts/reports/MH-C-TRUST-TRANSITION-001.acceptance.json=9047a5076b9a048f6c60826a073240630b620d48e4543367c990994ba76632da; src/mathhead/kernel/trust_transitions.py=74b54f54109cb8b837d368c92e777371aa6b4c8c218ef983ffb95586aadd9ea2; tools/validate_trust_transitions.py=ac3e342a2c0ca5ef2c8643df10cad4be95dd8107d69a1f8e2c9548b0861dfb63; tests/trust_transitions/test_trust_transitions.py=2f02942c62c932caf17845116fc45a309fd91f739d606190e594fe902407e0d3; docs/trust/trust-transition-catalogue-v1.json=1a26d41f546f4a9334442fc7ef7d83eccffef56ed1f7a46d4209c748fb1c4b93; docs/trust/reports/trust-transition-g3-v1.json=abcd3787944767038c0d975d40eb07a4ae80c7f48898a92fdd2ef75a7b59aeb5; docs/TRUST_TRANSITIONS_V1.md=1da1d833b5c7f8db28b0ec7e272136862da2166408cc5356a9fb79a3927f1eca; docs/trust/trust-base-v1.json=503df6156f520c099ec1bd3d2a7e59193174cc9683d2b7fcbd5ffcd4ce21f737; docs/trust/reports/trust-base-v1.json=6be090fbb1a176b2cbc5a83af7865782aa91b0f40c5fe4a03419e96bd7aaadb7

**Limitations.** G3 is closed only for the explicitly supported kernel fragment and its 11 current permitted transitions; the catalogue intentionally grants no present solver_verdict issuer and keeps SymPy, Z3, approximate, discovery, CLI, MCP, process, filesystem, clock, randomness, and dynamic-import surfaces non-authoritative. The local Python 3.14 interpreter cannot own the policy-supported solver and slow profiles, but exact-head GitHub runs 31553898168, 31553898208, 31553898206, 31553895879, and 31553895936 all passed on commit 74d72c1dd532f09da259548c033f14b639ba5db1, including coverage, solver, slow, clean-wheel, pinned Lean, governance, environment, and complete Linux, macOS, and Windows matrices.

**Next.** Activate MH-040 and define the contract-first syntax-neutral structured Python intake boundary, keeping natural-language and LaTeX adapters outside the trusted parser.

---

## 2026-08-12 - Pinned Lean verification loop closed

**Task.** MH-036 (`done`).

**Changed.** Accepted and bound MH-C-LEAN-VERIFICATION-001, then replaced the written-only legacy exporter with a dependency-minimal, canonical, non-authoritative Lean request boundary and a closed result algebra whose sole authoritative success state requires fresh execution by the exact pinned Lean 4.33.0 toolchain. Added content-addressed source, project, toolchain, observation, and result artifacts; fresh MH-035 provenance replay; bounded shell-free execution in a link- and mutation-resistant workspace; exact release and dependency locks; four live arithmetic proof rules; a hardened legacy adapter; clean-wheel smoke coverage; adversarial unit tests; documentation; trust-base ownership; and an exact-head GitHub CI job that acquires and independently verifies Lean and mathlib.

**Learned.** External proof authority depends on more than successful process exit: source bytes, project bytes, executable identities, dependency commits, environment isolation, pre-run provenance, post-run immutability, bounded observations, and result freshness must all agree. The clean GitHub run proved the committed acquisition manifests can reconstruct the pinned environment independently, while exporter-only and stale or malformed observations remain deterministically non-authoritative.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json); MH-C-PROOF-TERM-001=20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac (docs/contracts/MH-C-PROOF-TERM-001.json); MH-C-KERNEL-CHECKER-002=1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e (docs/contracts/MH-C-KERNEL-CHECKER-002.json); MH-C-PROVENANCE-REPLAY-001=31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67 (docs/contracts/MH-C-PROVENANCE-REPLAY-001.json); MH-C-LEAN-VERIFICATION-001=b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a (docs/contracts/MH-C-LEAN-VERIFICATION-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-c2e9cc8e92304cd875a8b17838ab0b12222ec2f75f6c998ab2186e908bacf320; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-77949efa0e219ce406d3900f405918eaa9547ce32f19cc411d48c80ed3da4331; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-423053ef77c3e77840eab130ad6f7d9a665678a1d68170c8d7c5fdc227b60eae; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-d7f39d837ffb3de0ad5b4946d1e3c584765556b1743630ee43edf793f3c04ef0; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-cb773b4039135f2cb33e733c4ad42e8b8b839ab7bf3b0182a277fcd1baeb5858; trust-base-inventory=passed/exit-0/output-cc25ddc56e92519e190c8e63989e10fbcb01f25df6a3bdc47ea4bf0ad73692fc; proof-term-tests=passed/exit-0/output-657b02841d00755830116f9687287da37e549bd215291cfd15212b94a3a6a452; proof-term-contract=passed/exit-0/output-1d62458e4f5fb01f07abcf06a401e1c7e1e014636e248d44a3b4851b125c5efe; kernel-checker-tests=passed/exit-0/output-a368415910289a0bd7169921a5cfe5f1de30e6cf32750bacd36e1a4b94665863; kernel-checker-validator=passed/exit-0/output-03f0dd57c8581539f7572fa371e04b54f24692c5c58c8eed16600a425fef91c4; kernel-checker-contract=passed/exit-0/output-4d2c7efb4d22c28dcf49484dc5188331c2a281fa57675706a1754677698509a0; kernel-checker-v2-contract=passed/exit-0/output-8fffd0af23f2b393129df6fe448734fe6fc3ff1ab565ed1b9791c38568daba28; sat-replay-tests=passed/exit-0/output-8ea4ec3eb2bfd4ccb12e903382c501d0d2bd1219aeddce9789745265b6b7f3c2; sat-replay-validator=passed/exit-0/output-c1baff3976224979af3b6a37bde3443caff210dbb247dea145116e55d6ece93f; sat-replay-contract=passed/exit-0/output-e3490ddcbd9e66d5854c30ea277838ab9e004ad4266b877e5eb8edd719b6194d; provenance-replay-tests=passed/exit-0/output-66bdd2d5b92a99deac38ba9b2601724a3d62f48661cfdb4d7fbc57955a841070; provenance-replay-validator=passed/exit-0/output-4dfd49f520a72243ace5fdd8c538c4ee2c2ca03b61e58b7b004de69c7f3476c9; provenance-replay-contract=passed/exit-0/output-fa590852a8034c1895fbc335a10170637f08ff8a0ba5b7aa981403d8be6554a4; lean-verification-tests=passed/exit-0/output-1da354f564ee02b52ccd7cecbb5295ad315a15d4ea46091c2ad3bccc0168e4cd; lean-verification-validator=passed/exit-0/output-a2402006f15aae97c561c2a257025d1bcd6a99fda70b4519be750fe58e350058; lean-verification-contract=passed/exit-0/output-1f419d01f2db2f93d2ed02706b4f41e5734f807515715d7129a6f33194d1d49d; lean-legacy-adapter-tests=passed/exit-0/output-0602abc7101da276f83e933dee8ec48f4d2b035b87cdd8051d23dfb2b6f63fb6

**Evidence.** docs/contracts/MH-C-LEAN-VERIFICATION-001.json=b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a; docs/contracts/schemas/lean-verification-request-v1.schema.json=696962e42cd29d08a7b38e6e0c8728244c4a3a58ef39a7cc2effe47f8a6ce58d; docs/contracts/schemas/lean-verification-result-v1.schema.json=109e7e71b71ccce3daea88ea0cfb9f4b112fb1eeecf49a732705892f1bfa9965; docs/contracts/reports/MH-C-LEAN-VERIFICATION-001.acceptance.json=2c023d142a6007dd3fc6e5f034b0f7c49777af58fc9ec2471224ec155e6bd7a5; src/mathhead/proof_assistant/export.py=fd8a98554c7895247c599a920eead11c6326acc79673d2ac55a3977c8d1c2009; src/mathhead/proof_assistant/lean.py=18c2d73de9669a986e0f7c18600924471e8f74b12f9c305f86b5ad7ddb0aa58c; src/mathhead/proof_assistant/provenance.py=4036f0a2802bc38c28b652d303809d07e1de9560205d088b770869f8e5a93971; tools/validate_lean_verification.py=f6636f490dd0b838500ea1cf7da77448ba535003f15c3a79f79e6c8f29220bff; tests/lean_verification/test_lean_verification.py=6975a8f5c0505a656847a59461dacf3933469e6a291361abd1c8ae3c622635f2; lean/mathhead-lean-lock.json=2dfb5da13edd080f31662bb636b47a25f2b0e5ec2a6faf5ece3548e38b8917c4

**Limitations.** Authority is intentionally limited to the four contracted arithmetic export rules and only to fresh exact-toolchain successes; arbitrary Lean source, written-only exports, unsupported rules, stale observations, and mismatched provenance remain non-authoritative. The local Python 3.14 interpreter cannot own the policy-supported solver and slow profiles, but exact-head GitHub runs 31550797201, 31550797191, 31550797236, 31550793849, and 31550793793 all passed on commit 5966a0c333444c8d09617dbe4c93c113940bc927, including the pinned Lean job, coverage, solver, slow, clean-wheel, governance, environment, and complete Linux, macOS, and Windows matrices.

**Next.** Activate MH-037 and systematically mutation-test, forge, truncate, corrupt, swap, and cross-wire every trust-tier transition from proof terms and arithmetic evidence through SAT replay, provenance, and the new Lean authority boundary.

---

## 2026-08-12 - Content-addressed provenance replay made authoritative

**Task.** MH-035 (`done`).

**Changed.** Accepted and bound MH-C-PROVENANCE-REPLAY-001; added a dependency-minimal pure verifier for closed canonical run manifests and exact content-addressed objects; bound complete ProblemIR, context, plugin, budget, evidence, certificate, checker, contract, implementation, configuration, source, and result identities; replayed allowlisted proof and SAT checkers from fresh bytes; added immutable deterministic results and finite budgets; built an atomic fan-out filesystem adapter that rejects traversal, links, writable or mutated objects, collisions, partial commits, and filename trust; retired the legacy truncated proof hash as authority while preserving an explicitly non-authoritative compatibility field; and validated clean-wheel and cross-platform behavior.

**Learned.** Filesystem safety must distinguish a symlink at the declared store root from harmless platform-level symlink ancestors: Windows runners also expose short-name aliases, while macOS maps /var through /private/var. Canonicalizing only ancestors, then lstat-validating the final root and every content-addressed component, preserves the fail-closed boundary across all three platforms. Atomic read-only installation on Windows also requires unlinking the temporary name before chmod while readers reject writable or multi-link transient states.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json); MH-C-PROVENANCE-REPLAY-001=31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67 (docs/contracts/MH-C-PROVENANCE-REPLAY-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-b41964b45162e7760031813405d457a83a2c20a94f4c118dada96d21ef354b1a; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-96153ef6feeccce7113cd1e64508ca75b6062951063c4ff9db3e6f4c8a1803ab; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-a42cb652e09442ee5dfdcec34cda3b9e0ba468f31fcd87db56e2afa9baeff7d9; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-c79604dbaacb2fad2d00023bafed7fc39196251f547f28f0ae315de857a67a8a; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-4fc2a771d9afb3803a6118431992b091031a0695941453bd1c4104ffe5143c96; trust-base-inventory=passed/exit-0/output-2b351cc9bb376db294a1790b573f3999d99771e3a8e2857c3eb5a34966be7c5e; proof-term-tests=passed/exit-0/output-758fbf2e1d42a9716182ae5e8eb948e180ba4282e253014eb7a629131501b08e; proof-term-contract=passed/exit-0/output-71ed32bf08a20873611860ff633a55a706c53a7e4fd13ded85066d74e0e97c62; kernel-checker-tests=passed/exit-0/output-e6bd3354b05b292a2132a310e230c04bade6f821c370ee7eababe552a2c33255; kernel-checker-validator=passed/exit-0/output-03f0dd57c8581539f7572fa371e04b54f24692c5c58c8eed16600a425fef91c4; kernel-checker-contract=passed/exit-0/output-02da0ee908c824507b71c56c8beb4b7cc1b6138f97a484e6b9890508eeaf610a; kernel-checker-v2-contract=passed/exit-0/output-ee627567064e748a206c98d3dd3b652cb8c4d555755602b0ff46e933b74dbb11; sat-replay-tests=passed/exit-0/output-8ea4ec3eb2bfd4ccb12e903382c501d0d2bd1219aeddce9789745265b6b7f3c2; sat-replay-validator=passed/exit-0/output-c1baff3976224979af3b6a37bde3443caff210dbb247dea145116e55d6ece93f; sat-replay-contract=passed/exit-0/output-9c93905b68195ef1f7e53fa39e17eb60f2119edab3ed7dcc0e1b83746fce2824; provenance-replay-tests=passed/exit-0/output-06bfd12a5bdccba18a8af1ff43a30a5cd8d48380e79e6e9d05e3a3dec4c1e077; provenance-replay-validator=passed/exit-0/output-4dfd49f520a72243ace5fdd8c538c4ee2c2ca03b61e58b7b004de69c7f3476c9; provenance-replay-contract=passed/exit-0/output-09f353480d9b7dc4e3de1bfe186f114bda1f9bd20c91b4ece48ba8903aad46d0

**Evidence.** docs/contracts/MH-C-PROVENANCE-REPLAY-001.json=31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67; docs/contracts/schemas/provenance-manifest-v1.schema.json=1c8be7ef43a42abf255e4799d60f2cccc8df05dfc82706f6de613fbf4f03776c; docs/contracts/schemas/provenance-replay-result-v1.schema.json=a40ac65f5d3560cb78be15ba121ba2d7e56c29c8d9f8abc2d10e4e8d07dcc4b0; docs/contracts/reports/MH-C-PROVENANCE-REPLAY-001.acceptance.json=813419a30a6890431813875882597360d34c2543a4d83b32cde06ca9e90ca5b1; src/mathhead/kernel/provenance.py=3c4199867b3d1940030c926e67da8f3db165ee66553c409d5db814b7623d4b07; src/mathhead/provenance_store.py=ea0272a468c08f94456446d8070b2a604743c780f411fd784647fc8b74d26257; src/mathhead/discovery/provenance.py=38a775d19c850ba92a19fca77e7d9d668a9152759047558cc9cc1badab20c130; tests/provenance_replay/test_provenance_replay.py=a313a6dfeb81f978637252eccb154af31ee9dbfa00bce9261caeeee121238f00; tools/validate_provenance_replay.py=a356197e13a69b34bcc71eb8df4bd0a1be6aa4bf543e8ba93d4ac9d3549c7851; docs/PROVENANCE_REPLAY_V1.md=70c8ffaa9082b35be72784ccdc8f274b554dc71f1bc22d4d3461d688417cd00e; docs/trust/trust-base-v1.json=9b3c96372b6d8c41b1e494a3074c93cd6a1dea40920a0150002b0ae8c5104ea9; docs/trust/reports/trust-base-v1.json=d6aa3fd546ae323dd600f932602172b4119ca2bae0946076f53a7ef398dc31ee

**Limitations.** Only the accepted proof-term and RUP-only SAT replay fragments are authoritative; unsupported producer-only, external, DRAT, and RAT content deterministically remains non-authoritative until separately contracted replay exists. The filesystem adapter provides same-host atomicity and immutability checks rather than distributed storage semantics. Local Python 3.14 cannot own the policy-pinned solver and slow profiles, but exact-head GitHub CI run 31545078311 passed them, coverage, and the complete Linux, macOS, and Windows matrices on commit 7e77189d5d2c8b5e7aafac43fd9e4a0840b1a77e; reproducibility runs 31545074363 and 31545078108 and governance runs 31545074422 and 31545078130 also passed that exact head.

**Next.** Activate MH-036 and bind external Lean execution, exact toolchain identity, generated source, process observations, and independently checked results into the same content-addressed provenance and authority model.

---

## 2026-08-12 - Versioned SAT and UNSAT certificate replay hardened

**Task.** MH-034 (`done`).

**Changed.** Accepted and bound MH-C-SAT-REPLAY-001, added the dependency-minimal mathhead.kernel.sat boundary for canonical SAT assignments and RUP-only DRUP replay, replaced both legacy checker implementations with non-authoritative adapters, separated unsupported DRAT and RAT semantics, added deterministic budgets and immutable content-addressed results, refreshed the trust inventory and versioned documentation, and preserved clean-wheel compatibility.

**Learned.** A sound deletion fallback must retain already entailed clauses permanently after the first deletion-sensitive RUP miss and must expose the exact transition addition through the legacy compatibility result. Python 3.14 can validate the dependency-minimal implementation locally, while solver and slow profile authority belongs to the repository-declared Python 3.11 jobs.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json); MH-C-EVIDENCE-001=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3 (docs/contracts/MH-C-EVIDENCE-001.json); MH-C-CERTIFICATE-001=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740 (docs/contracts/MH-C-CERTIFICATE-001.json); MH-C-KERNEL-CHECKER-002=1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e (docs/contracts/MH-C-KERNEL-CHECKER-002.json); MH-C-SAT-REPLAY-001=0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50 (docs/contracts/MH-C-SAT-REPLAY-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-67092e8731d02e7c9a59e0c604d5e91009d26a88b7dd3f785724e5f18eaeaea6; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-c9acb16a9f0d75dede045f236efeaffb4220b361353dc55290d1bd171f985820; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-2d8ad5660f3d2d53e19be72c38928407fa470d94c6e656b712454dd65f79075b; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-c79604dbaacb2fad2d00023bafed7fc39196251f547f28f0ae315de857a67a8a; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-3149ac369a33c71553142a2507cc0f0b6bc014be8fb3a7c5b74825e1399f8036; trust-base-inventory=passed/exit-0/output-6c1a6558178f507bbd94006de13e40925949486cd5d7485e3e03e9039a82af26; proof-term-tests=passed/exit-0/output-c9edf7515b5e7444fa99276c954c8199db6c584ee520a22e6b0e087f77de7357; proof-term-contract=passed/exit-0/output-746c1c7e7ddc53b272f603ad4a78006b2a2af8f4df3b85f713a1ac40ce314598; kernel-checker-tests=passed/exit-0/output-96ca39a92b0b11068fff843d70702fee4f53290eeae3cc149931b62cab28fe1c; kernel-checker-validator=passed/exit-0/output-03f0dd57c8581539f7572fa371e04b54f24692c5c58c8eed16600a425fef91c4; kernel-checker-contract=passed/exit-0/output-c115f472b6d5dbce816e6e451db0770535c05da50d762e76b61dcb5f004510f4; kernel-checker-v2-contract=passed/exit-0/output-5379c6c02db12415f7fb6974bab58fb2370391ee86edae36811eced297f7dd3d; sat-replay-tests=passed/exit-0/output-dcd79764e17d98d675d94b6580847be56bd2f0881b854c36d20714ff44c85e9d; sat-replay-validator=passed/exit-0/output-c1baff3976224979af3b6a37bde3443caff210dbb247dea145116e55d6ece93f; sat-replay-contract=passed/exit-0/output-f00ba073b08d5d7825f69af52a4766a7e6ff3cf08cc5b005de774f76af346cbd

**Evidence.** docs/contracts/MH-C-SAT-REPLAY-001.json=0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50; docs/contracts/schemas/sat-replay-result-v1.schema.json=e7bccaba76958f185a94d7570b5c65972a855dd99888c04269074491506ef242; docs/contracts/reports/MH-C-SAT-REPLAY-001.acceptance.json=db930ea9a8b95004cf6cf7536fb02c7720bc1325f0d0a3db7c7b775e51f0074a; src/mathhead/kernel/sat.py=1c53dc24f8dd36bca730b5c2ceaa50627dfe5ef889ebabc958ff9ed31b331f39; src/mathhead/drat.py=ccb248c54d7d08cf071d3e9d59601a0cad38758240cb06be2c0224fdea5e164c; src/mathhead/discovery/rup_check.py=bb9df53e3086c2e9c3a1f9e8452cfc53e33cbc20355c0ae0e9af672b3a5a38cc; tests/sat_replay/test_sat_replay.py=26b4020f5d15ca685332ecbb51e4ef8c18d2576265389045e9bede854f2e3001; tools/validate_sat_replay.py=855df1ef3f686ff8ef762734a807f1c04f996a41155e9c4e9938d7528a4b6bf5; docs/SAT_REPLAY_V1.md=3abb857c8b20e163f7d8ffdf61540591721cd24a6ac5b776b4a8c092bf797858; docs/trust/trust-base-v1.json=da704741292a6763434b58d7dd1865b388d3fc6fc6c7371bab77d29c568e501e; docs/trust/reports/trust-base-v1.json=ff3d5f414ad427b7fce07a969bf21a4951630d9f0d07c3209a706ad29510ffcb

**Limitations.** The authoritative fragment remains deliberately RUP-only; genuine DRAT and RAT certificates are recognized and refused until a separately contracted checker exists. Local solver and slow dispatch are unsupported on the available Python 3.14 interpreter, but same-head GitHub CI run 31540645320 passed both profiles plus coverage and the full platform matrix on commit 7353a2681b637324d5adc57f30fbda950b5027b6; reproducibility runs 31540640363 and 31540645349 and governance runs 31540640376 and 31540645327 also passed that exact head.

**Next.** Activate MH-035 and make complete run provenance, persisted replay bundles, and every cross-layer identity content-addressed, canonical, atomic, and independently replayable.

---

## 2026-08-12 - Explicit arithmetic evidence internalized

**Task.** MH-033 (`done`).

**Changed.** Accepted and bound MH-C-KERNEL-CHECKER-002, superseded v1 result bytes, added a closed immutable arithmetic-evidence algebra for residue rows, CRT Bezout witnesses and product steps, sum induction differences, and polynomial identities, bound complete evidence into canonical v2 checker results, refreshed the trust inventory and versioned package documentation, and preserved clean-wheel compatibility.

**Learned.** Retaining exact residue values makes evidence substantially larger than verdict-only output, so the v2 envelope needs an explicit 64 MiB ceiling in addition to logical step and evidence-item budgets. A package version bump also changes the generated discovery report header, whose differential SHA must be refreshed without modifying the immutable historical discovery TODO.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json); MH-C-PROOF-TERM-001=20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac (docs/contracts/MH-C-PROOF-TERM-001.json); MH-C-EVIDENCE-001=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3 (docs/contracts/MH-C-EVIDENCE-001.json); MH-C-CERTIFICATE-001=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740 (docs/contracts/MH-C-CERTIFICATE-001.json); MH-C-KERNEL-CHECKER-001=78293c5a2e8845377e8bd704398c7a0058afcea74017dffbc2a18daac97ecff7 (docs/contracts/MH-C-KERNEL-CHECKER-001.json); MH-C-KERNEL-CHECKER-002=1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e (docs/contracts/MH-C-KERNEL-CHECKER-002.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-2e8a45e1b2e93c6cdb6ebc2ce583bd6bf0622c587a64ab1aeeea7ef3cd2be119; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-23f66ce5f81e5965432e672634fcc1b2643a3009ad651b9ef26e33a5ee99404c; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-0c3d8bed0835030e0693c3db81543964e9f1a55e16d6ef594c89997e0e88bd68; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-d52c4d6935b0343bf9c9a0f76b85c476a555dce37041d2ed06800f4930b4a9d3; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-4d99aca0b9162ad9fa780200437c1c1b523854b3058cbb01bdccc1a6952c9753; trust-base-inventory=passed/exit-0/output-986a9e104066b0280d1da7057affe41e1326aebcd9468c47e78638162c3e7a48; proof-term-tests=passed/exit-0/output-657b02841d00755830116f9687287da37e549bd215291cfd15212b94a3a6a452; proof-term-contract=passed/exit-0/output-e88b43fe86ae3934573aa302ba9637e561d3bbcc8f80e6837f05153688a26927; kernel-checker-tests=passed/exit-0/output-fd0f5f42097415b48baf8d9209a6018f9fe81ecc7d73d55e620009129ad628de; kernel-checker-validator=passed/exit-0/output-03f0dd57c8581539f7572fa371e04b54f24692c5c58c8eed16600a425fef91c4; kernel-checker-contract=passed/exit-0/output-a66425497f2b26bec99125cdbefdb4745042994b848c1cd138c1803fb9b89e9f; kernel-checker-v2-contract=passed/exit-0/output-dfc92e2d1338bf10ea1bc0ef2d2828ea9ab56f5e06ccf4ba0ca420c261b66168

**Evidence.** docs/contracts/MH-C-KERNEL-CHECKER-002.json=1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e; docs/contracts/schemas/kernel-checker-result-v2.schema.json=1eb1f5560f493728f23214356583296880c74d9403377f5a867139a12bacff8b; docs/contracts/reports/MH-C-KERNEL-CHECKER-002.acceptance.json=a3cc5bb1371b173e083857cbb6f97320cc34bb684154cb97c681038ff0a15983; src/mathhead/kernel/arithmetic_evidence.py=56edfa4d5e93ebda9c718834be46eab1289ace6ca9dda73345333d33b585977c; src/mathhead/kernel/checkers.py=ea553033f81e670bbb5fb3b7826a912c2aa47980ada86e18287508698dff73b4; tests/kernel_checker/test_arithmetic_evidence.py=3a978d9c8431b3c4fcfb727f9e91ae9fa36c208459172aa25de11c23b4f9b698; tests/kernel_checker/test_kernel_checker.py=05b3b1d2c05d6feda09725bb1c851d6e6fa97d4dbbd57ab0f2fe8ed07667f869; tools/validate_kernel_checker.py=43b5749be0b153d369cbf43e4ee5ce74e77c263a3de42de76e8435015f5db272; docs/KERNEL_CHECKER_V2.md=72805d30616f531d3d0517ec207c7e2dd5f7449a9cde3e7e7af94963af1fe5c3; docs/trust/trust-base-v1.json=75979cf32c1283cb6f25ef83db9fe4b3ff5d2c36c89b2a44069982540f80a77a; docs/trust/reports/trust-base-v1.json=7d1063b32dc4b42fa8d7fe59b73cfb3913504005650e2a9bfc4fa9eb55a23614

**Limitations.** The current checker intentionally covers only the four MH-031 arithmetic proof rules. SAT and UNSAT proof replay, whole-run content-addressed provenance, external Lean authority, and transition red-teaming remain MH-034 through MH-037. Same-head GitHub runs 31536947340, 31536947349, 31536944402, 31536947331, and 31536944491 all succeeded on commit f6f3e8cf06f3560e92124196ef66a6c4c99120fb.

**Next.** Activate MH-034 and replace the two legacy RUP and DRUP checker paths with one versioned, bounded, streaming, dependency-minimal SAT certificate replay boundary.

---

## 2026-08-11 - Dependency-minimal kernel checker extracted

**Task.** MH-032 (`done`).

**Changed.** Accepted and bound MH-C-KERNEL-CHECKER-001; implemented a five-internal-module, seven-stdlib-root exact checker for residue, CRT, finite-sum induction, and polynomial-identity proof terms; made verified statements and checker results immutable and replayable; added canonical result bytes, deterministic resource accounting, stable invalid and exhausted reason codes, a deliberately non-authoritative legacy adapter, adversarial and legacy differential coverage, trust-base bindings, and clean-wheel checker smoke validation.

**Learned.** A normal import of the legacy discovery kernel executes the discovery package initializer and pulls SymPy into the core environment, so dependency-minimal compatibility must inspect legacy-shaped inputs without importing producer packages and must still rebuild only candidate proof terms for independent checking. Full Draft 2020-12 validation also caught a trust-inventory enum drift that the dependency-minimal fallback validator correctly did not overclaim to detect.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json); MH-C-PROOF-TERM-001=20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac (docs/contracts/MH-C-PROOF-TERM-001.json); MH-C-EVIDENCE-001=c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3 (docs/contracts/MH-C-EVIDENCE-001.json); MH-C-CERTIFICATE-001=0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740 (docs/contracts/MH-C-CERTIFICATE-001.json); MH-C-KERNEL-CHECKER-001=78293c5a2e8845377e8bd704398c7a0058afcea74017dffbc2a18daac97ecff7 (docs/contracts/MH-C-KERNEL-CHECKER-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-aa453f31a651ca3e2d61dd5c9b5dae33dc7776e1e334a931ae80e95f97eefee3; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-8af5f6bb9969f8faabe20908a06bc681d58243b34cef9a18755c03e0b98265df; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-0c3d8bed0835030e0693c3db81543964e9f1a55e16d6ef594c89997e0e88bd68; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-891e52c26cb543b20354b1721c46aea37784df6220188f74ec03c4588c3d2cd1; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-5c921f8b705a6bda77e571b356510ca1d87ac23af921040e246090e05876879d; trust-base-inventory=passed/exit-0/output-c8f493685cf7c7536c85c50ed599e6c64e11fc663b9756f91f5ab61a74d09929; proof-term-tests=passed/exit-0/output-c9edf7515b5e7444fa99276c954c8199db6c584ee520a22e6b0e087f77de7357; proof-term-contract=passed/exit-0/output-693821a901d106279d577c3b774a5c49c5eb11c055819d24f5140fd3136485e9; kernel-checker-tests=passed/exit-0/output-ade2e5dd068ba11328b3c8f4d410d1ca35bc694323de1740b1cf7496055a330a; kernel-checker-validator=passed/exit-0/output-0a2ef8427e5c71544541d77eeaf67b54599d4642f3623f7a80a85dc9b8b44546; kernel-checker-contract=passed/exit-0/output-bba199517ae072754fe5c3436a1c669bbceca6138673f806dc05d7d6a207cc55

**Evidence.** docs/contracts/MH-C-KERNEL-CHECKER-001.json=78293c5a2e8845377e8bd704398c7a0058afcea74017dffbc2a18daac97ecff7; docs/contracts/schemas/kernel-checker-result-v1.schema.json=0718099abb10ff08501909b59faa92a1d4579c9047ef29576b16b1ed8a1892e4; docs/contracts/reports/MH-C-KERNEL-CHECKER-001.acceptance.json=c06d7d803a545cd14baf63656fb0524ec13d6fe5924d8d53256676570672255a; src/mathhead/kernel/checkers.py=0244548329e1efcc1f669c9d939ef4f7a9cd8f4dbd295afe0375444517d97db2; src/mathhead/legacy_kernel_adapter.py=c2c617892be62c33a71b9825b0e4c3b1b63cf48108e4f9c7e0d47d6ba6c535e4; tests/kernel_checker/test_kernel_checker.py=46ecdf21be05eac452c42f77a603534bbe67eef7857a922f835a26551ac7f242; tests/kernel_checker/test_legacy_kernel_adapter.py=c6f3aae8c87bb6bcfe9d099ceb3f0db0ddc4742aaa2ca2f0fe779f9a360ff3a8; tools/validate_kernel_checker.py=548facc14607dcf671b3696ec0fa837a0812408773335bba7844ebeb02b3eaea; docs/KERNEL_CHECKER_V1.md=73fd53fb245b81a3dd541ab6593ab53f6d7ca7cf475650233b377f12464d88e2; docs/trust/trust-base-v1.json=9fde5e9f582288bd65b6d2be47ff48f3d7a0982ba4f6bb92c4721b3c39a83e0f; docs/trust/reports/trust-base-v1.json=9a982a9d8e392639b87c2242a8f76f1b83f19fb4ca7752ad833e7afef465f18d

**Limitations.** The checker intentionally keeps residue enumeration, pairwise coprimality, induction differences, and polynomial comparison as trusted internal arithmetic; MH-033 must expose those claimed derivations as explicit evidence. SAT replay, complete content-addressed provenance, external Lean authority, and transition red-teaming remain MH-034 through MH-037. Same-head GitHub runs 31533674911, 31533674366, 31533669262, 31533674865, and 31533669207 all succeeded on commit f834712ad439ae1dd06807ec0c2f6dbb67eda636.

**Next.** Activate MH-033 and internalize every residue, CRT, induction, and divisibility derivation that a trust tier claims into explicit, canonical, independently replayed evidence objects.

---

## 2026-08-11 - Immutable canonical proof terms implemented

**Task.** MH-031 (`done`).

**Changed.** Accepted and bound MH-C-PROOF-TERM-001, then added a closed four-rule proof-term algebra with constructor-controlled frozen final values, exact integer and Fraction normalization, canonical CRT ordering, deep graph revalidation, canonical full-SHA JSON envelopes, fixed byte, depth, node, part, coefficient, and integer budgets, stable classified failures, no authority fields, and no third-party or effect imports. Added eighteen adversarial tests, two fail-closed status checks, documentation, and deliberate trust-inventory expansion to 119 modules. Preserved the immutable MH-016 oracle by teaching its regression test to require recapture refusal after legitimate post-baseline source growth.

**Learned.** Python object.__new__ cannot be sealed; structural values therefore remain non-authoritative and every hash, serialize, parse, and future-checker boundary revalidates the full graph. The first new src module after MH-016 also revealed a test that conflated frozen capture provenance with a permanent ban on additive source growth; the oracle itself already refused recapture correctly, so the test now validates either exact-source deterministic rebuild or fail-closed refusal.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json); MH-C-PROOF-TERM-001=20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac (docs/contracts/MH-C-PROOF-TERM-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-82e33390190aa698fe4429de817a8335ad3f0a26e371d36214d11a794137883f; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-cd27369d2c3c1e5e945c6667958929ca6ec14fb4763c78eecbadb284a2c16b57; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-d604a5ef9c95d038115ea70ca1e5327f27f0827faf37348f6ffef855e757d741; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-fe8c1ca4463ac3780a26850025b401cd345177019dfa0cf4e9fa063c4a29ce0c; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-594a3bd2f325aedd0de0058a70b55ba607b05bcd3df85d8747b7b89e97da895c; trust-base-inventory=passed/exit-0/output-ffb335a3d097deb0911326cda57e41b0140f4a0aaa64f7384625d638d23134aa; proof-term-tests=passed/exit-0/output-c9edf7515b5e7444fa99276c954c8199db6c584ee520a22e6b0e087f77de7357; proof-term-contract=passed/exit-0/output-524579488ee992bdb48888a096315f08a5cae16b73bd317a477f55ff11b3e119

**Evidence.** docs/contracts/MH-C-PROOF-TERM-001.json=20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac; docs/contracts/schemas/proof-term-v1.schema.json=647bfd65e611a4e427ff36dd9e2c3e07af4839aa7d91a180d55af3e5e5ea99f7; src/mathhead/kernel/proof_terms.py=003971c2f3c656dbe02926ebf93ed674a1c5f859757b87b3847271d2703c84f9; src/mathhead/kernel/__init__.py=659b005a816912d5efed16606a9cea828e4ca77301bc1078221b4f19f65b88e3; tests/proof_terms/test_proof_terms.py=62bea91e5f02c354397152b277624449da51a9a0e4472e165dbaba07e03d4ba7; docs/PROOF_TERMS_V1.md=58c7a83019eeee4b13d517d3d813aa3cb80286b0de1220ec23ce1170c16f022f; docs/trust/trust-base-v1.json=6fcaf1aafd609b439b932d605b8c9555a531ce11d49c6ddef322f45259c82678; docs/trust/reports/trust-base-v1.json=e66d6babda6be7105af64c7a61967c328be36b5a1b9305d1551104338a9da4cd; .project-status.toml=e5040ff1727e5e1c53fbf1de63762b01866f58226e0113228b8339b55f3feee1; docs/project-facts.json=959b616b5ed6be5ce14304e40478f83d54eda706ac55f46aadebdf5e22a42738

**Limitations.** Proof terms are structural evidence only. The legacy discovery Theorem remains deliberately forgeable through object.__new__; mathematical evaluation, checker-issued immutable results, certificate migration, legacy adapters, and proof semantics are MH-032. CPython, Fraction, hashlib, json, and dataclasses remain trusted primitives. Same-head GitHub runs 31530300243, 31530300284, 31530296549, 31530300227, and 31530296483 succeeded on commit 099703d40c6a053290d9c22b9f4379cd403e3a53.

**Next.** Activate MH-032 and extract dependency-minimal mathematical checkers that alone can issue immutable attestations.

---

## 2026-08-11 - P3 trusted computing base inventoried

**Task.** MH-030 (`done`).

**Changed.** Accepted and bound MH-C-TRUST-BASE-001, then added one closed canonical trust-base inventory and deterministic static report covering all 117 source modules, 32 external import roots, 24 parser, serialization, hash, arithmetic, checker, solver, runtime, transport, process, and proof-assistant surfaces, seven entry-point closures, dynamic imports, effect boundaries, authority owners, two existing import cycles, trusted bytes, risks, controls, and exact MH-031 through MH-037 migration ownership. Added a dependency-minimal checker target capped at twelve modules and nine stdlib roots with zero third-party, dynamic-import, or effect roots, twenty-four adversarial tests, two fail-closed status checks, documentation, and a P2 manifest-prefix regression that preserves immutable MH-027 and MH-028 evidence when later contracts append.

**Learned.** Static source analysis confirmed that the current independent boundary is not one kernel: stdlib certificates, two RUP and DRUP implementations, and the discovery LCF-style kernel are separate authorities; exact and approximate math also share legacy surfaces. Adding the first P3 contract exposed that MH-027 hashed the entire live manifest, so later append-only contracts rewrote P2 evidence; binding its original manifest prefix preserves the stable fixture bundle while retaining fail-closed P2 drift.

**Contracts.** MH-C-WORKFLOW-001=99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca (docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md); MH-C-TRUST-BASE-001=2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456 (docs/contracts/MH-C-TRUST-BASE-001.json)

**Validator profile.** fast.

**Validators.** dev-environment-contract=passed/exit-0/output-a5d12a4366f7b754d6b4bfb641c42c61ab63cd2fca9373521e42043411707de2; legacy-baseline=passed/exit-0/output-67e9b831ee9562c7349211b81b71c8f6980fba822c741c29ab2c70bf50d046e2; optional-dependency-contract=passed/exit-0/output-9b6c89c4799b009bf7763e0fa95d16d60ca0dd4bb79b91eb3b2f9e4c8d1a21c9; graph-budget-contract=passed/exit-0/output-cee9ef7d724bd33473900600123db290c92ac623f1b64f507936438047392503; command-encoding-contract=passed/exit-0/output-6d10647e5ec87d340636de633ae04d25f6d634a024e2b03108dacc2906fde5e7; live-mcp-contract=passed/exit-0/output-6d1c5de7dfea9929d580ad221b80d16d1f297b87f0a048a68065a9adbf5f8312; project-metadata-contract=passed/exit-0/output-f243a673e396961eaa55196fba23ebe3802ab94c8ae17a4c14d6b473b834d9a0; ast-parse-contract=passed/exit-0/output-70ca7baa7b3b75148e5a0f57dcdbcecf5751715a0cf16ef5f244b6d1a3957a48; discovery-portfolio-contract=passed/exit-0/output-4181ac69819cf2985cfc4ff6516a1f863b08e14786a0623853c5d703da7fe08e; legacy-compat-contract=passed/exit-0/output-2b0378541035d4578c07dd455ba51ee05ecee22b1690a4678f7489d96c3d808f; contract-artifact-tests=passed/exit-0/output-aebfe660e81ff4933df083447a13f7d8852a7206980d829bba9a32fded2bc2a4; contract-artifact-workflow=passed/exit-0/output-b0ca27108a6d7ed70aaeccfb40c1aebe9fa13fe23fd94172fecda53e51b09c19; problem-ir-contract=passed/exit-0/output-5d79fe1def4d4f26b36ecde4fd4b1f61938869ca948574a5f135c37963d7de68; theory-context-contract=passed/exit-0/output-f24f2be1f18acde0fece5a52df2a6e01dd006959aae7da3d492c5d05658b531c; resource-budget-contract=passed/exit-0/output-8bb1a05a7c0196d839031e95e46f4c01221e27baee2453596bc31e029e23d0ae; engine-result-contract=passed/exit-0/output-8b2c527ad5ee906e03c9b0fbf95ddfaeb7b7f4be28d14142c5c5eb72f2532d79; evidence-certificate-contracts=passed/exit-0/output-ca715228579cd4c11772b6a6ecc5801f7871a3cfbf08772a7f49280d77aba173; theory-plugin-contract=passed/exit-0/output-446dc06ef34cfc678f32c989d2f3299e19cf51dae037a451f2fdc57ff0896f9b; foundation-conformance-tests=passed/exit-0/output-2d67f90a6acb892aed28853240d29c3244eb531c2fe6cd80a6a3193917aa7d15; foundation-conformance-report=passed/exit-0/output-dc7fd352efc5b9f6b98be59ad807e6bad6acb2bbe1509b46868087a60823aefe; foundation-reference-fixture-tests=passed/exit-0/output-bc0c02312d6f82b33256bd5bdebf6fd71f8db69b2bde6c55ce48d0f858d935bc; foundation-reference-fixtures=passed/exit-0/output-2f2cff4f7c4334c6f0b604d9dfe39f5a47e909d37bea2b6998f854e6c9d77d9f; trust-base-tests=passed/exit-0/output-3e2434009aad95706041792ad296f00380c59ffe2b20791bcb239ab1165ae934; trust-base-inventory=passed/exit-0/output-c900754b4d627b9dcc7de0ff172efe52055356b275e772d5cdcac3d534e9793a

**Evidence.** tools/validate_trust_base.py=2a5e88ea5041a5cad83cff4f7cadfbb99a3ca42e1844c5bc6459c86f61114db7; tests/trust_base/test_trust_base.py=98d8aef260e9a4379e3506e26afc25b463cd2464f7c43a62dc0a2b218bc53fdd; docs/trust/trust-base-v1.json=88adcf18e4c47018a29b8935e1522fe662e2c6cdf581a355e5ddebcaefe04026; docs/trust/trust-base-v1.schema.json=99c3024ffc5f2de636d2a61ed9c01a9396aa51c1f54b09fe14e6dde7d6816f3d; docs/trust/reports/trust-base-v1.json=c41de0a7363f2bf860d904668051cbba11f5447c69caf96edfda93e96fafbad7; docs/trust/README.md=44dcace52022006913c401db87896f955ad6f44ac453711b1999ce32bbee6562; .project-status.toml=8835a1c616b3b659e32ffda3a869d20d64bd5c4da73d24bfa9c9f7d81f2bd445; docs/project-facts.json=a657525ea48fc82edc7dba7387c2b76d6f9cf38cee3ddadb886117e41bf924fa; tools/validate_contract_conformance.py=8058cf116c0e2a34865ee53832dffcc28cfda817f9fa58c18287dba14a40efd0; tests/contract_conformance/test_contract_conformance.py=94b9d20f1e47ff2bec6dba49e1cf8696b6d75d2527887d960566c8536d42ce85

**Limitations.** This inventory is governance and static-analysis evidence, not a proof that CPython, hashlib, integer or Fraction arithmetic, existing checkers, Z3, SymPy, PySAT, nauty, MCP, or Lean is sound. Existing theorem objects remain forgeable via object.__new__; the certificate checker still has a visible approximate branch; two RUP implementations and two import cycles remain; Lean export is pending. Production proof terms, checkers, derived evidence, SAT replay, provenance, Lean, and red-team work remains MH-031 through MH-037. Same-head GitHub runs 31527419068, 31527418980, 31527414683, 31527419083, and 31527414712 succeeded on commit 580bef30b4216caed42ca0ade7127c63dddab018.

**Next.** Activate MH-031 and replace forgeable legacy theorem objects with immutable constructor-controlled proof terms.

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

