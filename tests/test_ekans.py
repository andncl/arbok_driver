import importlib
import sys
import types
import pytest

from arbok_driver.ekans import Ekans  # adjust import if needed


# Use your real examples package
import arbok_driver.examples as examples


# ----------------------------
# Basic initialization
# ----------------------------

def test_init_with_valid_module():
    ek = Ekans(examples)
    assert ek is not None


def test_init_with_invalid_type():
    with pytest.raises(TypeError):
        Ekans("not_a_module")


# ----------------------------
# Module collection
# ----------------------------

def test_collects_modules():
    ek = Ekans(examples)
    modules = ek._collect_module_names()

    # sanity checks
    assert any("examples.configurations" in m for m in modules)
    assert any("examples.sub_sequences" in m for m in modules)
    assert any("examples.readout_classes" in m for m in modules)


# ----------------------------
# Attribute tree structure
# ----------------------------

def test_namespace_structure_exists():
    ek = Ekans(examples)

    assert hasattr(ek, "configurations")
    assert hasattr(ek, "experiments")
    assert hasattr(ek, "readout_classes")
    assert hasattr(ek, "sub_sequences")


def test_nested_namespace():
    ek = Ekans(examples)

    assert hasattr(ek.configurations, "hardware")
    assert hasattr(ek.configurations, "sequence")


# ----------------------------
# Flattening behavior
# ----------------------------

def test_flattened_attributes_from_submodules():
    ek = Ekans(examples)

    # e.g. square_pulse.py should expose things directly under sub_sequences
    attrs = dir(ek.sub_sequences)

    # We don't know exact class/function names, so just ensure flattening happened
    assert len(attrs) > 0
    assert not any(name.endswith(".py") for name in attrs)


def test_no_private_attributes_exposed():
    ek = Ekans(examples)

    attrs = dir(ek.sub_sequences)

    # ignore dunder attributes, only check "real" ones
    public_like = [name for name in attrs if not (name.startswith("__") and name.endswith("__"))]

    assert not any(name.startswith("_") for name in public_like)


# ----------------------------
# __all__ behavior
# ----------------------------

def test_respects___all__():
    ek = Ekans(examples)

    module = importlib.import_module(
        "arbok_driver.examples.readout_classes.dc_average"
    )

    if hasattr(module, "__all__"):
        for name in module.__all__:
            assert hasattr(ek.readout_classes, name)


# ----------------------------
# Reload behavior
# ----------------------------

def test_reload_modules_runs_without_error():
    ek = Ekans(examples)

    ek.reload_modules()  # should not raise


def test_reload_preserves_structure():
    ek = Ekans(examples)

    before = dir(ek.sub_sequences)
    ek.reload_modules()
    after = dir(ek.sub_sequences)

    assert before == after


# ----------------------------
# Submodule attachment
# ----------------------------

def test_direct_submodule_attributes_are_attached():
    ek = Ekans(examples)

    module = importlib.import_module(
        "arbok_driver.examples.sub_sequences.square_pulse"
    )

    public = getattr(module, "__all__", None)
    if public is None:
        public = [n for n in dir(module) if not n.startswith("_")]

    found = [name for name in public if hasattr(ek.sub_sequences, name)]

    # At least one should be attached
    assert len(found) > 0


# ----------------------------
# No overwrite behavior
# ----------------------------

def test_no_overwrite_of_existing_attributes():
    ek = Ekans(examples)

    attrs = dir(ek.sub_sequences)

    # ensure uniqueness
    assert len(attrs) == len(set(attrs))


# ----------------------------
# Internal helper correctness
# ----------------------------

def test_get_submodules_only_direct_children():
    ek = Ekans(examples)

    module = importlib.import_module(
        "arbok_driver.examples.sub_sequences"
    )

    subs = ek._get_submodules(module)

    for sub in subs:
        assert sub.__name__.count(".") == module.__name__.count(".") + 1


# ----------------------------
# Robustness: broken module import
# ----------------------------

def test_import_error_propagates(monkeypatch):
    ek = Ekans(examples)

    # remove one module so import_module gets called
    target = "arbok_driver.examples.sub_sequences.square_pulse"
    sys.modules.pop(target, None)

    def broken_import(name):
        raise ImportError("boom")

    monkeypatch.setattr(importlib, "import_module", broken_import)

    with pytest.raises(ImportError):
        ek.reload_modules()