def test_project_folder_exists():
    import os
    assert os.path.isdir("openunderstand")


def test_utils_folder_exists():
    import os
    assert os.path.isdir("openunderstand\\utils")