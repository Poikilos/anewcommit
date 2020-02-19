# linux-minetest-kit config
This configuration directory is for use with
[anewcommit](https://github.com/poikilos/anewcommit).


## Mirroring Minetest
190204 has only one changelog entry, so it is fine for use as the
first commit. It is at http://git.minetest.org/minetest/minetest and
is not a fork, so leaving out upstream_repo is best, so that a new
mirror repo is created.

### Sub-projects
#### Sqlite3
- "upstream_repo" in "subsnaps/mtsrc/sqlite3.json" was obtained via
  `git config --get remote.origin.url`
- "upstream_commit" in "subsnaps/mtsrc/sqlite3.json" was obtained via
  `git rev-parse HEAD | cut -c 1-8`


## Tasks
- [ ] generate a single file from each entry in
  https://minetest.org/changes.html
  - Account for missing snapshots (collect all change entries and put
    them in the next snapshot).
