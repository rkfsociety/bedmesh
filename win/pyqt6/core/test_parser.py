from mesh_parser import MeshParser

# Пример строки конфига Klipper
test_cfg = """
[bed_mesh default]
version = 1
points =
      0.012, 0.005, -0.008
      0.010, 0.003, -0.006
      0.008, 0.001, -0.004
x_count = 3
y_count = 3
min_x = 20.0
max_x = 280.0
min_y = 20.0
max_y = 280.0
"""

parser = MeshParser()
data = parser.parse_config(test_cfg)
print(f"✅ Сетка: {data.x_count}x{data.y_count}")
print(f"Z matrix:\n{data.z}")