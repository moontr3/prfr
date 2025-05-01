# https://github.com/moontr3/braille_tools

from typing import Literal
from PIL import Image


def binary_to_braille(
    pattern: "list[int | bool]",
    grid: bool = True
) -> str:
    '''
    Converts a list of binary elements to a unicode braille character.

    If `grid` is set to True, dots go from top left to bottom
    right.
    
    If `grid` is set to False, the positions of the dots correlate to 
    the pattern as follows:
    - First 6 elements represent the top 2x3 zone of a braille character,
    from top left to bottom right.
    - Other 2 elements represent the two bottom dots. If they're omitted,
    they get replaced with 0, 0.
    '''
    assert len(pattern) in [6,8],\
        'Length of the pattern must be either 6 or 8.'
    
    # converting grid to unicode representation
    if grid:
        indices = [0, 2, 4, 1, 3, 5, 6, 7][0:len(pattern)]
        pattern = [pattern[i] for i in indices]

    # converting pattern to unicode
    pattern = "".join(["1" if i else "0" for i in pattern][::-1])
    char = 0x2800+int(pattern, 2)
    return chr(char)


def matrix_to_braille(
    matrix: "list[list[int | bool]]",
    yheight: Literal[3, 4] = 4,
    line_separator: str = "\n"
):
    '''
    Converts a matrix of binary elements to a list of unicode braille characters.
    '''
    # checks
    assert yheight in [3, 4],\
        '`yheight` must be either 3 or 4.'
    
    assert len(matrix) != 0,\
        'Matrix must not be empty.'
    
    assert len(matrix) % yheight == 0,\
        'The height of the matrix must be divisible by `yheight`.'
    
    width = len(matrix[0])
    for index, row in enumerate(matrix):
        assert len(row) == width,\
            f'All rows must have the same width (error in row {index}).'
        
    assert width != 0,\
        'Matrix must not be empty.'
    
    assert width % 2 == 0,\
        'Matrix\'s width must be divisible by 2.'
    
    # converting matrix to a matrix of characters
    rows = []
    for index in range(int(len(matrix)/yheight)):
        pos = index*yheight
        m_rows = [
            matrix[pos],
            matrix[pos+1],
            matrix[pos+2],
        ]
        if yheight == 4:
            m_rows.append(matrix[pos+3])
            
        string = ''
        for xindex in range(len(m_rows[0])//2):
            binary = []
            for i in m_rows:
                binary.extend(i[xindex*2:xindex*2+2])
            string += binary_to_braille(binary, grid=True)

        rows.append(string)
    
    return line_separator.join(rows)


def pil_image_to_braille(
    image: Image, width: int = 20, threshold: float = 0.5,
    invert: bool = False
):
    '''
    Returns a braille string from a PIL image.
    '''
    threshold = int(255*3*threshold)

    # calculating size
    width *= 2
    height = int(image.size[1]*(width/image.size[0]))
    while height%4 != 0:
        height -= 1

    # resizing
    image = image.resize((width, height))

    # putting pixels in a matrix
    matrix = []
    for y in range(height):
        row = []
        for x in range(width):
            # grayscaling
            color = image.getpixel((x, y))
            color = (color[0]+color[1]+color[2])
            color = color > threshold

            if invert:
                color = not color
            row.append(color)

        matrix.append(row)
    
    return matrix_to_braille(matrix)