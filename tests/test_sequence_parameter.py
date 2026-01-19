
def test_sequence_parameter_call(measurement_parameter):
    assert measurement_parameter.qua_var == 'placeholder'
    # with pytest.raises(ValueError):
    #     seq_param((3,))