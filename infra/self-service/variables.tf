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
  description = "Hard TTL for a self-service environment, in minutes (ADR-0035 guardrail 3). 90 is the decided number, not a placeholder: it bounds exposure to duration x rate, against the $0.09 and $0.17 cycles already measured. The launch workflow's own timeout MUST stay strictly below it."
  type        = number
  default     = 90
}

variable "daily_cap" {
  description = "How many public launches a UTC day may start (ADR-0035 guardrail 2). Three, giving ~$0.30/day worst case."
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
  description = "Reserved concurrency on the launch function. Bounds what an unauthenticated endpoint can cost BY ITSELF, independently of every guardrail in ADR-0035, and is the only control here that does not depend on the store being readable."
  type        = number
  default     = 2
}

variable "allowed_origin" {
  description = "The dashboard origin permitted to call the Function URL from a browser. CORS is not a security control - it is what keeps an unrelated page from using this endpoint as its own."
  type        = string
  default     = "https://demo.uveapp.net"
}

variable "stage_environment" {
  description = "The ONLY environment the public path may create. Not an input to the workflow: the launch workflow resolves the stage deploy role and declares no prod environment, so no value produces a prod credential (ADR-0034)."
  type        = string
  default     = "stage"
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
