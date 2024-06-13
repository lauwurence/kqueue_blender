
import re

# line = 'blender --background "I:/test 1.blend" --scene "Scene" -E "CYCLES" --python "F:/render_settings.py" -f "1,2,3,4,5,6,7,8,9,10"'
line = "Saved: 'F:\RenPy\00_Renders\input\parts0004.png'"
# line = 'Saved: "F:\RenPy\00_Renders\input\parts0004.png"'
print(re.search(r'Saved: [\'|"](.*?)[\'|"]', line).group(1))
