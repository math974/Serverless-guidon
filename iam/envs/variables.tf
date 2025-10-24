variable "project_id" {
  description = "GCP project id"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "team_member_emails" {
  description = "List of team member emails"
  type        = list(string)
  validation {
    condition     = length(var.team_member_emails) > 0
    error_message = "Provide at least one team member email."
  }
}

variable "team_role" {
  description = "IAM role granted to team members"
  type        = string
  default     = "roles/editor"
}

variable "instructor_email" {
  description = "Instructor email"
  type        = string
  validation {
    condition     = can(regex("^[_A-Za-z0-9-+.]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", var.instructor_email))
    error_message = "Provide a valid instructor email address."
  }
}

variable "instructor_role" {
  description = "Least-privilege role for instructor (viewer by default)"
  type        = string
  default     = "roles/viewer"
}

variable "enable_instructor_binding" {
  description = "Whether to create instructor IAM binding"
  type        = bool
  default     = true
}

variable "auto_invite_missing_users" {
  description = "If true, ensure IAM membership for all emails (acts as invite if not yet provisioned)."
  type        = bool
  default     = true
}

variable "billing_account_id" {
  description = "Billing account ID for IAM bindings"
  type        = string
  default     = "01A214-B000AA-9F1F38"
}