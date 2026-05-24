# Integrations

Optional external-service integrations. The framework boots without
any of them; deployments opt in per service.

## Google Drive (CoS file upload + share)

Lets ChiefOfStaff upload deliverables to Google Drive and send a
share link in an outbound message, rather than attaching files
inline. Particularly useful for large files, ongoing-collaboration
docs, and anything the recipient may want to access more than once.

### Setup

1. **Create a Google Cloud project** with the Drive API enabled.
   ([console.cloud.google.com](https://console.cloud.google.com))

2. **Create OAuth credentials** (OAuth 2.0 Client ID → "Desktop
   app"). Download the `client_secret.json`.

3. **Install Python deps** in the deployment's venv:
   ```bash
   pip install google-api-python-client google-auth google-auth-oauthlib
   ```

4. **Run the setup flow:**
   ```bash
   agency integrations google-drive setup \
       --profile <your-cos-id> \
       --client-secret /path/to/client_secret.json
   ```
   A browser opens for OAuth consent. After consent, the refresh
   token is saved at
   `~/.agency/profiles/<cos-id>/credentials/google_drive_token.json`
   (file mode `0600` — protect it).

5. **Restart any CoS cron jobs** that should pick up the new
   capability.

### Usage from a CoS skill

```python
from _framework.integrations.google_drive import upload_and_share

result = upload_and_share(
    profile="loriah",  # whatever your CoS profile id is
    file_path="/tmp/ha/deliverables/q3-report.pdf",
    share_with=["client@example.com"],
    role="reader",  # or "writer" / "commenter"
)
print(result.web_view_link)
# https://drive.google.com/file/d/.../view?usp=drivesdk
```

The function returns a `DriveUploadResult` with `file_id`, `name`,
`web_view_link`, and the list of recipients the file was actually
shared with.

### When to use it

- Outbound emails where the deliverable is large enough that an
  attachment is rude (or rejected by the recipient's MTA).
- Ongoing documents the recipient may want to revisit.
- Client work where you'd like to be notified when they view it.

### When NOT to use it

- Quick text snippets — paste in the body.
- Anything sensitive that shouldn't have a shareable link
  (compromised links leak silently).
- Replacements for proper version control (Drive is not git).

### Audit + access control

- Token file is profile-local. Only the profile with the token can
  upload from that account.
- Recipients are recorded in the upload result; CoS may log them
  to the kanban task for audit trail.
- The integration honors the agency-wide blacklist via the
  send-guard's recipient check before sharing (planned for v0.3).

### Failure modes

- **Token expired** — refresh token auto-refreshes; if Google has
  revoked it (security event, manual revoke), re-run `setup`.
- **Drive API quota exceeded** — surfaces as a RuntimeError; CoS
  falls back to inline attachment.
- **Recipient bounce** — the email-send is downstream of upload;
  even if share notification fails, the upload itself remains valid
  (we send share notifications with `sendNotificationEmail=False`
  by default; CoS writes the share link into the outbound message
  body herself).

---

## Future integrations (v0.3+)

- **Google Calendar** (read/write, two-way sync)
- **Gmail API** (alternative transport — Himalaya/IMAP remains the
  default per spec)
- **Signal / Slack ingress** (CoS triage normalization)
- **Generic OAuth-2 helper** so deployments can add their own
  integrations against the same setup-flow pattern

The pattern is consistent across integrations: profile-local
credentials, optional Python deps, lazy-imported runtime client,
friendly error messages when not configured.
