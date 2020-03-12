# anewcommit
https://github.com/poikilos/anewcommit

Commit a series of source snapshots (where each may also contain
snapshots of subprojects).


## Main Features
- Split into "subprojects" and commit to separate repositories where
  configuration specifies how.


## Configuration
Your subdirectory in conf.d can have the following files and
directories.

### project config
- If a modpack and in modpack_repos, that will override
  mod-repos.json--for example, 3d_armor.

#### settings.json
If settings.json is present in conf.d/<project>, the settings will
affect the entire snapshot process. For example:
```json
{
    "author_meta": {
        "OldCoder": {
            "github_email": "oldcoder@yahoo.com",
            "github_user": "OldCoder",
            "full_name": "Robert Kiraly",
            "github_website": "http://oldcoder.org/"
        }
    },
    "always_add_coauthors": ["OldCoder"]
}
```

### subproject configuration
Use a file such as "conf.d/<project>/subsnaps/[.../]<subproject>.json"
(where <project> is the project name of the set of snapshots and
<subproject> is the name of a directory or archive):
- The name can match a directory such as
  "<snapshot>/[.../]<subproject>/"
  - You can force the root of the subproject to be a certain archive
    in the directory (other files in the directory will be ignored) by
    setting something like "archive": "irrlicht-snappy.tar.bz2" in the
    json file.
- The name can match a file such as "<snapshot>/[.../]<subproject.*>"
  (where ".../" is any directory path, or blank; and <subproject.*>
  is an archive such as "irrlicht-1.8.4.zip")

The settings file must represent a json list, even if there is only one
subproject. The "archive" option must be present. For example:
```json
[
    {
        "upstream_repo": "https://github.com/LuaJIT/LuaJIT.git",
        "upstream_version": "git",
        "upstream_commit": "61464b0a5",
        "upstream_version_dt": "2019-01-12 19:16 ET",
        "archive": "luajit-git-61464b0a5.tar.bz2",
        "branch_readme": "luajit.url",
        "patch": "luajit.patch"
    },
    {
        "upstream_repo": "https://github.com/LuaJIT/LuaJIT.git",
        "upstream_version": "git",
        "upstream_commit": "288219fd6",
        "upstream_version_dt": "2019-01-12 20:42 ET",
        "archive": "luasocket-git-<upstream_commit>.tar.bz2",
        "ignore_subs": "luasocket-git-288219fd6.tar.bz2",
        "branch_readme": "luasocket.url",
        "patch": "luasocket.patch"
    },
]

```
- "upstream_version_dt": must be in the format "2019-01-20 01:03 ET"


## Tasks
- See also: `anewcommit/conf.d/linux-minetest-kit/readme.md`.
- [ ] Get git commits for versions of packages in
  `anewcommit/conf.d/linux-minetest-kit/subsnaps/mtsrc/gcc/suplib.json`.
- [ ] any variable can contain any other variable's value in "<>" signs
  (parse in 2 passes).
- [ ] Alternatively, allow "sub" instead of "archive" (if subpoject is
  not in an archive file)
- [ ] If the "ignore_subs" list contains the value of "archive",
  or "sub", the file is excluded, no subproject is generated, and all
  other files in the directory become part of the main project.
  - [ ] Test with solib64.tar.bz2 (which contains **only binaries** to
    ignore and which are only needed for the linux-minetest-kit
    install) in
    `anewcommit/conf.d/linux-minetest-kit/subsnaps/mtsrc/newline.json`.
- [ ] Deal with sub-sub projects (using separate JSON identical in
  format to a regular subproject).
- [ ] Warn on any files not in the subprojects settings.
  - [ ] Append them to the main project.
- [ ] Warn on any files not in the directory that are in the subproject
  settings.
- [ ] Do dry run first. Implement ANewCommitError.
  Stop on ANewCommitError.
- [ ] raise ANewCommitError on invalid JSON.
- [ ] raise ANewCommitError on empty JSON string
- [ ] automatically log when a subproject moves to a different part of
  the project, is removed, or is added (say "re-added" if re-added).
- Handle mod/modpack variables:
  - [ ] `upstream_git_url`
  - [ ] `upstream_git_subfolder`
  - [ ] `downstream_git_url`
  - [ ] `downstream_branch`

## Developer Notes
### Date formats
Python example:
```Python

```



