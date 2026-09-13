variable "name_prefix" {
  description = "Prefix for every name here, e.g. aws-devops-sdet-demo-stage."
  type        = string
}

variable "name" {
  description = "The queue's name after the prefix: `items` (api → worker) or `results` (worker → api), ADR-0098."
  type        = string
  default     = "items"
}

variable "visibility_timeout_seconds" {
  description = "How long a received message is hidden from other consumers. Longer than the worker's one UPDATE needs by a wide margin; short enough that a worker that dies mid-batch costs a redelivery, not an outage."
  type        = number
  default     = 30
}

variable "max_receive_count" {
  description = "Receipts before a message is moved to the dead-letter queue. Three: one for the failure, two to prove it was not the network."
  type        = number
  default     = 3
}
