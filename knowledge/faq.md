# Support knowledge base

Answers the support assistant may use when helping a customer. Keep entries short and
factual. This file is served over MCP as `file://faq` and folded into the agent's system
prompt.

## Account status

- An account is **active** or **inactive**. Only active accounts can open support tickets.
- Inactive accounts must be reactivated by the account-support team; the assistant cannot
  do this. Direct the customer to account support.
- Customers can see their own account record (name, email, status) but not other
  customers'.

## Tickets

- A ticket has a status of **open** or **closed**. New tickets start **open**.
- Only an administrator can change a ticket's status.
- A ticket needs a concrete description of the problem (5–1000 characters).
- Customers see only their own tickets. Administrators see everyone's.

## High-priority issues

These get escalated ahead of the normal queue:

- **Payment failure** — a charge was declined or double-charged.
- **Account locked** — the customer cannot sign in and it is not a forgotten password.
- **Security concern** — suspected unauthorized access, phishing, or data exposure.

For a security concern, advise the customer to change their password immediately and open a
ticket tagged as a security issue.

## Common questions

**"How long until my ticket is answered?"**
Normal-priority tickets are answered within two business days. High-priority issues (above)
are looked at the same business day.

**"Can I reopen a closed ticket?"**
Yes — an administrator can set it back to open. A customer should open a new ticket that
references the old one if they cannot reach an admin.

**"I forgot my password."**
Password resets are self-service from the sign-in page. If the reset email does not arrive
within 15 minutes, that is an "account locked" high-priority issue.

**"Why can't I create a ticket?"**
Almost always because the account is inactive. Check the account status first.
