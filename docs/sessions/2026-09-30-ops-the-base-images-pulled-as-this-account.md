# Ops — the base images, pulled as this account

**2026-09-28 to 2026-09-30**, on `next`, then `main` on the owner's word.

## What was found

*все работает?* - the live page yes, the three environments destroyed by
#38, `main` clean; and four dependabot PRs, three of them red since
dependabot rebased them on 2026-09-28. Not the updates: every red run died
in the image build, pulling `python` and `nginx` from ECR Public, on
`429 Too Many Requests - Data limit exceeded`. The anonymous limit is per IP
address and GitHub's runners share theirs. A rerun passed two of three and
failed the third on the same 429; the next day `local-ci` failed four tries
30/60/120 s apart while `image-scan` in the same run, on another runner,
built fine. It is a sustained cap on some addresses, not a window. A public
launch rebuilds on every new commit of `main`, so it was the button's risk
too.

## What was done

On the owner's *up to you, make all we need*, and two explicit yeses for
the part that widens IAM:

- the four dependabot branches merged into `next` - SQLAlchemy 2.1,
  uvicorn, alembic, psycopg2, boto3; the db tests' pair;
  `configure-aws-credentials` 6.3.0; Playwright 1.63.0;
- `iam_github_deploy_role` gained `PublicRegistryPull` -
  `ecr-public:GetAuthorizationToken` and `sts:GetServiceBearerToken` on the
  three deploy roles; the plan was shown - 0 to add, 3 to change, 0 to
  destroy, one statement in each policy - and applied; the statement read
  back from the stage role;
- the launch and deploy jobs sign in to ECR Public before building, with a
  warning and an anonymous pull if the sign-in fails;
- the build retries four times 30/60/120 s apart, in the script and in
  `make docker-build`.

The owner signed in to SSO from a phone: the device-code flow was started
on the devbox with the owner's *go*, the owner approved on the phone - the
portal's account list first, the device page on the second open.

The account, read directly while the session was up: no ECS service, EKS,
RDS, balancer, NAT, VPC, address or instance. What the tag index still
lists is free - two `INACTIVE` clusters, 147 `INACTIVE` task-definition
revisions, and one `ACTIVE` revision, `aws-devops-sdet-demo-stage-app:22`,
from before the services split.

## The proof

#39 from `next` at 15:44 UTC: `Login Succeeded`, *base images will be
pulled as this account*, three images built on the first attempt; green end
to end in 70 minutes with the dependabot updates on every runtime. CI on
`next` green after one rerun of `local-ci`.

## And CI

Merged to `main` on the owner's *да, вливай*; CI on `main` went red twice -
`image-scan` on the same anonymous 429, eight tries - and nothing else. The
owner's *yes* to a CI role: `aws-devops-sdet-demo-ci-pull` in
`infra/bootstrap-oidc`, the same two token reads, trusted by pushes to
`main` and `next` and by pull requests; the plan shown - 2 to add, 0 to
change, 0 to destroy - and applied on *go*; `CI_PULL_ROLE_ARN` set as a
repository variable. The first CI run with it: `Login Succeeded` in both
building jobs - and two things the anonymous failures had been hiding. The
map refused the role's two records, belonging to no display group; they
belong to the OIDC group now. And the image scan, pulling for the first
time in two days, found four HIGH OpenSSL findings in `web` with a fix
that `nginx:1.27-alpine`'s Alpine 3.21 does not carry yet; `1.28-alpine`
took them and kept five HIGH nginx CVEs that Alpine patches only in its
own package; the mainline `1.29-alpine` scans clean, and `web` is on it.
CI on `next` green on every job.

## What is still open

The web image changed, so a cycle from `next` proves it before `main`
gets it - on the owner's word. Whether dependabot's runs get an OIDC token
is unverified; if not, they pull anonymously with a warning. The old
`stage-app:22` revision could be deregistered; it costs nothing.
