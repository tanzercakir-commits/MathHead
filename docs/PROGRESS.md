# MathHead reconstruction progress

Append-only history for `MH-RECONSTRUCTION-V1`, newest first. Entries are added
only through the repository-owned status tool after adoption.

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

