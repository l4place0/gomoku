import os
import json
import random

# Reuse the verified SymmetryHelper
from ml.verify_symmetry import SymmetryHelper

class OpeningBook:
    def __init__(self, filepath="opening_book.json"):
        self.filepath = filepath
        self.db = {}
        self.load()

    _MAX_JSON_SIZE = 50 * 1024 * 1024  # 50MB

    def load(self):
        if os.path.exists(self.filepath):
            try:
                if os.path.getsize(self.filepath) > self._MAX_JSON_SIZE:
                    print(f"Warning: {self.filepath} exceeds 50MB limit, skipping load")
                    self.db = {}
                    return
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.db = json.load(f)
            except Exception as e:
                self.db = {}
        else:
            self.db = {}

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.db, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save db: {e}")

    def query(self, moves, style="hybrid"):
        # 1. Get canonical moves and which symmetry index produced it
        canon_moves, sym_index = SymmetryHelper.get_canonical_sequence(moves)
        
        # Convert moves to string key: "x1,y1|x2,y2|..."
        key = "|".join(f"{x},{y}" for x, y in canon_moves)
        
        # 2. Query in standard DB
        candidates = self.db.get(key, [])
        if not candidates:
            return None
            
        # 3. Filter based on style
        filtered = []
        for c in candidates:
            src = c.get("source", "TRADITIONAL")
            if style == "traditional" and src != "TRADITIONAL":
                continue
            if style == "novelty" and src != "AI_NOVELTY":
                continue
            filtered.append(c)
            
        if not filtered:
            filtered = candidates
            
        # 4. Weighted random choice
        total_w = sum(c.get("weight", 1.0) for c in filtered)
        if total_w <= 0:
            return None
            
        r = random.uniform(0, total_w)
        curr = 0.0
        selected_move = None
        for c in filtered:
            curr += c.get("weight", 1.0)
            if curr >= r:
                selected_move = c["move"]
                break
                
        if selected_move is None and filtered:
            selected_move = filtered[0]["move"]
            
        if selected_move is None:
            return None
            
        # 5. Transform selected move back from canonical coordinates using inverse symmetry
        rx, ry = SymmetryHelper.invert_point(selected_move[0], selected_move[1], sym_index)
        return rx, ry

    def add_move(self, canon_moves, next_move_canon, source="AI_NOVELTY", weight=1.0, winrate=0.5, visits=100):
        key = "|".join(f"{x},{y}" for x, y in canon_moves)
        candidates = self.db.setdefault(key, [])
        
        for c in candidates:
            if c["move"] == next_move_canon:
                c["weight"] = max(c["weight"], weight)
                c["winrate"] = winrate
                c["visits"] = max(c.get("visits", 0), visits)
                c["source"] = source
                self.save()
                return
                
        candidates.append({
            "move": next_move_canon,
            "weight": weight,
            "source": source,
            "winrate": winrate,
            "visits": visits
        })
        self.save()

# ---- Unit Tests ----
def test_opening_book():
    test_db_path = "test_opening_book.json"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        
    book = OpeningBook(test_db_path)
    
    # 1. Add canonical openings
    # Standard: [(7,7)], next moves: (7,8) traditional, (8,8) AI novelty
    book.add_move([(7, 7)], [7, 8], source="TRADITIONAL", weight=1.0)
    book.add_move([(7, 7)], [8, 8], source="AI_NOVELTY", weight=1.5, winrate=0.68)
    
    # 2. Query symmetric equivalent
    # Active board: moves is [(7, 7)]
    # Symmetry transformation yields canon [(7, 7)], sym_index = 0
    # Expected results (transformed back) are either (7, 8) or (8, 8)
    res = book.query([(7, 7)], style="hybrid")
    assert res in [(7, 8), (8, 8)], f"Failed hybrid query: returned {res}"
    
    # 3. Test traditional style filter
    for _ in range(20):
        res_trad = book.query([(7, 7)], style="traditional")
        assert res_trad == (7, 8), f"Traditional style filter failed: returned {res_trad}"
        
    # 4. Test novelty style filter
    for _ in range(20):
        res_nov = book.query([(7, 7)], style="novelty")
        assert res_nov == (8, 8), f"Novelty style filter failed: returned {res_nov}"

    # 5. Clean up
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        
    print("All OpeningBook database query & style filter tests PASSED!")

if __name__ == "__main__":
    test_opening_book()
