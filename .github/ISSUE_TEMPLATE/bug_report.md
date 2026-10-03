---
name: Bug report
about: Something in Attesta does not work as documented
labels: bug
---

**What happened**

A clear description of the wrong behavior.

**Steps to reproduce**

1. Go to ...
2. Upload / click ...
3. See error (paste the response body; errors use `{"error": {"code", "message", "details"}}`)

**Expected**

What the trust model or the docs say should happen instead.

**Environment**

- OS / browser:
- How you ran it (`./make check`, `./make demo-check`, dev servers):
- Was the local chain running (`./make chain`)?

**Trust-model impact (if any)**

Does this touch trust states, credential issue/verify/revoke, or the Integrity Agent? If yes, explain the wrong state transition.
