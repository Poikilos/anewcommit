#!/usr/bin/env python3


def extract(src_file, new_parent_dir, auto_sub=True,
            auto_sub_name=None):
    """
    Extract any known archive file type to a specified directory.

    Sequential arguments:
    src_file -- Extract this archive file.
    new_parent_dir -- Place the extracted files into this directory
        (after temp directory).

    Keyword arguments:
    auto_sub -- Automatically create a subdirectory only if there is
        more than one item directly under the root of the archive. If
        False, extract as-is to new_parent_dir (even if that results in
        a subdirectory that is the name of the original directory).
    auto_sub_name -- If auto_sub is true, rename the extracted or
        created directory to the value of this string.
    """
    raise NotImplementedError("There is nothing implemented here yet.")


def main():
    pass


if __name__ == "__main__":
    print("Import this module into your program to use it.")
    main()
