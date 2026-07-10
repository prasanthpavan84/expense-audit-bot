import os
import threading
import time
import unittest
from app.conversation.memory import SessionMemory


class TestSessionMemory(unittest.TestCase):
    def setUp(self):
        SessionMemory.reset()
        SessionMemory.set_ttl(1800)
        SessionMemory.set_max_history_size(1000)

    def tearDown(self):
        SessionMemory.reset()

    def test_session_isolation(self):
        sess_a = "user-a"
        sess_b = "user-b"
        
        SessionMemory.update_session(sess_a, {"user": "Alice", "role": "admin"})
        SessionMemory.update_session(sess_b, {"user": "Bob", "role": "user"})
        
        data_a = SessionMemory.get_session(sess_a)
        data_b = SessionMemory.get_session(sess_b)
        
        self.assertEqual(data_a.get("user"), "Alice")
        self.assertEqual(data_b.get("user"), "Bob")
        self.assertNotEqual(data_a.get("user"), data_b.get("user"))

    def test_long_conversation_100_turns(self):
        sess_id = "long-conv"
        for i in range(100):
            SessionMemory.add_to_history(sess_id, {"turn": i, "text": f"message {i}"})
            
        session = SessionMemory.get_session(sess_id)
        self.assertEqual(len(session["history"]), 100)
        self.assertEqual(session["history"][0]["turn"], 0)
        self.assertEqual(session["history"][-1]["turn"], 99)

    def test_rolling_history_pruning(self):
        sess_id = "rolling-conv"
        SessionMemory.set_max_history_size(5)
        
        for i in range(10):
            SessionMemory.add_to_history(sess_id, f"item_{i}")
            
        session = SessionMemory.get_session(sess_id)
        self.assertEqual(len(session["history"]), 5)
        self.assertEqual(session["history"], ["item_5", "item_6", "item_7", "item_8", "item_9"])

    def test_session_expiration_ttl(self):
        sess_id = "expiring-session"
        SessionMemory.set_ttl(1)
        
        SessionMemory.update_session(sess_id, {"val": 42})
        
        session = SessionMemory.get_session(sess_id)
        self.assertEqual(session.get("val"), 42)
        
        time.sleep(1.2)
        
        session_expired = SessionMemory.get_session(sess_id)
        self.assertNotIn("val", session_expired)

    def test_memory_reset(self):
        sess_id = "reset-session"
        SessionMemory.update_session(sess_id, {"secret": "xyz"})
        
        SessionMemory.reset()
        
        session = SessionMemory.get_session(sess_id)
        self.assertNotIn("secret", session)
        self.assertFalse(os.path.exists(SessionMemory._backup_file))

    def test_session_recovery_serialization(self):
        sess_id = "recovery-session"
        SessionMemory.update_session(sess_id, {"data": "save-me"})
        SessionMemory.add_to_history(sess_id, {"msg": "hi"})
        
        self.assertTrue(os.path.exists(SessionMemory._backup_file))
        
        with SessionMemory._lock:
            SessionMemory._store.clear()
            SessionMemory._last_accessed.clear()
            
        session = SessionMemory.get_session(sess_id)
        self.assertEqual(session.get("data"), "save-me")
        self.assertEqual(session.get("history"), [{"msg": "hi"}])

    def test_race_conditions_concurrency(self):
        sess_id = "concurrent-session"
        num_threads = 10
        iterations = 30
        
        def worker():
            for i in range(iterations):
                SessionMemory.add_to_history(sess_id, i)
                time.sleep(0.001)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        session = SessionMemory.get_session(sess_id)
        self.assertEqual(len(session["history"]), num_threads * iterations)
