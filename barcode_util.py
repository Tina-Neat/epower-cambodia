"""
barcode_util.py - Standalone offline SVG Barcode Generator (Code 39 standard)
Generates high-precision vector barcodes without any external dependencies.
"""

CODE39_PATTERNS = {
    '0': 'bwbwbwBwb', '1': 'BwbwbWbwb', '2': 'bwBwbWbwb', '3': 'BwBwbwbwb',
    '4': 'bwbwBWbwb', '5': 'BwbwBWbwb', '6': 'bwBwBWbwb', '7': 'bwbwbWBwb',
    '8': 'BwbwbWBwb', '9': 'bwBwbWBwb', 'A': 'BwbwbwbWB', 'B': 'bwBwbwbWB',
    'C': 'BwBwbwbwb', 'D': 'bwbwBwbWB', 'E': 'BwbwBwbwb', 'F': 'bwBwBwbwb',
    'G': 'bwbwbwBWB', 'H': 'BwbwbwBwb', 'I': 'bwBwbwBwb', 'J': 'bwbwBwBwb',
    'K': 'BwbwbwbwB', 'L': 'bwBwbwbwB', 'M': 'BwBwbwbwb', 'N': 'bwbwBwbwB',
    'O': 'BwbwBwbwb', 'P': 'bwBwBwbwb', 'Q': 'bwbwbwBwB', 'R': 'BwbwbwBwb',
    'S': 'bwBwbwBwb', 'T': 'bwbwBwBwb', 'U': 'BwbwbwbwB', 'V': 'bwBwbwbwB',
    'W': 'BwBwbwbwb', 'X': 'bwBwbwBwB', 'Y': 'BwbwBwBwb', 'Z': 'bwBwBwBwb',
    '-': 'bWbwbwbWB', '.': 'BWbwbwbwb', ' ': 'bWBwbwbwb', '*': 'bWbwBwBwb',
    '$': 'bWbWbWbwb', '/': 'bWbWbwbWb', '+': 'bWbwbWbWb', '%': 'bwbWbWbWb'
}

def generate_barcode_svg(code: str, height: int = 38, narrow_width: float = 1.1, wide_width: float = 2.6) -> str:
    """
    Generates an inline SVG vector barcode for Code 39.
    Works 100% offline with zero external libraries.
    """
    cleaned = ''.join(c.upper() for c in code if c.upper() in CODE39_PATTERNS and c != '*')
    if not cleaned:
        cleaned = "000000"
    
    encoded = '*' + cleaned + '*'
    bars = []
    for char in encoded:
        pattern = CODE39_PATTERNS.get(char, 'bwbwbwbwb')
        for elem in pattern:
            bars.append(elem)
        bars.append('w') # Gap between characters

    x = 0.0
    rects = []
    for b in bars:
        w = wide_width if b in ('B', 'W') else narrow_width
        if b in ('b', 'B'):
            rects.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="{height}" fill="#000"/>')
        x += w

    total_width = x
    svg = (
        f'<svg viewBox="0 0 {total_width:.2f} {height}" '
        f'width="{total_width:.1f}px" height="{height}px" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;margin:0 auto;">'
        + ''.join(rects) +
        '</svg>'
    )
    return svg
