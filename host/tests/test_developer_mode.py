import sys
import os
import time
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from developer_models import (
    DeveloperEventType,
    DeveloperState,
    DeveloperPriority,
    DeveloperEvent,
    DeveloperZone,
    DeveloperLayout,
    get_event_profile,
)
from developer_engine import DeveloperEventManager, DeveloperRenderer
from dev_events import DevEventHandler
from app_state import AppState, AppMode
from lighting_engine import LightingEngine

# 1. Every supported event is valid
def test_every_supported_event_is_valid():
    manager = DeveloperEventManager()
    all_events = [
        # Coding
        DeveloperEventType.CODE_ACTIVE,
        DeveloperEventType.FILE_SAVED,
        DeveloperEventType.CODE_WARNING,
        DeveloperEventType.CODE_ERROR,
        # Build
        DeveloperEventType.BUILD_STARTED,
        DeveloperEventType.BUILD_SUCCESS,
        DeveloperEventType.BUILD_FAILED,
        # Tests
        DeveloperEventType.TEST_STARTED,
        DeveloperEventType.TEST_SUCCESS,
        DeveloperEventType.TEST_FAILED,
        # Git
        DeveloperEventType.GIT_COMMIT,
        DeveloperEventType.GIT_PUSH,
        DeveloperEventType.PR_CREATED,
        DeveloperEventType.PR_MERGED,
        # Deployment
        DeveloperEventType.DEPLOY_STARTED,
        DeveloperEventType.DEPLOY_SUCCESS,
        DeveloperEventType.DEPLOY_FAILED,
        # Runtime
        DeveloperEventType.SERVER_STARTED,
        DeveloperEventType.SERVER_STOPPED,
        DeveloperEventType.SERVER_ERROR,
        # General
        DeveloperEventType.WARNING,
        DeveloperEventType.ERROR,
    ]

    for ev in all_events:
        # Check string enum resolution
        resolved = DeveloperEventType.from_string(ev.value)
        assert resolved == ev, f"Failed to resolve {ev.value} from string"

        # Check manager accepts the event
        ok, err, res = manager.handle_event(ev)
        assert ok is True, f"Event {ev} was rejected: {err}"
        assert res["event"]["event_type"] == ev.value

# 2. Invalid event is rejected
def test_invalid_event_is_rejected():
    manager = DeveloperEventManager()
    invalid_cases = ["NON_EXISTENT_EVENT", "deploy_invalid", "random_string", "", None, 123]
    for inv in invalid_cases:
        ok, err, res = manager.handle_event(inv)
        assert ok is False, f"Expected invalid event '{inv}' to be rejected"
        assert err is not None

# 3. BUILD_STARTED changes state to BUILDING
def test_build_started_changes_state_to_building():
    manager = DeveloperEventManager()
    assert manager.get_state() == DeveloperState.IDLE

    ok, err, res = manager.handle_event(DeveloperEventType.BUILD_STARTED)
    assert ok is True
    assert manager.get_state() == DeveloperState.BUILDING
    assert res["developer_state"] == "BUILDING"

# 4. BUILD_SUCCESS changes state appropriately
def test_build_success_changes_state_appropriately():
    manager = DeveloperEventManager()
    manager.handle_event(DeveloperEventType.BUILD_STARTED)
    assert manager.get_state() == DeveloperState.BUILDING

    ok, err, res = manager.handle_event(DeveloperEventType.BUILD_SUCCESS)
    assert ok is True
    # Should transition state back to IDLE
    assert manager.get_state() == DeveloperState.IDLE
    assert res["developer_state"] == "IDLE"
    # Should produce transient success event
    active = manager.get_active_event()
    assert active is not None
    assert active.event_type == DeveloperEventType.BUILD_SUCCESS

# 5. BUILD_FAILED produces a high-priority developer event
def test_build_failed_produces_high_priority_developer_event():
    manager = DeveloperEventManager()
    ok, err, res = manager.handle_event(DeveloperEventType.BUILD_FAILED)
    assert ok is True
    active = manager.get_active_event()
    assert active is not None
    assert active.event_type == DeveloperEventType.BUILD_FAILED
    assert active.priority == DeveloperPriority.CRITICAL

    # Ensure lower-priority event cannot overwrite it while active
    ok_low, err_low, res_low = manager.handle_event(DeveloperEventType.CODE_ACTIVE)
    assert ok_low is True
    # Event should be rejected from active slot because priority is lower
    assert res_low["event_accepted"] is False
    assert manager.get_active_event().event_type == DeveloperEventType.BUILD_FAILED

# 6. TEST_STARTED changes state to TESTING
def test_test_started_changes_state_to_testing():
    manager = DeveloperEventManager()
    ok, err, res = manager.handle_event(DeveloperEventType.TEST_STARTED)
    assert ok is True
    assert manager.get_state() == DeveloperState.TESTING

    ok2, err2, res2 = manager.handle_event(DeveloperEventType.TEST_SUCCESS)
    assert ok2 is True
    assert manager.get_state() == DeveloperState.IDLE

# 7. DEPLOY_STARTED changes state to DEPLOYING
def test_deploy_started_changes_state_to_deploying():
    manager = DeveloperEventManager()
    ok, err, res = manager.handle_event(DeveloperEventType.DEPLOY_STARTED)
    assert ok is True
    assert manager.get_state() == DeveloperState.DEPLOYING

    ok2, err2, res2 = manager.handle_event(DeveloperEventType.DEPLOY_SUCCESS)
    assert ok2 is True
    assert manager.get_state() == DeveloperState.IDLE

# 8. Developer zones are valid
def test_developer_zones_are_valid():
    layout = DeveloperLayout.default(total_leds=300)
    valid, err = layout.validate()
    assert valid is True
    assert err is None

    # Check the default 4 zones exist
    assert "build" in layout.zones
    assert "test" in layout.zones
    assert "git" in layout.zones
    assert "deploy" in layout.zones

    # Test invalid zones: start_led < 1
    bad_zone1 = DeveloperZone(name="bad", start_led=0, end_led=50)
    v1, e1 = bad_zone1.validate(300)
    assert v1 is False

    # Test invalid zones: end_led < start_led
    bad_zone2 = DeveloperZone(name="bad", start_led=100, end_led=50)
    v2, e2 = bad_zone2.validate(300)
    assert v2 is False

    # Test invalid zones: end_led > total_leds
    bad_zone3 = DeveloperZone(name="bad", start_led=1, end_led=301)
    v3, e3 = bad_zone3.validate(300)
    assert v3 is False

# 9. LED numbering: UI/config = 1-based, internal = 0-based
def test_led_numbering_ui_config_1_based_internal_0_based():
    layout = DeveloperLayout.default(total_leds=300)
    build_zone = layout.zones["build"]
    test_zone = layout.zones["test"]
    git_zone = layout.zones["git"]
    deploy_zone = layout.zones["deploy"]

    # 1-based UI / config verification
    assert build_zone.start_led == 1
    assert build_zone.end_led == 75
    assert test_zone.start_led == 76
    assert test_zone.end_led == 150
    assert git_zone.start_led == 151
    assert git_zone.end_led == 225
    assert deploy_zone.start_led == 226
    assert deploy_zone.end_led == 300

    # 0-based internal indexing verification
    assert build_zone.start_idx == 0
    assert build_zone.end_idx == 74
    assert build_zone.led_count == 75

    assert test_zone.start_idx == 75
    assert test_zone.end_idx == 149
    assert test_zone.led_count == 75

    assert git_zone.start_idx == 150
    assert git_zone.end_idx == 224
    assert git_zone.led_count == 75

    assert deploy_zone.start_idx == 225
    assert deploy_zone.end_idx == 299
    assert deploy_zone.led_count == 75

    # Contiguity check across 300 LEDs
    assert build_zone.led_count + test_zone.led_count + git_zone.led_count + deploy_zone.led_count == 300

# 10. Renderer always produces exactly 300 LEDs
def test_renderer_always_produces_exactly_300_leds():
    renderer = DeveloperRenderer(led_count=300)
    layout = DeveloperLayout.default(total_leds=300)

    states = [
        DeveloperState.IDLE,
        DeveloperState.CODING,
        DeveloperState.BUILDING,
        DeveloperState.TESTING,
        DeveloperState.DEPLOYING,
    ]

    events = [
        None,
        DeveloperEvent(event_type=DeveloperEventType.BUILD_STARTED, metadata={"zone": "build"}),
        DeveloperEvent(event_type=DeveloperEventType.BUILD_SUCCESS, metadata={"zone": "build"}),
        DeveloperEvent(event_type=DeveloperEventType.BUILD_FAILED, priority=DeveloperPriority.CRITICAL, metadata={"zone": "build"}),
        DeveloperEvent(event_type=DeveloperEventType.TEST_STARTED, metadata={"zone": "test"}),
        DeveloperEvent(event_type=DeveloperEventType.DEPLOY_STARTED, metadata={"zone": "deploy"}),
        DeveloperEvent(event_type=DeveloperEventType.ERROR, priority=DeveloperPriority.CRITICAL),
    ]

    for st in states:
        for ev in events:
            frame = renderer.render(
                state=st,
                active_event=ev,
                layout=layout,
                global_brightness=1.0,
                mode_limit=1.0,
                power_on=True
            )
            assert len(frame) == 300, f"Frame length was {len(frame)} for state {st} and event {ev}"
            for r, g, b in frame:
                assert 0 <= r <= 255
                assert 0 <= g <= 255
                assert 0 <= b <= 255

    # Also test Protocol V2 compact zone extraction <= 42 zones
    zones = renderer.extract_zones_for_protocol(frame, layout)
    assert len(zones) <= 42

# 11. Power OFF produces all black
def test_power_off_produces_all_black():
    renderer = DeveloperRenderer(led_count=300)
    layout = DeveloperLayout.default(total_leds=300)
    ev = DeveloperEvent(event_type=DeveloperEventType.BUILD_FAILED, priority=DeveloperPriority.CRITICAL)

    frame = renderer.render(
        state=DeveloperState.BUILDING,
        active_event=ev,
        layout=layout,
        global_brightness=1.0,
        mode_limit=1.0,
        power_on=False # Power OFF
    )
    assert len(frame) == 300
    assert all(pixel == (0, 0, 0) for pixel in frame)

    # Also test brightness 0 produces black
    frame_zero_bright = renderer.render(
        state=DeveloperState.BUILDING,
        active_event=ev,
        layout=layout,
        global_brightness=0.0,
        mode_limit=1.0,
        power_on=True
    )
    assert all(pixel == (0, 0, 0) for pixel in frame_zero_bright)

# 12. Switching away from Developer Mode clears developer influence
def test_switching_away_clears_developer_influence():
    mock_transport = MagicMock()
    mock_transport.is_connected.return_value = True

    app_state = AppState()
    app_state.set_power(True)
    app_state.set_mode(AppMode.DEVELOPER)

    engine = LightingEngine(transport=mock_transport, app_state=app_state)
    try:
        # Trigger an event in developer mode
        engine.trigger_developer_event("BUILD_STARTED")
        time.sleep(0.1) # let render loop execute
        assert engine.developer_event_manager.get_state() == DeveloperState.BUILDING

        # Switch to custom mode
        app_state.set_mode(AppMode.CUSTOM)
        time.sleep(0.1) # let render loop execute
        # Frame should now be rendered by CustomEffectEngine, not developer
        assert engine.last_mode == "custom"

        # Triggering developer event while in custom mode must NOT affect custom frame
        engine.trigger_developer_event("BUILD_FAILED")
        time.sleep(0.1)
        # Verify custom mode is still active
        assert app_state.mode == AppMode.CUSTOM

        # Now switch back to developer mode: stale events should be reset
        app_state.set_mode(AppMode.DEVELOPER)
        time.sleep(0.1)
        # Transient event was cleared upon entering developer mode
        assert engine.developer_event_manager.get_active_event() is None
    finally:
        engine.stop()

# 13. Existing Music Mode tests still pass
def test_existing_music_mode_integrity():
    from music_models import MusicAnalysis, DEFAULT_3_BAND_PRESET, MusicMapping
    from music_mapping_engine import MusicMappingEngine

    engine = MusicMappingEngine(led_count=300)
    analysis = MusicAnalysis()
    analysis.bass_energy = 0.8
    analysis.music_gate_open = True
    mappings = [MusicMapping.from_dict(m) for m in DEFAULT_3_BAND_PRESET]

    frame = engine.render_frame(
        analysis=analysis,
        mappings=mappings,
        user_brightness=1.0,
        mode_limit=1.0,
        power_on=True,
        response_mode="flash"
    )
    assert len(frame) == 300
    zones = engine.extract_zones_for_protocol(
        analysis=analysis,
        mappings=mappings,
        user_brightness=1.0,
        mode_limit=1.0,
        power_on=True,
        response_mode="flash"
    )
    assert len(zones) <= 42

# 14. Existing Custom Mode tests still pass
def test_existing_custom_mode_integrity():
    from custom_effects import CustomEffectEngine, DEFAULT_EFFECT_CONFIGS

    engine = CustomEffectEngine(led_count=300)
    for effect_name, config in DEFAULT_EFFECT_CONFIGS.items():
        frame = engine.render(
            effect_name=effect_name,
            config=config,
            led_count=300,
            elapsed_time=1.0,
            dt=0.033,
            global_brightness=1.0,
            mode_limit=1.0,
            power_on=True
        )
        assert len(frame) == 300
        zones = engine.extract_zones_for_protocol(frame, effect_name, config)
        assert len(zones) <= 42

# 15. Semantic visual color dominance tests
def test_visual_semantic_properties():
    renderer = DeveloperRenderer(led_count=300)
    layout = DeveloperLayout.default(total_leds=300)

    # IDLE: Non-black subtle output, blue/cyan dominant
    frame_idle = renderer.render(DeveloperState.IDLE, None, layout, current_time=2.0)
    assert any(c != (0, 0, 0) for c in frame_idle)
    avg_r = sum(c[0] for c in frame_idle) / 300.0
    avg_g = sum(c[1] for c in frame_idle) / 300.0
    avg_b = sum(c[2] for c in frame_idle) / 300.0
    assert avg_r == 0
    assert avg_b > avg_g > 0

    # CODING: Non-black output, bright flowing cyan/blue
    frame_coding = renderer.render(DeveloperState.CODING, None, layout, current_time=2.0)
    avg_r = sum(c[0] for c in frame_coding) / 300.0
    avg_g = sum(c[1] for c in frame_coding) / 300.0
    avg_b = sum(c[2] for c in frame_coding) / 300.0
    assert avg_b > 60
    assert avg_g > 20

    # BUILDING: Active blue
    frame_build = renderer.render(DeveloperState.BUILDING, None, layout, current_time=2.0)
    avg_b = sum(c[2] for c in frame_build) / 300.0
    assert avg_b > 60

    # TESTING: Active purple/magenta
    frame_test = renderer.render(DeveloperState.TESTING, None, layout, current_time=2.0)
    avg_r = sum(c[0] for c in frame_test) / 300.0
    avg_b = sum(c[2] for c in frame_test) / 300.0
    assert avg_r > 30 and avg_b > 40

    # DEPLOYING: Active cyan
    frame_deploy = renderer.render(DeveloperState.DEPLOYING, None, layout, current_time=2.0)
    avg_g = sum(c[1] for c in frame_deploy) / 300.0
    avg_b = sum(c[2] for c in frame_deploy) / 300.0
    assert avg_g > 30 and avg_b > 50

    # SUCCESS: Green-dominant output
    ev_success = DeveloperEvent(event_type=DeveloperEventType.BUILD_SUCCESS, duration=3.0, timestamp=1.0)
    frame_success = renderer.render(DeveloperState.IDLE, ev_success, layout, current_time=1.5)
    avg_r = sum(c[0] for c in frame_success) / 300.0
    avg_g = sum(c[1] for c in frame_success) / 300.0
    avg_b = sum(c[2] for c in frame_success) / 300.0
    assert avg_g > avg_r and avg_g > avg_b, "Success event must be green-dominant"

    # FAILURE: Red-dominant output
    ev_fail = DeveloperEvent(event_type=DeveloperEventType.BUILD_FAILED, duration=3.0, timestamp=1.0)
    # Sample during pulse peak
    frame_fail = renderer.render(DeveloperState.IDLE, ev_fail, layout, current_time=1.17)
    avg_r = sum(c[0] for c in frame_fail) / 300.0
    avg_g = sum(c[1] for c in frame_fail) / 300.0
    avg_b = sum(c[2] for c in frame_fail) / 300.0
    assert avg_r > avg_g and avg_r > avg_b, "Failure event must be red-dominant"

    # WARNING: Orange/yellow dominant (Red and Green high, Blue low)
    ev_warn = DeveloperEvent(event_type=DeveloperEventType.WARNING, duration=3.0, timestamp=1.0)
    frame_warn = renderer.render(DeveloperState.IDLE, ev_warn, layout, current_time=1.25)
    avg_r = sum(c[0] for c in frame_warn) / 300.0
    avg_g = sum(c[1] for c in frame_warn) / 300.0
    avg_b = sum(c[2] for c in frame_warn) / 300.0
    assert avg_r > avg_b and avg_g > avg_b, "Warning event must be orange/yellow-dominant"


# 16. Time-based animation progression test
def test_time_based_animation_progression():
    renderer = DeveloperRenderer(led_count=300)
    layout = DeveloperLayout.default(total_leds=300)

    # Frame at t=1.0 vs t=1.5 in BUILDING state
    frame1 = renderer.render(DeveloperState.BUILDING, None, layout, current_time=1.0)
    frame2 = renderer.render(DeveloperState.BUILDING, None, layout, current_time=1.5)

    # Must produce different pixel values as the sweep moves
    diffs = [abs(f1[2] - f2[2]) for f1, f2 in zip(frame1, frame2)]
    assert sum(diffs) > 100, "BUILDING animation must progress across time"

    # Protocol V2 Zone extraction produces <= 42 zones
    zones = renderer.extract_zones_for_protocol(frame1, layout)
    assert len(zones) == 25
    assert len(zones) <= 42
    # Contiguous coverage check
    assert zones[0]["start"] == 0
    assert zones[-1]["end"] == 299


# 17. HTTP event API ingestion test
def test_http_event_api_ingestion():
    import urllib.request
    import json

    manager = DeveloperEventManager()
    handler = DevEventHandler(manager, port=9998)
    handler.start()
    time.sleep(0.1)

    try:
        # GET /
        req = urllib.request.Request("http://127.0.0.1:9998/")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            assert data["status"] == "ok"
            assert data["developer_state"] == "IDLE"

        # POST /event with BUILD_STARTED
        post_data = json.dumps({"event": "BUILD_STARTED"}).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:9998/event",
            data=post_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode('utf-8'))
            assert res["status"] == "ok"
            assert res["developer_state"] == "BUILDING"

        # State should now be BUILDING
        assert manager.get_state() == DeveloperState.BUILDING

        # POST / with CODING_ACTIVITY
        post_data = json.dumps({"event": "CODING_ACTIVITY"}).encode('utf-8')
        req = urllib.request.Request(
            "http://127.0.0.1:9998/",
            data=post_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode('utf-8'))
            assert res["status"] == "ok"
            assert res["developer_state"] == "CODING"

        assert manager.get_state() == DeveloperState.CODING

        # Invalid event -> 400
        post_bad = json.dumps({"event": "INVALID_EVENT_123"}).encode('utf-8')
        req_bad = urllib.request.Request(
            "http://127.0.0.1:9998/event",
            data=post_bad,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req_bad)
        assert exc_info.value.code == 400

    finally:
        handler.stop()
