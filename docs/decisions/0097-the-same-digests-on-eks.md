# ADR-0097: The same digests on EKS

## Status
Accepted (Phase 43, 2026-09-13), in slices; each slice's verification is
recorded under Consequences as it happens. Item 3 of the plan in **ADR-0094**.
Builds on ADR-0095 (three images, a release of digests) and ADR-0096 (the
queue, the task roles' permissions). Reverses the *EKS / Helm — out* entry
of `docs/next-phases.md`, as ADR-0094 said it would.

## Context

Two runtimes for the same containers is the comparison; one runtime is a
deployment. The plan put Kubernetes third on purpose: on one container it
would have shown what ECS already shows at a control-plane price, and after
the split and the queue there are three services, a per-service identity and
an asynchronous seam for a second runtime to carry. The owner accepted the
cost for hands-on value and asked that the principle of a large project be
kept: Terraform for the cluster, Helm for the application, no GitOps
controller, and the page observing the cluster rather than trusting the run.

The owner's decisions, taken before a line was written:

> по всем пунктам как рекомендуешь

on: a complete third environment; managed nodes rather than Fargate; the
Terraform/Helm boundary; the lab beside promote in the cycle.

## Decision

**D1. The lab is a whole environment, beside stage and prod.** `infra/envs/lab`
has its own VPC, RDS instance, secret, queue and dead-letter alarm — the
modules the ECS environments use, unchanged — and its own state key, tags and
deploy role. It shares nothing with stage; an environment that reached into
another's database would make the comparison a lie about isolation. It is
beside prod, not instead of stage: replacing stage would lose the thing being
compared.

**D2. Managed nodes, in the public subnets.** Two `t3.small` on-demand
instances in one managed node group, public IPs and no NAT (ADR-0006), AL2023.
EKS on Fargate is closer to the project's no-servers posture and further from
the Kubernetes a reader expects — no DaemonSets, a CoreDNS patch, IP-mode
targets only, slow pod starts — and the story here is the second runtime, not
the absence of nodes. One instance type, so one price: the sizing reader
refuses a list of several.

*Amended 2026-09-13, evening.* **Spot.** The owner asked whether a smaller
node would do and whether spot is a real practice; the answer to the first is
no — EKS caps pods per instance by ENI, `t3.micro` carries four and the
system pods alone are eight across two nodes — and to the second is yes, for
exactly this shape: stateless pods, a managed control plane, the database on
RDS, an environment that lives twenty minutes. An interruption with its
two-minute notice is a reschedule, not an outage, and a lab that survives
one is a test nobody had to write. `capacity_type = SPOT` by default, 60–90 %
off the nodes, which were a third of the lab's hour. Still one instance
type: the cost fold prices what the configuration declares, and it prices it
at the on-demand rate as a ceiling, said so in the model. A wider pool
(`t3a.small` beside `t3.small`) and ARM (`t4g.small`, which needs multi-arch
images from every build) are noted and not taken.

**D3. Terraform owns the cluster and the platform; Helm owns the
application.** Terraform makes the control plane, the node group, the
cluster's OIDC provider, the access entries, three IRSA roles, the namespace,
the Kubernetes Secret carrying `DATABASE_URL` (the same Secrets Manager value
the task definitions inject, passing through a state that already holds the
password), and the AWS Load Balancer Controller as a `helm_release`. The
application — three Deployments, two Services, one Ingress, two ServiceAccounts
— is a chart in this repository installed by the workflow with `--atomic
--wait` and the digests stage tested. Argo CD and Flux stay out: one more
system to run, and a paragraph explaining their absence is worth more here
than the controller.

**D4. IRSA is the task role.** ADR-0096 D6 gave the api and the worker one
permission each on their task roles; here each gets an IAM role that trusts
exactly one service account in exactly one namespace, holding exactly that
permission. The controller gets the policy its own project publishes, vendored
beside the module from the same release as the chart and bumped with it — the
one wide policy in the lab, held by the one service account that needs it.

**D5. Authentication mode API, and the creator is the first admin.** No
`aws-auth` ConfigMap: the principal that applies the configuration — the
deploy role in CI, `demo-admin` on the devbox — is cluster-admin by EKS's own
bootstrap, and any further admin is an access entry a reader can list. The
owner's SSO role is passed as `TF_VAR_admin_principal_arns` by the workflow —
its full ARN, path included; the first apply tried the path-stripped form and
EKS refused it as an invalid principal — so kubectl works from the devbox
after a cycle created the cluster. Never the creator itself: the creator's
entry is EKS's own, and the second apply learned that a second one for the
same role is a 409, so a local apply under the SSO role passes nothing.

**D6. The teardown trap is met with tags.** An Ingress makes the controller
build a load balancer Terraform does not own. Two things follow: the chart is
uninstalled — and the balancer's deletion waited for — before `terraform
destroy` reaches the VPC, and the controller runs with `defaultTags` of
`Project` and `Environment`, because `sweep-orphans.sh` asks the tagging API
for exactly those and would otherwise be blind to the one resource in the
environment nothing declared. The first is the workflow's (slice three); the
second is here.

**D7. The public endpoint stays public, and Kubernetes secrets stay under
AWS's key.** Checkov's three findings on the cluster are decisions: the API
server is reached from GitHub-hosted runners and the devbox and there is no
private path (no NAT, no VPN, no runner in the VPC); a CIDR allow-list would
name addresses GitHub does not publish per job; what stands in front of it is
EKS's authentication and an hour of life. Every cluster of 1.28 or newer
already envelope-encrypts secrets with an AWS-owned key; a customer key would
leave one key pending deletion per cycle for a database URL that is also in
Secrets Manager.

**D8. The cost model learns two lifetimes and a proxy.** The control plane by
the cluster-hour, the nodes by the instance-hour times `node_count`, both from
the Price List API like every other rate; the node group's lifetime stands in
for the instances' as the service's does for Fargate tasks. Kubernetes objects
and the Helm release are named as not metered, with the sentence that the
balancer the controller builds is billable and enters no event stream. Sizing
reads a node-group shape beside the task shape and refuses an environment
that declares neither.

**D9. In the cycle, beside promote.** (Slice three.) A `lab` job after a green
stage, in parallel with `promote`, both taking the digests stage tested; its
own destroy; api contract and smoke against the Ingress hostname. Wall-clock
barely moves; the cost is the cluster's hour.

**D10. The board draws the cluster and two service roles now, and the
application through kubectl later.** (Slice four for the second half.) *EKS
cluster* holds the control plane, the nodes, the OIDC provider, the roles the
cluster and the nodes assume, and the platform Terraform put inside;
*Kubernetes — api* and *— worker* hold the IRSA roles and their policies, the
way the ECS tiles hold task roles. The Deployments are not Terraform's and are
not counted; they are observed, with the Ingress and its balancer, by a
`kubectl` read beside `observe-environment.sh`.

## Consequences

- Slice one, 2026-09-13: `terraform validate` on all nine levels; checkov 501
  passed after D7; every checkout gate green over a topology of 9 levels and
  200 blocks; sizing reads the lab as `node_count 2, t3.small`; the rate table
  carries `eks_cluster_hour` ($0.10) and `ec2_instance_hour` ($0.0208) from
  the Price List API. **Not yet applied anywhere**: the lab deploy role plans
  2 to add on `bootstrap-oidc`, and the lab itself has never been created.
- Slice two, 2026-09-13, by hand under `demo-admin`: the cluster ACTIVE in
  9m24s, the node group in 1m47s, RDS in 4m53s, the controller in 22s; the
  chart's two hooks and three pods up on the first install; the balancer
  built by the controller with `Project` and `Environment` on it and on both
  target groups, visible to the tagging API; 54 api contract tests and 2
  smoke green through the Ingress, the worker consuming through IRSA (ten
  `processed` lines in its log). Three findings on the way, all in the
  configuration now: the secret read raced the RDS create; an access entry
  wants the SSO role's full ARN; the creator must not be given a second one.
  Teardown: `helm uninstall` and the balancer gone in 38 s; `terraform
  destroy` 38 resources in 11m53s, the node group 8m10s of it and the
  internet gateway waiting 6m44s on the nodes' interfaces - the lab's
  teardown is a node-group teardown. Afterwards the account holds the lab's
  deploy role and nothing else of the lab.
- Slice three, 2026-09-13, written and not yet run: the `lab` job beside
  `promote` in `self-service.yml` (its own deploy role by name, the watcher,
  the apply, `lab-install.sh`, api contract and smoke against the Ingress,
  the observation, the timeline, the results, the publish) and `destroy-lab`
  after it; `destroy.yml` uninstalls the chart and waits for the balancer
  before the destroy when the environment is the lab, skips the ECS-only
  balancer step, scopes the EKS check to the environment and checks for
  instances tagged with it. The sweep confirms clusters, node groups,
  instances, launch templates and OIDC providers; the adoption map knows the
  lab's five roles with their policies, the cluster, the node group and the
  provider, and its drift gates now read every environment's modules. The
  observation carries an `eks` block - cluster, node group, and the
  Deployments through kubectl - and counts the cluster as the lab's runtime.
  Three cycles were the proof: #27 fell at the publish role's trust (`lab`
  added to `publish_environments`), and its stage and prod sweeps went red
  asking their roles about the lab's five names (`unindexed_names` is per
  environment now); #28 fell at the node group - EKS validates its
  service-linked role with the caller's `iam:GetRole` (a read on the two EKS
  service-linked roles); **#29 (34777285974) ran the lab end to end in CI**:
  apply 1146 s, chart 148 s, api contract 16 s and smoke 30 s through the
  Ingress, the observation with `eks: cluster ACTIVE 1.35, node group ACTIVE
  2 × t3.small, deployments api 1/1 · web 1/1 · worker 1/1`, timeline and
  node states published; the teardown - uninstall, the balancer gone,
  `Destroy complete! 40 destroyed`, *no billable lab resources remain*, the
  sweep `clean` - in 13 minutes; the cost fold priced the lab at
  $0.040..$0.076 for a 36-minute life. The one red step was the results fold
  refusing a suite result for `lab` over a map that had no `suite.api.lab`,
  which is slice four.
- Slice four, 2026-09-13: the map gains `Apply — lab`, `Install — lab` (the
  chart with its hooks) and `Quality gate — lab` (api contract, smoke), and
  `Destroy` a `lab — everything above` node bound to `destroy-lab`; the page
  lists three environments everywhere it listed two, the lab's panel shows
  the cluster, the node group and the Deployments in place of three services,
  and the run layer reads the lab's documents. Every fixture family carries
  the lab's documents, synthesised from cycle #29's own with the clock
  shifted; the in-flight gate's *figures dated* claim learned that "the cycle
  that ended" over a destroyed environment at rest is true rather than
  premature. The teardown uninstalls the chart before the revocation and the
  sweep, so neither meets the controller's objects; the sweep confirms
  access entries and listener rules.
- **Verified by cycle #30 (34780714051, 2026-09-13, 63 minutes, every job
  green)** - the first green cycle with three environments: launch 18 m,
  lab 20 m beside promote 13 m (apply 963 s, chart 171 s, api contract 23 s
  and smoke 28 s through the Ingress, the results fold landing on
  `suite.api.lab` and `suite.smoke.lab`), destroy 11 m, destroy-lab 13 m
  (the balancer gone before the destroy, the join carrying `destroy.lab` at
  684 s), hold, destroy-prod 13 m, release-lock. Three status files say
  `destroyed` and name #30; the lab's cost fold closed its cycle at
  $0.043..$0.073 for 33 minutes; the account afterwards holds the default
  VPC, the permanent levels and nothing of any environment.
- Three lists of service names became four with the IRSA roles; plan item 5.
