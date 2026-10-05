# Ops — the application, generated

**2026-10-04**, on `next`. **ADR-0104**, superseding ADR-0103.

The owner asked for a plan to make the application's picture a chart like the
estate's rather than an image, then answered it: in `Details`, whole without a
cycle; tables and step numbers left to judgement. So the manifest learned the
inside of each service - its tables, its parts with the file and symbol each
is, what each reads, writes, publishes and consumes, and each queue's event
contract - and `manifest-check` holds it to the code both ways, refusing too a
part that touches another service's table. `scripts/generate-app-flow.py`
walks the flow from the browser and numbers what it meets: ten steps, the same
ten the drawing had, now derived. Clauses the manifest cannot say are notes
with evidence the generator checks in the code. The layout file only places
things, and a thing with no place or a place with no thing is a refusal.

Proven on copies of the tree: a fourth service with no place, a place for a
queue that does not exist, a receipt that stopped being idempotent, the worker
writing the api's table, a renamed table, a renamed class - each named. Gates
16/16, contrast and every page check green; light and dark photographed.

Then two of the owner's notes. The application's picture is in Details only,
and the estate now points to it in one line. And the lab was not plain at a
glance: wherever the page names an environment it now reads `lab ·
Kubernetes`, with one line in its panel - the same images stage tested, on EKS,
beside prod and not after it. Display only, on the owner's word: the id `lab`
stays in Terraform, the GitHub environment, the status files and the page's
data.
