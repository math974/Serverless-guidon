resource "google_billing_account_iam_member" "instructor_billing_viewer" {
  count              = var.enable_instructor_binding ? 1 : 0
  billing_account_id = var.billing_account_id
  role               = "roles/billing.user"
  member             = "user:${var.instructor_email}"
}
