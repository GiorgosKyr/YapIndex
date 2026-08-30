---
title: Laptop setup for engineers (macOS)
category: onboarding
author: Priya Ramanathan
team: Platform
created: 2023-07-14
updated: 2026-03-11
status: current
version: 5.0
---

# Laptop setup

This is the "run these commands and you'll be able to build the services"
doc. macOS only. If you're on Linux (a couple of people are), the shape
is the same — swap `brew` for your package manager.

Rough time: 45–90 min end-to-end.

## 0. Prereqs

- FileVault on
- 1Password installed and signed in
- Command Line Tools for Xcode:

  ```bash
  xcode-select --install
  ```

## 1. Homebrew + our Brewfile

Install Homebrew if you don't have it:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then clone the eng-tools repo and run the bundle:

```bash
mkdir -p ~/src/meridian && cd ~/src/meridian
git clone git@github.com:meridian-data/eng-tools.git
cd eng-tools
brew bundle --file=./Brewfile
```

That gives you: `git`, `gh`, `jq`, `yq`, `git-lfs`, `pre-commit`, `direnv`,
`asdf`, `awscli`, `aws-vault`, `kubectl`, `kubectx`, `helm`, `argocd`,
`terraform` (1.7 pinned), `k9s`, `stern`, `postgresql-client@15`,
`redis`, `nodejs`, `pnpm`, `go`, `python@3.11`.

## 2. asdf for language versions

We use asdf so everyone runs the same runtimes.

```bash
asdf plugin add python
asdf plugin add nodejs
asdf plugin add golang
cd ~/src/meridian
# most repos have a .tool-versions committed
asdf install
```

## 3. AWS access via aws-vault + SSO

Do **not** put long-lived IAM keys on your laptop. We use AWS SSO through
Okta and `aws-vault` for keychain-backed session credentials.

```bash
aws configure sso --profile meridian-dev
# SSO start URL: https://meridian.awsapps.com/start
# region: us-west-2
```

Once you can `aws sso login --profile meridian-dev`, wrap it:

```bash
aws-vault exec meridian-dev -- aws sts get-caller-identity
```

Profiles you should end up with: `meridian-dev`, `meridian-staging`,
`meridian-sandbox`. Prod access (`meridian-prod`) is granted per-team
after week 2, via a `SEC-xxxx` ticket.

> Note: an older version of this doc referenced installing `awscli v1`
> via `pip install awscli`. Ignore that. **Use v2 from brew (`awscli`)**;
> everything below assumes v2. (There is one script in `eng-tools/legacy/`
> that still assumes v1 output format — flagged in that dir's README.)

## 4. kubectl + our clusters

Get the shared kubeconfig:

```bash
cd ~/src/meridian/eng-tools
./scripts/write-kubeconfig.sh
# writes ~/.kube/config with contexts:
#   meridian-dev, meridian-staging, meridian-prod
```

Switch with `kubectx`. Prod context is protected — `kubectl` there will
prompt for an aws-vault MFA touch.

Smoke test:

```bash
kubectx meridian-dev
kubectl get ns
```

## 5. ArgoCD CLI

You'll mostly use the UI (`https://argocd.mrdn.io`), but the CLI helps
for scripting:

```bash
argocd login argocd.mrdn.io --sso
argocd app list
```

## 6. Docker / container runtime

We use Colima on M-series (Docker Desktop's licensing was more hassle
than it was worth). Already in the Brewfile.

```bash
colima start --cpu 4 --memory 8 --disk 60
```

Test with `docker run --rm hello-world`.

## 7. Repo-level setup

For most services:

```bash
cd ~/src/meridian
git clone git@github.com:meridian-data/<service>.git
cd <service>
direnv allow
make setup
make test
```

`make setup` should get you a working local dev loop. If it doesn't,
that's a bug — please open a `ENG-xxxx` ticket against the owning team.

## 8. Editor / IDE

Whatever you want. Popular internal choices: Cursor, VS Code, Goland,
PyCharm, Neovim. We keep a shared `.editorconfig` in every repo.

## 9. VPN

We don't run a corporate VPN. Access to internal services is via Okta +
Cloudflare Access on `*.mrdn.io`. If a service is genuinely inside the
VPC and needs `kubectl port-forward`, that's a separate ask through
`#platform`.

## Done?

You should now be able to:

- `aws-vault exec meridian-dev -- aws s3 ls`
- `kubectl -n default get pods` in dev
- Clone a service, `make test`, and see green
- `argocd app list`

If any of those fail, please post in `#it-help` with the exact error.
