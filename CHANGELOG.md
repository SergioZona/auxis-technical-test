# Changelog

## [1.0.0](https://github.com/SergioZona/auxis-technical-test/compare/v1.0.0...v1.0.0) (2026-05-21)


### Features

* implement LangChain RAG adapter with vector search and SQL query tools for document intelligence ([21d2f73](https://github.com/SergioZona/auxis-technical-test/commit/21d2f7321a825031d9f0aa381e69f4863641f05f))
* implement RAG chat, document metadata curation, and Langfuse tr… ([9a37453](https://github.com/SergioZona/auxis-technical-test/commit/9a374539183c91714c14906b252e15e4ac51ef0a))
* implement RAG chat, document metadata curation, and Langfuse tracing ([a9901a5](https://github.com/SergioZona/auxis-technical-test/commit/a9901a5b0ed872d2458ae0b9c09ff5ffeefb364c))
* **rag:** overhaul architecture diagrams, integrate SonarQube docker scan, purge obsolete env variables ([b994bd7](https://github.com/SergioZona/auxis-technical-test/commit/b994bd7c15c5c358e8337d00c57debbe110fdd35))
* **tracing:** add LangSmith tracing and fix CI Add [@traceable](https://github.com/traceable) to router endpoints, document parser, and RAG adapter. Fix Ruff lints, import ordering, type signatures, and test config ([3e9895a](https://github.com/SergioZona/auxis-technical-test/commit/3e9895a33be34eddcab653c0916bc15174425a67))


### Bug Fixes

* **ci:** resolve sonar async warning and coverage gaps ([9227188](https://github.com/SergioZona/auxis-technical-test/commit/9227188083de3f208998c496af7bffb78b2f57a2))
* **docker:** attach api and ui to dokploy-network for SSL cert issuance ([97fd6cb](https://github.com/SergioZona/auxis-technical-test/commit/97fd6cb8de206e203e1618ead1e06cd28172ccdf))
* **docker:** change ui healthcheck from wget to python urllib ([d04e97a](https://github.com/SergioZona/auxis-technical-test/commit/d04e97ac7987f00d85b50b7fcd734a1595f68651))
* **docker:** update ui healthcheck to use wget and increase timeout ([29e3dda](https://github.com/SergioZona/auxis-technical-test/commit/29e3dda859bf81c37ea82a531f8899409fb1e341))
* **infra:** resolve SonarQube ACR security hotspots S6329 and S6378 ([3bbc2ca](https://github.com/SergioZona/auxis-technical-test/commit/3bbc2ca8da3bbae3a4759787600034241fcde47d))
* **persistence:** strip timezone from upload_date ([42a8bf5](https://github.com/SergioZona/auxis-technical-test/commit/42a8bf50e62eedc4ddf865b6868b42bc200e20cf))
* ruff format ([634591a](https://github.com/SergioZona/auxis-technical-test/commit/634591a092b42b8c7bb9ca94a3996e88c04102f7))

## 1.0.0 (2026-05-19)


### ⚠ BREAKING CHANGES

* configure release-please v4 manifest and config files

### Features

* **ci:** add self-hosted SonarQube integration ([cb32d68](https://github.com/SergioZona/hexagonal_backend_template/commit/cb32d68bef14880d40259f959f991e429df124eb))
* **ci:** add self-hosted SonarQube integration ([06ca1c4](https://github.com/SergioZona/hexagonal_backend_template/commit/06ca1c476491c24e7212182bf23900ec63084714))
* configure release-please v4 manifest and config files ([8c327ad](https://github.com/SergioZona/hexagonal_backend_template/commit/8c327ad16492b925f5473678451245cddbb66c4a))
* force next release to be 1.0.0 and set manifest base to 0.0.0 ([dd6a9cc](https://github.com/SergioZona/hexagonal_backend_template/commit/dd6a9cc1f46ae59b75c70930802f4a17688c0d6a))
* init project with hexagonal architecture and agent tools ([62b59cf](https://github.com/SergioZona/hexagonal_backend_template/commit/62b59cf44ad206db890697cd75bfc4fe90559b88))
* **init:** setup hexagonal template and AI agent tooling ([dba95bb](https://github.com/SergioZona/hexagonal_backend_template/commit/dba95bb181cbca87d40c36d577641d96e0756995))


### Bug Fixes

* **architecture:** resolve importlinter execution and clean up type checking imports ([e49802a](https://github.com/SergioZona/hexagonal_backend_template/commit/e49802a072d530421d704d7b83b2fb101dea44d8))
* **ci:** remove type ignore and use Field default validation ([474c9c9](https://github.com/SergioZona/hexagonal_backend_template/commit/474c9c923a35980fe365ab39264ec24e2edd395e))
* **ci:** type-annotate dict returns and format placeholder test ([60e3d8b](https://github.com/SergioZona/hexagonal_backend_template/commit/60e3d8bdf261ccfd22539d3d819afab86fadc993))
* **lint:** resolve ruff errors and optimize type checking ([e121cfe](https://github.com/SergioZona/hexagonal_backend_template/commit/e121cfe0c3ee29ba4b0aee7a45f68fa104b096c9))


### Documentation

* add local CI checks guide ([56926a6](https://github.com/SergioZona/hexagonal_backend_template/commit/56926a671e3f962d14bd3d8f77b7eaa005dc4edd))
* reorder compose files and update README, getting-started, and agent docs with repo links ([96714fd](https://github.com/SergioZona/hexagonal_backend_template/commit/96714fd3bb4614c8c5445b87d38fe41ee5fbeb13))
* **rules:** add proj-ci rule and update CONSTITUTION, getting_started, code-style ([cab4dd0](https://github.com/SergioZona/hexagonal_backend_template/commit/cab4dd013f056ebea1ceff90556fa1ec08cb247d))
