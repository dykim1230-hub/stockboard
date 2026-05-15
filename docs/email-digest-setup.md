# Email Digest Setup

## Required Environment Variables

Set these on the Render backend service.

| Name | Example | Purpose |
| --- | --- | --- |
| `FIREBASE_SERVICE_ACCOUNT` | `{...}` | Firebase Admin SDK service account JSON |
| `ADMIN_UIDS` | `uid1,uid2` | Admin user UID list |
| `RESEND_API_KEY` | `re_xxxxx` | Resend API key |
| `MAIL_FROM` | `MarketPulse <no-reply@ahdoyoon.site>` | Sender address verified in Resend |
| `CRON_SECRET` | random long string | Secret required by the digest cron endpoint |

## Render Cron Job

Create a Render Cron Job that runs every hour and calls the backend endpoint.

```bash
curl -sS -X POST "https://stockboard-fhh4.onrender.com/api/cron/digest" \
  -H "x-cron-secret: $CRON_SECRET"
```

The backend uses `Asia/Seoul` time. Each user receives one digest per day at the selected hour only.

## User Settings

The account modal stores settings in Firestore.

```js
users/{uid}.emailDigest = {
  enabled: true,
  hour: 8,
  timezone: "Asia/Seoul",
  maxNewsPerStock: 5,
  lastSentDate: "2026-05-14",
  lastSentAt: "...",
  lastError: null
}
```

## Duplicate Send Guard

The cron job skips a user when `emailDigest.lastSentDate` is already today's date in `Asia/Seoul`.

## Dry Run

Use `dry_run=true` to count eligible users without sending email.

```bash
curl -sS -X POST "https://stockboard-fhh4.onrender.com/api/cron/digest?dry_run=true" \
  -H "x-cron-secret: $CRON_SECRET"
```

Use `include_details=true` when diagnosing delivery issues. The response includes the current Asia/Seoul hour, Resend configuration presence, skip reason counts, and masked eligible recipients.

```bash
curl -sS -X POST "https://stockboard-fhh4.onrender.com/api/cron/digest?dry_run=true&include_details=true" \
  -H "x-cron-secret: $CRON_SECRET"
```

Common skip reasons:

| Reason | Meaning |
| --- | --- |
| `disabled` | User has not enabled email digest |
| `invalid_hour` | Saved hour is missing or outside 0-23 |
| `hour_mismatch` | User selected a different hour from the current Asia/Seoul hour |
| `already_sent_today` | Digest was already sent today |
| `missing_email` | User document/Auth record has no email |
| `missing_favorites` | User has no favorite stocks |
