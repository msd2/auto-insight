# Auth: the provider reads DIGITALOCEAN_TOKEN (or DIGITALOCEAN_ACCESS_TOKEN)
# from the environment — never put the token in files or state. Locally:
#   export DIGITALOCEAN_TOKEN=<personal access token, write scope>
# In CI the same token lives in the GitHub `staging` environment as the
# secret DIGITALOCEAN_ACCESS_TOKEN (the only GitHub-side secret this stack
# needs — see .github/workflows/deploy-staging.yml).
provider "digitalocean" {}
