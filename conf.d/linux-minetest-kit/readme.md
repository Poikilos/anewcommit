# linux-minetest-kit config
This configuration directory is for use with
[anewcommit](https://github.com/poikilos/anewcommit).

- "upstream_repo" in "subsnaps/mtsrc/sqlite3.json" was obtained via
  `git config --get remote.origin.url`
- "upstream_commit" in "subsnaps/mtsrc/sqlite3.json" was obtained via
  `git rev-parse HEAD | cut -c 1-8`
- [ ] generate a single file from each entry in
  https://minetest.org/changes.html
  - Account for missing snapshots (collect all change entries and put
    them in the next snapshot).
