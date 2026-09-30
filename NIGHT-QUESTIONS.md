# Night questions, 2026-09-30, Group erase (branch group-erase-removed)

- `del group[a:b]`: main accepted slices, the first version of the branch broke
  that (`TypeError`). C raises NotImplementedError for slices. Chose to keep
  slice support, since dropping it would break code that works on Blinka today.
- `group[i] = x` skipped the type and "already in a group" checks that `insert`
  does. C's setitem runs those checks before removing anything. Chose to add
  them in this PR, since replacement is one of the removal paths it fixes; it is
  about 3 lines. Easy to split out if you would rather keep the PR narrower.
- Bounding the removed-area queue at 8 (merged into one area past that) is my
  pick for "small"; a removed layer costs one queued Area until the next refresh.
