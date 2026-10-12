"""Provision one server-only enrollment secret without printing its contents.

Requires an authorized gcloud owner. No local secret file is written; no broad
Google user access is granted here. Existing secret/version is reused unchanged.
"""
import argparse
import secrets
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--gcloud", default="gcloud")
    args = parser.parse_args()
    secret = "friday-public-demo-enrollment"
    def cli(*parts, data=None, check=True):
        result = subprocess.run([args.gcloud, *parts, "--project=" + args.project, "--quiet"],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and result.returncode:
            raise RuntimeError("Secret provisioning command failed; no secret value was printed")
        return result
    exists = cli("secrets", "describe", secret, check=False)
    if exists.returncode:
        cli("secrets", "create", secret, "--replication-policy=automatic")
        cli("secrets", "versions", "add", secret, "--data-file=-", data=secrets.token_hex(32).encode())
    for identity in ("financial-friday-web", "financial-friday-runtime"):
        cli("secrets", "add-iam-policy-binding", secret,
            "--member=serviceAccount:" + identity + "@" + args.project + ".iam.gserviceaccount.com",
            "--role=roles/secretmanager.secretAccessor")
    print("Enrollment secret provisioned/reused; only web/runtime identities granted secret access. Values withheld.")


if __name__ == "__main__":
    main()
