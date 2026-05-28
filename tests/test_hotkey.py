from translator_app.hotkey import DoubleCtrlCDetector


def test_double_ctrl_c_triggers_within_interval() -> None:
    detector = DoubleCtrlCDetector(max_interval_seconds=0.7)

    assert detector.register_key_press("c", True, 10.0) is False
    assert detector.register_key_press("c", True, 10.5) is True


def test_double_ctrl_c_does_not_trigger_after_interval() -> None:
    detector = DoubleCtrlCDetector(max_interval_seconds=0.7)

    assert detector.register_key_press("c", True, 10.0) is False
    assert detector.register_key_press("c", True, 11.0) is False


def test_non_ctrl_key_resets_sequence() -> None:
    detector = DoubleCtrlCDetector(max_interval_seconds=0.7)

    assert detector.register_key_press("c", True, 10.0) is False
    assert detector.register_key_press("x", True, 10.2) is False
    assert detector.register_key_press("c", True, 10.3) is False
