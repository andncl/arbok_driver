"""Module testing the Program class"""
import pytest

def test_add_sequence(mock_program, dummy_sequence):
    assert len(mock_program.sequences) == 0
    mock_program.add_sequence(dummy_sequence)
    assert len(mock_program.sequences) == 1
    assert mock_program.sequences[0] == dummy_sequence