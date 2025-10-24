resource "google_project_iam_binding" "project" {
  project = "serverless-ejguidon-dev"
  role    = "roles/editor"

  members = [
    "user:saididriss@gmail.com",
    "arnassalomlucas@gmail.com",
    "mathias.ballot974@gmail.com"
  ]
}

resource "google_project_iam_binding" "project" {
  project = "serverless-ejguidon-dev"
  role    = "roles/viewer"
  members = "jeremie@jjaouen.com"
}
