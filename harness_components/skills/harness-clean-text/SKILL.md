---
name: harness-clean-text
description: Clean, normalize or inspect supplied text with traceable harness components, including conservative email handling and caller-supplied slang lexicons. Use when precise transformations and retained originals matter.
---

# Clean text with traceable transformations

Find the reviewed `harness_components` package in the user's workspace and run its CLI from the parent directory. Discover and inspect the particular operation before chaining transformations:

```bash
python3 -m harness_components search "normalize text" --kind function --limit 5
python3 -m harness_components get text.unicode_normalize
python3 -m harness_components run text.unicode_normalize --input '{"text":"e\u0301","form":"NFC"}'
python3 -m harness_components run text.email_normalize --input '{"email":"Case+tag@EXAMPLE.ORG"}'
```

Keep source text and transformed views separate. Preserve exact research prompts, recorded model inputs and source quotations; attach a derived view when matching or display needs normalization. Record the chosen component/version and transformation order.

Select the change needed by the task. `text.normalize_newlines` changes line endings; `text.collapse_whitespace` can remove line structure; `text.unicode_normalize` exposes NFC/NFD/NFKC/NFKD explicitly. Choose compatibility folding only when the task calls for losing those distinctions. Compute spans against the exact string being indexed, since normalization can change offsets.

`text.email_normalize` lowercases only a supported mailbox's DNS domain. Keep local-part case, dots and plus tags, and handle unsupported syntax through its returned status. It does not establish delivery.

Use `text.slang_lookup`, `text.slang_matches` or `text.expand_lexicon` with the caller's lexicon. Retain alternative meanings and original terms. Lexicon matches provide candidate interpretations; keep demographic inference and invented contextual certainty out of the transformation.

Check an unchanged control and a difficult input appropriate to the chosen operation. Read CLI output from `result`; retain the ID/version/hash separately. Report what changed, what was preserved and any unsupported inputs. Save transformed files only within the requested destination and scope.
