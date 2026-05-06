# Alex's config

Alex reads three files in this folder before each weekly run. Edit them so they describe your business.

| File | What it's for | When to update |
|------|---------------|----------------|
| `brand-voice.md` | How your business writes. Vocabulary, tone, things to avoid. Used to shape meta descriptions, draft outreach replies, and content brief language. | Once at setup. Revisit every 6 months. |
| `state.md` | What's happening right now in the business. What you're focusing on. Pages and topics that matter most. | Whenever priorities shift. |
| `system-prompt.md` | The Alex persona. How he approaches SEO and outreach. | Optional. Leave blank to use the default. |

## Credentials

Don't put your `gsc-credentials.json` in this folder for any repo you're going to push to GitHub. It's listed in `.gitignore`, but the safest pattern is:

- **For GitHub Actions runs (recommended):** Add the JSON as a repo secret called `GSC_CREDENTIALS_JSON`. Alex will use it directly without ever writing it to the repo.
- **For local runs only:** Place `gsc-credentials.json` in this folder. The `.gitignore` will keep it out of git.

See [SETUP.md](../SETUP.md) for the full GSC walkthrough.
