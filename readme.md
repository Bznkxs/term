# readme
```python
python imshow.py
```

enters image viewer.

```python
python imshow.py FILENAME
```

loads image.

```python
python imshow.py FILENAME MODE
```

load with chosen render mode: 
- (default) rgb: 24-bit true color
- color256: 8-bit color
- color8: preset
- grey: greyscale

In image viewer:

- `wasd` move up, left, down, right
- `j` zoom in
- `k` zoom out
- **`q` quit**
- **`q` quit**
- **`q` quit**
- `l`+`FILENAME[ENTER]` (no space between) load new file
- `b` change pixel width between 2 and 3. Usually the width should be set to 3 if the console fontsize is small.
- `x` + `NEW_HEIGHT[ENTER]` + `NEW_WIDTH[ENTER]` fix display height and/or width. 
  
  By default, if you change terminal size, the image will be aligned to the new size when you press any key. 
  `x` allows you to fix one or two size dimensions. Set the dimension to -1 if you want it to align to terminal.
  e.g. `x` + `200` + `-1`: fix height but leave a flexible width.
  
- `f` shortcut for `x`+`-1`+`-1`; align both dimensions to terminal size
- `p` change pooling method between "mean" and "nearest".
- `m` change render mode between "rgb", "color256", "color8" and "grey".
- `t`+`FILENAME[ENTER]` output ANSI sequence to file
- `NUMBER` + `OPERATION`: repeat
  
    eg. 3d: move right 3 steps

> note: may have to commit input with an ending Enter. For example, 
> in Windows terminal, you may have to enter the following sequence
> `20` + `[ENTER]` + `w` + `[ENTER]` to move up 20 pixels.
> Also: `l` + `[ENTER]` + `FILENAME`.