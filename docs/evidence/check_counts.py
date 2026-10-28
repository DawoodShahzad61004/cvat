"""
Compares the stats endpoint with counts made straight from a COCO annotation file.

CVAT stores each part of a multi-part COCO polygon as its own shape (parts are
linked by the "group" field), so the endpoint is expected to match the number of
polygon parts per category, not the number of COCO instances. Both are printed.

usage: python check_counts.py BASE_URL TASK_ID TOKEN instances_val2017.json
"""

import json
import sys
import urllib.request
from collections import Counter

base_url, task_id, token, coco_path = sys.argv[1:]

with open(coco_path) as f:
    coco = json.load(f)
names = {category["id"]: category["name"] for category in coco["categories"]}
instances = Counter()
shapes = Counter()
for annotation in coco["annotations"]:
    name = names[annotation["category_id"]]
    segmentation = annotation["segmentation"]
    instances[name] += 1
    # a list holds polygon parts; a dict is one RLE mask (crowd regions)
    shapes[name] += len(segmentation) if isinstance(segmentation, list) else 1

request = urllib.request.Request(
    f"{base_url}/api/tasks/{task_id}/annotation-stats",
    headers={"Authorization": f"Token {token}"},
)
with urllib.request.urlopen(request) as response:
    stats = json.load(response)
actual = {label["name"]: label["count"] for label in stats["labels"]}

print(f"labels: COCO {len(names)}, endpoint {len(actual)}")
print(f"COCO instances: {sum(instances.values())}")
print(f"COCO shapes (polygon parts + masks): {sum(shapes.values())}")
print(f"endpoint total: {stats['total']}")

mismatches = [name for name in sorted(names.values()) if shapes[name] != actual.get(name)]
print(f"labels whose endpoint count differs from COCO shapes: {len(mismatches)}")
for name in mismatches:
    print(f"  {name}: COCO shapes {shapes[name]}, endpoint {actual.get(name)}")
