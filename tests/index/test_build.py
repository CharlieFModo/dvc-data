import pytest
from dvc_objects.fs.local import LocalFileSystem
from dvc_objects.fs.memory import MemoryFileSystem

from dvc_data.index.build import DataIndexEntry, build, build_entry


def test_build_entry(tmp_path):
    (tmp_path / "foo").write_bytes(b"foo\n")

    fs = LocalFileSystem()
    entry = build_entry(str(tmp_path / "foo"), fs)
    assert isinstance(entry, DataIndexEntry)

    assert entry.meta
    assert entry.meta.size == 4
    assert entry.key is None
    assert entry.hash_info is None

    with pytest.raises(FileNotFoundError):
        build_entry(str(tmp_path / "missing"), fs)


def test_build(tmp_path):
    (tmp_path / "foo").write_bytes(b"foo\n")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "bar").write_bytes(b"bar\n")
    (tmp_path / "data" / "baz").write_bytes(b"baz\n")

    fs = LocalFileSystem()
    index = build(str(tmp_path), fs)
    assert index[("foo",)].meta.size == 4
    assert index.storage_map.get_data(index[("foo",)]) == (
        fs,
        str(tmp_path / "foo"),
    )
    assert index[("data",)].meta.isdir
    assert index[("data", "bar")].meta.size == 4
    assert index.storage_map.get_data(index[("data", "bar")]) == (
        fs,
        str(tmp_path / "data" / "bar"),
    )
    assert index[("data", "baz")].meta.size == 4
    assert index.storage_map.get_data(index[("data", "baz")]) == (
        fs,
        str(tmp_path / "data" / "baz"),
    )


def test_build_object_store_uses_one_listing(mocker):
    fs = MemoryFileSystem(global_store=False)
    fs.pipe(
        {
            "/root/foo": b"foo\n",
            "/root/data/bar": b"bar\n",
            "/root/data/sub/baz": b"baz\n",
        }
    )
    walk = mocker.spy(fs.fs, "walk")
    find = mocker.spy(fs.fs, "find")

    index = build("/root", fs)

    assert find.call_count == 1
    assert walk.call_count == 0
    assert index[("foo",)].meta.size == 4
    assert index[("data",)].meta.isdir
    assert index[("data", "bar")].meta.size == 4
    assert index[("data", "sub")].meta.isdir
    assert index[("data", "sub", "baz")].meta.size == 4
    assert index.storage_map.get_data(index[("data", "sub", "baz")]) == (
        fs,
        "/root/data/sub/baz",
    )
