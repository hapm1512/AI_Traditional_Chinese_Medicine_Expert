from tcm_expert.core.paths import AppPaths


def test_paths_create_required_directories(tmp_path):
    paths = AppPaths.discover(tmp_path / "app")
    paths.ensure()
    assert paths.data.is_dir()
    assert paths.logs.is_dir()

