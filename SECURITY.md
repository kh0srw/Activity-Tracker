# Security

The current Go implementation has no Telegram integration and contains no bot credentials.

A credential previously committed to a public Git repository should be treated as compromised even after the file is deleted or the repository is made private. Revoke/regenerate the old Telegram token in BotFather.

The tracker is local-first and binds its dashboard to `127.0.0.1` by default. Window titles may still contain sensitive information; protect the activity data directory accordingly.
