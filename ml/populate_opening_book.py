import json
import os
from ml.verify_symmetry import SymmetryHelper
from verify_opening_book import OpeningBook

def build_opening_book():
    book_path = "opening_book.json"
    if os.path.exists(book_path):
        os.remove(book_path)
        
    book = OpeningBook(book_path)
    
    # 1. Turn 0 -> Move 1 (Black plays center)
    # Canon key is "" (empty)
    # Next move is (7, 7)
    book.add_move([], [7, 7], source="TRADITIONAL", weight=1.0)
    
    # 2. Turn 1 -> Move 2 (White plays Direct or Indirect)
    # Moves list has [(7, 7)]
    # Canon: [(7, 7)], next moves: (7, 8) Direct, (8, 8) Indirect
    book.add_move([(7, 7)], [7, 8], source="TRADITIONAL", weight=1.0) # Direct
    book.add_move([(7, 7)], [8, 8], source="TRADITIONAL", weight=1.0) # Indirect
    
    # 3. Turn 2 -> Move 3 (Black plays standard Renju openings)
    # Direct openings: White is at (7, 8)
    # Indirect openings: White is at (8, 8)
    
    # --- Direct Openings (直指) ---
    # 花月 (Flower Moon): Black at (8, 8)
    book.add_move([(7, 7), (7, 8)], [8, 8], source="TRADITIONAL", weight=1.2)
    # 浦月 (Crescent Moon): Black at (8, 7)
    book.add_move([(7, 7), (7, 8)], [8, 7], source="TRADITIONAL", weight=1.2)
    # 松月 (Pine Moon): Black at (8, 6)
    book.add_move([(7, 7), (7, 8)], [8, 6], source="TRADITIONAL", weight=1.0)
    # 疏星 (Sparse Star): Black at (9, 7)
    book.add_move([(7, 7), (7, 8)], [9, 7], source="TRADITIONAL", weight=1.0)
    # 瑞星 (Auspicious Star): Black at (9, 8)
    book.add_move([(7, 7), (7, 8)], [9, 8], source="TRADITIONAL", weight=1.0)
    # 寒星 (Cold Star): Black at (6, 8)
    book.add_move([(7, 7), (7, 8)], [6, 8], source="TRADITIONAL", weight=1.0)
    # 溪月 (Stream Moon): Black at (6, 7)
    book.add_move([(7, 7), (7, 8)], [6, 7], source="TRADITIONAL", weight=1.0)
    
    # --- Indirect Openings (斜指) ---
    # 斜月 (Diagonal Moon): Black at (7, 6)
    book.add_move([(7, 7), (8, 8)], [7, 6], source="TRADITIONAL", weight=1.2)
    # 恒星 (Constant Star): Black at (7, 8)
    book.add_move([(7, 7), (8, 8)], [7, 8], source="TRADITIONAL", weight=1.2)
    # 明星 (Bright Star): Black at (6, 8)
    book.add_move([(7, 7), (8, 8)], [6, 8], source="TRADITIONAL", weight=1.0)
    # 流星 (Meteor): Black at (9, 8)
    book.add_move([(7, 7), (8, 8)], [9, 8], source="TRADITIONAL", weight=1.0)
    # 名月 (Famous Moon): Black at (5, 9)
    book.add_move([(7, 7), (8, 8)], [5, 9], source="TRADITIONAL", weight=1.0)
    # 峡月 (Gorge Moon): Black at (6, 9)
    book.add_move([(7, 7), (8, 8)], [6, 9], source="TRADITIONAL", weight=1.0)
    
    # 4. Turn 3 -> Move 4 (White plays defense)
    # We add recommended Move 4 responses for the most common openings:
    
    # For 花月 Direct: [(7, 7), (7, 8), (8, 8)]
    # Canon: [(7, 7), (6, 7), (6, 6)]
    # Recommended White responses in canonical form:
    # 1st response: (8, 7) -> standard defense
    # 2nd response: (6, 8) -> diagonal counter-attack
    book.add_move([(7, 7), (7, 8), (8, 8)], [8, 7], source="TRADITIONAL", weight=1.0)
    book.add_move([(7, 7), (7, 8), (8, 8)], [6, 8], source="TRADITIONAL", weight=0.8)
    
    # For 浦月 Direct: [(7, 7), (7, 8), (8, 7)]
    # Recommended White response:
    book.add_move([(7, 7), (7, 8), (8, 7)], [8, 8], source="TRADITIONAL", weight=1.0)
    book.add_move([(7, 7), (7, 8), (8, 7)], [7, 6], source="TRADITIONAL", weight=0.8)
    
    # For 斜月 Indirect: [(7, 7), (8, 8), (7, 6)]
    # Recommended White response:
    book.add_move([(7, 7), (8, 8), (7, 6)], [8, 7], source="TRADITIONAL", weight=1.0)
    book.add_move([(7, 7), (8, 8), (7, 6)], [7, 8], source="TRADITIONAL", weight=0.8)
    
    # 5. Turn 4 -> Move 5 (Black plays attack)
    # For 花月 and White defense: [(7, 7), (7, 8), (8, 8), (8, 7)]
    # Recommended Black Move 5:
    book.add_move([(7, 7), (7, 8), (8, 8), (8, 7)], [6, 9], source="TRADITIONAL", weight=1.0)
    book.add_move([(7, 7), (7, 8), (8, 8), (8, 7)], [9, 6], source="TRADITIONAL", weight=0.8)
    
    # Print out summary
    print(f"Generated opening book database with {len(book.db)} canonical keys successfully!")

if __name__ == "__main__":
    build_opening_book()
