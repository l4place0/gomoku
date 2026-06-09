class SymmetryHelper:
    BOARD_SIZE = 15
    CENTER = 7

    @staticmethod
    def transform_point(x, y, sym_index):
        dx = x - SymmetryHelper.CENTER
        dy = y - SymmetryHelper.CENTER
        
        if sym_index == 0:
            tx, ty = dx, dy
        elif sym_index == 1:
            tx, ty = -dy, dx
        elif sym_index == 2:
            tx, ty = -dx, -dy
        elif sym_index == 3:
            tx, ty = dy, -dx
        elif sym_index == 4:
            tx, ty = dx, -dy
        elif sym_index == 5:
            tx, ty = -dx, dy
        elif sym_index == 6:
            tx, ty = dy, dx
        elif sym_index == 7:
            tx, ty = -dy, -dx
        else:
            raise ValueError("Invalid symmetry index")
            
        return tx + SymmetryHelper.CENTER, ty + SymmetryHelper.CENTER

    @staticmethod
    def invert_point(tx, ty, sym_index):
        dx = tx - SymmetryHelper.CENTER
        dy = ty - SymmetryHelper.CENTER
        
        if sym_index == 0:
            rx, ry = dx, dy
        elif sym_index == 1:
            rx, ry = dy, -dx
        elif sym_index == 2:
            rx, ry = -dx, -dy
        elif sym_index == 3:
            rx, ry = -dy, dx
        elif sym_index == 4:
            rx, ry = dx, -dy
        elif sym_index == 5:
            rx, ry = -dx, dy
        elif sym_index == 6:
            rx, ry = dy, dx
        elif sym_index == 7:
            rx, ry = -dy, -dx
        else:
            raise ValueError("Invalid symmetry index")
            
        return rx + SymmetryHelper.CENTER, ry + SymmetryHelper.CENTER

    @staticmethod
    def get_canonical_sequence(moves):
        if not moves:
            return [], 0
            
        candidates = []
        for i in range(8):
            transformed = [SymmetryHelper.transform_point(x, y, i) for x, y in moves]
            candidates.append((transformed, i))
            
        # Lexicographically sort and pick the smallest sequence
        best_seq, best_i = min(candidates, key=lambda x: x[0])
        return best_seq, best_i

# ---- Unit Tests ----
def test_symmetry():
    # Test point transformation and inversion for all 8 symmetries
    test_points = [(7, 7), (7, 8), (5, 9), (12, 3), (0, 14)]
    for pt in test_points:
        for i in range(8):
            tx, ty = SymmetryHelper.transform_point(pt[0], pt[1], i)
            rx, ry = SymmetryHelper.invert_point(tx, ty, i)
            assert (rx, ry) == pt, f"Failed for point {pt} on sym {i}: transformed to {(tx, ty)}, inverted to {(rx, ry)}"
    print("All point transform/invert tests PASSED!")

    # Test canonical sequence uniqueness
    # 26 standard openings first few moves should normalize to the same canonical form
    moves1 = [(7, 7), (7, 8), (8, 8)]
    moves2 = [(7, 7), (8, 7), (8, 8)] # diagonal reflection
    
    canon1, i1 = SymmetryHelper.get_canonical_sequence(moves1)
    canon2, i2 = SymmetryHelper.get_canonical_sequence(moves2)
    
    assert canon1 == canon2, f"Failed canonical sequence matching: {canon1} vs {canon2}"
    print(f"Canonical matching test PASSED! Canon: {canon1}")

if __name__ == "__main__":
    test_symmetry()
