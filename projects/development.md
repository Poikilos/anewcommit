# Development
## Reconstruct FROM on TO
Reconstruct one action's path in the context of another action.

This logic is for:
- `on_left_click_sub` in gui_tkinter.py (examine sources or
  destinations)
- ANCProject's `generate_cache` in __init__.py (examine destinations)

### Example 1
Input:
```
from/a/b from/c/d
to/e/f to/g/h
#
# to_source = e/f
# try_from_src = a/b
# to_src_parts = [e, f]
# from_src_parts = [a, b]
#
# from_dst_parts = [c, d]
# to_dst_parts = [g, h]
#
# to_dst_subs = []
# from_dst_subs = []
#
```

Desired output:
- use os.path.join(from_src_parts[:1]+to_src_parts[-1:]) if exists

### Example 2
(wip)
Input:
```
from/source from/dest/sub
to/source/sub to/dest
#
# from_dst_subs = []
# to_dst_subs = [sub]
#
to to/dest
```
