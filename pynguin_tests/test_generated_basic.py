def test_generated_project_structure():
    import os
    assert os.path.isdir("openunderstand")
    assert os.path.isdir("openunderstand\\utils")