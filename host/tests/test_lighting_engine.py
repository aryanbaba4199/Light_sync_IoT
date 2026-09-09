import sys
import os
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lighting_state import LightingState, EventPriority
from lighting_engine import PriorityManager

class TestLightingEngine(unittest.TestCase):
    def test_priority_manager_base(self):
        pm = PriorityManager()
        pm.set_base_state(100, 150, 200, 255)
        target = pm.get_current_target()
        
        self.assertEqual(target.r, 100)
        self.assertEqual(target.g, 150)
        self.assertEqual(target.b, 200)
        self.assertEqual(target.brightness, 255)

    def test_priority_manager_event_override(self):
        pm = PriorityManager()
        pm.set_base_state(100, 100, 100, 128)
        
        event_state = LightingState(r=255, g=0, b=0, brightness=255, priority=EventPriority.CRITICAL_DEV_EVENT)
        pm.set_event(event_state, 0.5) # 0.5 sec duration
        
        target = pm.get_current_target()
        self.assertEqual(target.r, 255)
        self.assertEqual(target.priority, EventPriority.CRITICAL_DEV_EVENT)
        
        # Wait for expiration
        time.sleep(0.6)
        target_after = pm.get_current_target()
        self.assertEqual(target_after.r, 100)
        self.assertEqual(target_after.priority, EventPriority.SCREEN_COLOR)

    def test_lighting_state_bounds(self):
        state = LightingState(r=300, g=-50, b=255, brightness=999)
        state.validate()
        self.assertEqual(state.r, 255)
        self.assertEqual(state.g, 0)
        self.assertEqual(state.b, 255)
        self.assertEqual(state.brightness, 255)

if __name__ == '__main__':
    unittest.main()
