#!/usr/bin/env python3


def extract(src_file, new_parent_dir, auto_sub=True,
            auto_sub_name=None):
    """
    Sequential arguments:
    src_file -- Extract this archive file.
    new_parent_dir -- Place the extracted files into this directory
        (after temp directory).

    Keyword arguments:
    auto_sub -- Automatically create a subdirectory
    """
    raise NotImplementedError("There is nothing implemented here yet.")


def main():
    pass


if __name__ == "__main__":
    print("Import this module into your program to use it.")
    main()
