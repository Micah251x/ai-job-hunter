# Field mapping

How each source's API response maps onto the `Job` model.

## Lever

API: `https://api.lever.co/v0/postings/{company}?mode=json`

| Job field | Lever source | Transformation |
|---|---|---|
| source | none (not in the JSON) | Always `JobSource.LEVER`; this adapter only handles Lever jobs |
| company | not in the JSON; the `{company}` part of the url | Passed into the adapter as a slug; model lowercases it |
| source_job_id | `id` | None |
| title | `text` | None |
| url | `hostedUrl` | None |
| location_raw | `categories.allLocations` (fallback `categories.location`) | Join the list into one string with `"; "` |
| remote_status | `workplaceType` | Lookup table (see Decisions) |
| description | `descriptionPlain` + `lists` (each section's `text` heading + `content` bullets) + `additionalPlain` | Combine in that order; strip HTML tags from the `lists` bullets |
| salary_min / salary_max / salary_currency | `salaryRange` | Map min / max / currency if present, otherwise `None` |
| posted_at | `createdAt` | Epoch milliseconds → divide by 1000 → aware datetime in UTC |

## Decisions

- **remote_status:** trust `workplaceType` over `categories.location`, because it’s a fixed-choice field Lever built for this (remote / hybrid / on-site), while location is free text a recruiter types and can say anything.

  | Lever `workplaceType` | `RemoteStatus` |
  |---|---|
  | `"remote"` | `REMOTE` |
  | `"hybrid"` | `HYBRID` |
  | `"on-site"` | `ONSITE` |
  | anything else or missing | `UNKNOWN` |

  The adapter records what the posting says. Whether I want the job is decided by the deterministic filter.

- **description:** `descriptionPlain` alone is only the intro paragraph. The requirements are in lists, and compensation is in additionalPlain.

- **salary:** `salaryRange` was empty in every sample. Some companies (e.g. Minted) put salary in free text instead. I don't parse it because every company formats it differently (Minted has three geographic tiers). The LLM still sees it because `additionalPlain` is included in the description, and the LLM reads the full description.

- **Not mapped:** `categories.commitment` (e.g. "Seasonal"). No `Job` field for it; the title filter covers it for now.
