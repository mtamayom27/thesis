# How to Modify the Mazes?
The environment consists of the plane and the actual maze placed on top. This way both have different, easily adjustable textures. The textures within one of those objects, can not be easily adjusted (e.g. one wall has a different texture from the rest).
## Python
The texture can be adjusted by using a different texture file.
```python
self.__load_obj("mesh.obj","yellow_wall.png")
```
Just add the texture file into the texture folder and adjust the __load_obj() call.

Textures taken from https://github.com/deepmind/labmaze.

## Blender
The actual maze layout was created in Blender 2.93. Of course you can create an entirely new blender file, however in the existing files the maze is already oriented and placed, so that it will sit correctly on the plane.
Some quick blender tips:
- choose the layout tab for adjustments
-  click on the coordinate system axis to get a topview of the maze
- right from the coordinate system, click on the arrow to access the Transform tab to easily adjust any walls dimension precisely
- use "absolute grid snap" to move the walls along the grid lines

### Deleting a Wall
Select the wall and delete
### Moving a Wall
Select the wall, arrows will appear to move the object along the x or z axis.
With "absolute grid snap" activated you can move the wall along the grid easily.
### Creating a Wall
Use Shift-D to duplicate a selected wall. This way the wall will already be at the correct depth to sit correctly on the plane. For exact adjustments of the dimensions use the Transform tab, the Transform tool is also available. Creating a completely new wall or obstacle is also possible, but take care to place it correctly.

### Exporting the Maze
Go to 
File -> Export -> Wavefront (.obj)
This will also export the .mtl file, but you don't need it.

You're done! Don't forget to add a topview image for plotting purposes if you need it.

## Layouts

The available layouts are taken from:

TY  - Informal Publication
ID  - DBLP:journals/corr/abs-1803-00653
AU  - Savinov, Nikolay
AU  - Dosovitskiy, Alexey
AU  - Koltun, Vladlen
TI  - Semi-parametric Topological Memory for Navigation.
JO  - CoRR
VL  - abs/1803.00653
PY  - 2018//
UR  - http://arxiv.org/abs/1803.00653
ER  -
