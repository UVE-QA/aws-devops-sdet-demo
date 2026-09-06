variable "region" {
  description = "AWS region for the endpoint, its control store and both Lambdas. The same region as everything else in this account."
  type        = string
  default     = "us-west-2"
}

variable "owner" {
  description = "Owner tag value for all resources. MUST match the other levels: the Owner tag is what every cost query filters on, and one level spelling it differently silently drops out of all of them."
  type        = string
}

variable "github_owner" {
  description = "GitHub org/owner that owns the repository the button dispatches into."
  type        = string
  default     = "UVE-QA"
}

variable "github_repo" {
  description = "GitHub repository the button dispatches into."
  type        = string
  default     = "aws-devops-sdet-demo"
}

variable "github_app_installation_id" {
  description = "Installation id of the GitHub App on the repository. An identifier, not a credential - the private key is pasted by hand into the Secrets Manager secret this level creates (ADR-0034). Empty until the App exists, which is a 19b step."
  type        = string
  default     = ""
}

variable "github_app_id" {
  description = "The GitHub App's numeric id. Also an identifier, for the same reason."
  type        = string
  default     = ""
}

variable "ttl_minutes" {
  description = <<-EOT
    Hard TTL for a self-service environment, in minutes (ADR-0035 guardrail 3).
    It bounds exposure to duration x rate, and the launch workflow's own job
    timeouts MUST stay strictly below it: a hung run has to reach its own
    teardown before the deadline it is being held to.

    90 -> 150 for ADR-0068. The cycle stopped being one deploy and became five
    phases, and the two numbers are coupled or the guarantee is not one:

      launch        45   stage apply, migrate, seed, four suites
      promote       ~30  prod apply, ECS stability, public HTTPS, prod smoke
      destroy        30  stage teardown
      hold           15  the five-minute countdown, with room to publish it
      destroy-prod   30  prod teardown, adoption and CLI verification
                    ---
                    150  and the TTL may not be under the sum

    150 minutes of a $0.051/h prod plus a $0.043/h stage is under $0.15 in the
    worst case, against three launches a day. The bound that matters is still
    the daily cap, not this.

    IT IS LOAD-BEARING IN A SECOND DIRECTION, and ADR-0068 moved it knowing only
    the first. This is also the CEILING ON HOW LONG A STRANDED LOCK KEEPS THE
    BUTTON SHUT: a run that dies before producing any job cannot release the
    lock, and `lock_is_expired()` only lets the next press take over once this
    deadline passes. Raising 90 -> 150 therefore lengthened that window by an
    hour, for a reason that had nothing to do with it (ADR-0069).

    So the number is squeezed from both sides: it must EXCEED the sum of the job
    timeouts or the watchdog tears down a cycle still working, and every minute
    above that sum is a minute the public path can be shut for nothing. 150 is
    the sum exactly, which is the smallest value the first constraint allows.
  EOT
  type        = number
  default     = 150

  validation {
    # The in-band half of guardrail 3 is that the workflow finishes before the
    # deadline it is held to. If this drops below the sum of the job timeouts,
    # the watchdog starts tearing down environments while their own cycle is
    # still working on them - which is the race the ordering exists to avoid.
    condition     = var.ttl_minutes >= 150
    error_message = "ttl_minutes must be at least the sum of self-service.yml's job timeouts (150). Lower it only by lowering those first."
  }
}

variable "quota_timezone" {
  description = <<-EOT
    The IANA zone the daily cap is counted in (ADR-0072). The counter was keyed
    by UTC date, which made the reset the same instant everywhere - and that
    instant was 17:00 local, the middle of the working day, so the window nobody
    could see the edge of reset while people were using it.

    ONE NAMED ZONE, not the visitor's: the counter is a single shared item, and a
    reset that followed whoever was looking would empty at a different moment for
    each of them.

    NAMED, not an offset. America/Los_Angeles is UTC-7 in summer and UTC-8 in
    winter; a reset pinned to an hour of UTC would be an hour wrong for half the
    year, in the direction nobody checks.
  EOT
  type        = string
  default     = "America/Los_Angeles"
}

variable "daily_cap" {
  description = "How many public launches a day may start (ADR-0035 guardrail 2). Three, giving ~$0.30/day worst case. A DAY IN var.quota_timezone, not in UTC, since ADR-0072 - the two are the same length and start seven or eight hours apart."
  type        = number
  default     = 3
}

variable "lock_grace_minutes" {
  description = "How long after a lock expires the watchdog waits for the dispatched destroy to work before taking the blunt path. Short, because by this point the in-band promise has already failed."
  type        = number
  default     = 15
}

variable "watchdog_interval_minutes" {
  description = "How often EventBridge Scheduler runs the watchdog. Its failure domain is deliberately NOT GitHub Actions (ADR-0035 guardrail 5)."
  type        = number
  default     = 5
}

variable "nonce_ttl_seconds" {
  description = "How long an issued nonce stays redeemable. A speed bump against a scripted loop, not authorization (ADR-0034) - whoever can read the page can get one."
  type        = number
  default     = 300
}

variable "reserved_concurrency" {
  description = "Reserved concurrency on the launch function. It was decided as 2 (ADR-0034) to bound what an unauthenticated endpoint can cost BY ITSELF, independently of every guardrail in ADR-0035 and of the store being readable. It is -1 (no reservation) because AWS REFUSES any reservation while this account's Lambda `Concurrent executions` quota is 10: a reservation may not take the unreserved pool below 10, and 10 is all there is. Found by applying, in Phase 19b - no static check can see it. While the quota stays at 10 the ACCOUNT is the bound: an account-wide ceiling of 10 concurrent executions, which is weaker per function and stronger in that nothing inside the account can raise it. Set this to 2 once the quota is raised, and see terraform.tfvars.example."
  type        = number
  default     = -1
}

variable "internal_reserved_concurrency" {
  description = "Reserved concurrency on the watchdog and the kill switch. Decided as 1, and for a different reason than the launch function: single-flight, not spend. Two watchdogs would each read the other's half-finished teardown; a flag that is already set needs no second writer. Same account quota, same -1, and the exposure is smaller than it looks - the watchdog's 120s timeout is well under its 300s interval, so an overlap needs a FAILED invocation that EventBridge Scheduler then retries."
  type        = number
  default     = -1
}

variable "allowed_origin" {
  description = "The dashboard origin permitted to call the Function URL from a browser. CORS is not a security control - it is what keeps an unrelated page from using this endpoint as its own."
  type        = string
  default     = "https://demo.uveapp.net"
}

variable "stage_environment" {
  description = "The environment the public path creates FIRST, and the one the watchdog names in its dispatched teardown. No longer the only one it may create: ADR-0068 added the promotion, so the sentence that used to be here - 'no value produces a prod credential' - is false and is corrected in that ADR rather than repeated here."
  type        = string
  default     = "stage"
}

variable "watched_environments" {
  description = <<-EOT
    Every environment the watchdog's blunt path may delete from, matched on the
    `Environment` tag AND a non-empty `Launch` tag.

    This was `stage` alone, hardcoded, and ADR-0035 could say prod was
    "unreachable from this function by policy". ADR-0068 made the public path
    deploy prod, and a net scoped to stage while the cycle creates prod is not a
    narrower guarantee - it is an absent one. A run that dies after the promotion
    would leave prod up with nothing able to remove it.

    It is a LIST rather than a second string so that adding an environment is one
    edit in one place. It is not `["*"]` and must not become one: the whole force
    of this policy is that it names what it may touch.
  EOT
  type        = list(string)
  default     = ["stage", "prod"]

  validation {
    # A watchdog that may delete anything tagged with this project, in any
    # environment, is a blunt instrument with no edge left. The Launch tag still
    # protects the owner's own cycles, but that is one condition holding the
    # whole line, and a wildcard here would make it the only one.
    condition     = !contains(var.watched_environments, "*")
    error_message = "watched_environments names environments; a wildcard would leave the Launch tag as the only condition."
  }
}

variable "launch_workflow_file" {
  description = "Workflow file the launch Lambda dispatches."
  type        = string
  default     = "self-service.yml"
}

variable "destroy_workflow_file" {
  description = "Workflow file the watchdog dispatches before it considers the blunt path."
  type        = string
  default     = "destroy.yml"
}

variable "log_retention_days" {
  description = "CloudWatch retention for both Lambdas. Long enough that a refusal can still be read the next day, short enough to stay in cents."
  type        = number
  default     = 14
}
