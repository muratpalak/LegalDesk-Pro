# LegalDesk Pro — Portfolio Case Study

**Repository:** https://github.com/muratpalak/LegalDesk-Pro  
**Status:** Local demonstration / portfolio project  
**Technical focus:** FastAPI · SQLite · JavaScript  
**Automated workflow:** [GitHub Actions](https://github.com/muratpalak/LegalDesk-Pro/actions/workflows/ci.yml)

## Context and problem

This project explores **business process modelling and application support** through a reproducible portfolio exercise. Its examples are not represented as an employer deployment or production customer implementation.

## Implemented capabilities

- Multi-module business CRUD processes
- Document upload, retrieval and basic validation
- Backend testing and SQLite data persistence
- Local-first HTML/CSS/JS application

## Reproducible review

Read the repository [README](../README.md) for supported platforms and installation prerequisites. Where the necessary runtime tools are installed, reproduce the checks using:

```bash
python3 -m pip install -r requirements.txt pytest httpx && python3 -m pytest -q
```

The associated CI workflow provides evidence of the configured automated checks; it is **not** a guarantee of full feature coverage, security accreditation or production availability.

## Boundaries and honest limitations

Demo only with synthetic data. No authentication or production security review; not suitable for real legal data.

## Relevance to IT roles

Application support, requirements translation and business workflow automation.

## Deutsche Kurzfassung

**Projekt:** Lokales Kanzlei-Workflow-Demo für Akten, Termine, Aufgaben, Finanzen und Dokumente.  
**Schwerpunkt:** Business process modelling and application support.  
**Nachweis:** Quellcode, Installationsanleitung, definierte Tests und GitHub-Actions-Protokolle.  
**Einordnung:** Portfolio-/Demonstrationsprojekt; keine Behauptung eines Produktiveinsatzes.
