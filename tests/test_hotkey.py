from translator_app.hotkey import CtrlCPollStateDetector, DoubleCtrlCDetector


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


def test_poll_detector_triggers_only_on_c_key_edges() -> None:
    detector = CtrlCPollStateDetector(DoubleCtrlCDetector(max_interval_seconds=0.7))

    assert detector.update(ctrl_down=True, c_down=True, now=10.0) is False
    assert detector.update(ctrl_down=True, c_down=True, now=10.1) is False
    assert detector.update(ctrl_down=True, c_down=False, now=10.2) is False
    assert detector.update(ctrl_down=True, c_down=True, now=10.4) is True


def test_poll_detector_resets_when_ctrl_is_released() -> None:
    detector = CtrlCPollStateDetector(DoubleCtrlCDetector(max_interval_seconds=0.7))

    assert detector.update(ctrl_down=True, c_down=True, now=10.0) is False
    assert detector.update(ctrl_down=False, c_down=False, now=10.2) is False
    assert detector.update(ctrl_down=True, c_down=True, now=10.3) is False
