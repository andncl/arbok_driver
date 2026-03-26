import types
import sys
import pytest

from arbok_driver.ekans import Ekans


def create_module(name: str, attrs: dict) -> types.ModuleType:
    parts = name.split(".")
    
    # Create parent packages
    for i in range(1, len(parts)):
        parent_name = ".".join(parts[:i])
        if parent_name not in sys.modules:
            parent_module = types.ModuleType(parent_name)
            parent_module.__path__ = []  # mark as package
            sys.modules[parent_name] = parent_module

    # Create the actual module
    module = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(module, k, v)

    # If it's meant to be a package, caller can overwrite __path__
    sys.modules[name] = module

    return module


def test_flattening_and_root_stripping():
    root = create_module("pkg.devices.nova", {})
    root.__path__ = []  # mark as package

    subpkg = create_module("pkg.devices.nova.spin_init", {})
    subpkg.__path__ = []

    leaf = create_module(
        "pkg.devices.nova.spin_init.config_a",
        {
            "__all__": ["conf_a"],
            "conf_a": 123,
        },
    )

    ekans = Ekans(root)

    assert hasattr(ekans, "spin_init")
    assert hasattr(ekans.spin_init, "conf_a")
    assert ekans.spin_init.conf_a == 123

    # ensure no redundant prefix
    assert not hasattr(ekans, "devices")
    assert not hasattr(ekans, "nova")


def test_multiple_leaf_modules_flattened():
    root = create_module("pkg.devices.nova2", {})
    root.__path__ = []

    subpkg = create_module("pkg.devices.nova2.spin_init", {})
    subpkg.__path__ = []

    create_module(
        "pkg.devices.nova2.spin_init.mod1",
        {"__all__": ["a"], "a": 1},
    )
    create_module(
        "pkg.devices.nova2.spin_init.mod2",
        {"__all__": ["b"], "b": 2},
    )

    ekans = Ekans(root)

    assert ekans.spin_init.a == 1
    assert ekans.spin_init.b == 2


def test_respects___all__():
    root = create_module("pkg.devices.nova3", {})
    root.__path__ = []

    subpkg = create_module("pkg.devices.nova3.spin_init", {})
    subpkg.__path__ = []

    create_module(
        "pkg.devices.nova3.spin_init.mod",
        {
            "__all__": ["visible"],
            "visible": 1,
            "hidden": 2,
        },
    )

    ekans = Ekans(root)

    assert hasattr(ekans.spin_init, "visible")
    assert not hasattr(ekans.spin_init, "hidden")


def test_no___all___falls_back_to_public():
    root = create_module("pkg.devices.nova4", {})
    root.__path__ = []

    subpkg = create_module("pkg.devices.nova4.spin_init", {})
    subpkg.__path__ = []

    create_module(
        "pkg.devices.nova4.spin_init.mod",
        {
            "a": 1,
            "_private": 2,
        },
    )

    ekans = Ekans(root)

    assert hasattr(ekans.spin_init, "a")
    assert not hasattr(ekans.spin_init, "_private")


def test_reload_updates_objects():
    root = create_module("pkg.devices.nova5", {})
    root.__path__ = []

    subpkg = create_module("pkg.devices.nova5.spin_init", {})
    subpkg.__path__ = []

    module_name = "pkg.devices.nova5.spin_init.mod"
    module = create_module(
        module_name,
        {"__all__": ["value"], "value": 1},
    )

    ekans = Ekans(root)
    assert ekans.spin_init.value == 1

    # simulate change
    module.value = 42

    ekans.reload_modules()

    assert ekans.spin_init.value == 42


def test_collision_raises_error():
    root = create_module("pkg.devices.nova6", {})
    root.__path__ = []

    subpkg = create_module("pkg.devices.nova6.spin_init", {})
    subpkg.__path__ = []

    create_module(
        "pkg.devices.nova6.spin_init.mod1",
        {"__all__": ["dup"], "dup": 1},
    )
    create_module(
        "pkg.devices.nova6.spin_init.mod2",
        {"__all__": ["dup"], "dup": 2},
    )

    with pytest.raises(ValueError):
        Ekans(root)


def test_deep_hierarchy_flattening():
    root = create_module("pkg.devices.nova7", {})
    root.__path__ = []

    lvl1 = create_module("pkg.devices.nova7.a", {})
    lvl1.__path__ = []

    lvl2 = create_module("pkg.devices.nova7.a.b", {})
    lvl2.__path__ = []

    create_module(
        "pkg.devices.nova7.a.b.mod",
        {"__all__": ["x"], "x": 99},
    )

    ekans = Ekans(root)

    assert ekans.a.b.x == 99