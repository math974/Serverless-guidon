locals {
  unique_team_member_emails = distinct(var.team_member_emails)
}

resource "google_project_iam_member" "team_members" {
  for_each = var.auto_invite_missing_users ? {
    for email in local.unique_team_member_emails : email => email
  } : {}
  project = var.project_id
  role    = var.team_role
  member  = "user:${each.value}"
}

resource "google_project_iam_member" "instructor" {
  count   = var.enable_instructor_binding ? 1 : 0
  project = var.project_id
  role    = var.instructor_role
  member  = "user:${var.instructor_email}"
}
