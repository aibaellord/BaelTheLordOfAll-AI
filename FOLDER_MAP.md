# Project Folder Map & Integration Reference

This document maps every major folder in the BaelTheLordOfAll-AI project to its system role and integration point. Use this as the living reference for orchestrators, automation, and development.

---

| Folder         | System Role / Contents                                      | Integration Notes |
|----------------|-------------------------------------------------------------|-------------------|
| core/          | All reasoning, orchestration, memory, agent, intelligence   | Orchestrators auto-discover agents, skills, plugins, workflows |
| .github/       | CI/CD, automation, workflows, community standards           | Workflows for build, test, deploy, docs; triggers orchestrators |
| .agent/        | Agent templates, skills, agent workflows                    | Auto-register agents/skills at startup; expose in UI |
| .ai/           | Prompts, model configs, orchestration settings              | Auto-load into orchestrators and UI; live editing enabled |
| .gemini/       | Creative/synthesis workflows, settings                      | Integrate creative pipelines; UI triggers |
| plugins/       | Custom plugins, reasoners, connectors, tools                | Auto-load at runtime; expose in UI and orchestrators |
| workflows/     | Workflow definitions, automation logic                      | Auto-register; UI run/edit |
| integrations/  | External system/API integrations                            | Auto-load; expose in orchestrators and UI |
| ui/            | React/TypeScript frontend                                   | All features accessible, one-click actions |
| docs/          | Documentation, guides, API docs                            | Auto-generate/update from codebase and reference folders |
| tests/         | Test suite for all modules and features                     | Automated in CI/CD; coverage for all modules |
| data/          | Data storage                                                | Orchestrators/UI access and visualization |
| memory/        | Memory storage                                              | Orchestrators/UI access and visualization |
| knowledge/     | Knowledge base                                              | Orchestrators/UI access and visualization |
| research/      | Research data and scripts                                   | Orchestrators/UI access and visualization |
| outputs/       | Output storage                                              | Orchestrators/UI access and visualization |
| deploy/        | Deployment scripts/configs                                  | Used by CI/CD and orchestrators |
| docker/, k8s/  | Docker/Kubernetes configs                                   | Used by CI/CD and orchestrators |
| scripts/, tools/| Utility scripts and tools                                  | Used by automation and developers |
| personas/      | Persona definitions for agents                              | Used by agent orchestrators and UI |
| prompts/       | Prompt templates for LLMs/agents                            | Used by orchestrators and UI |

---

- All orchestrators and engines must dynamically load from .agent, .ai, .gemini, plugins, workflows, integrations.
- UI must expose all features for one-click access and automation.
- CI/CD must automate build, test, lint, deploy, and doc generation.
- Documentation and knowledge base must be auto-generated and always up to date.

> This file is auto-generated and should be updated as the project evolves.
