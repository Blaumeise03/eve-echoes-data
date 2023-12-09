import argparse
import json
import sys


def import_item_data(path):
    sys.path.append(path)
    from data_common.static.item import item_type
    category_ids = {}
    group_ids = {}
    type_ids = {}
    for cat in filter(lambda c: not c.startswith('__'), dir(item_type.CategoryIds)):
        category_ids[getattr(item_type.CategoryIds, cat)] = cat
    for group in filter(lambda g: not g.startswith('__'), dir(item_type.GroupIds)):
        group_ids[getattr(item_type.GroupIds, group)] = group
    for i_type in filter(lambda t: not t.startswith('__'), dir(item_type.ItemTypeIds)):
        type_ids[getattr(item_type.ItemTypeIds, i_type)] = i_type
    result = {
        "category_ids": category_ids,
        "group_ids": group_ids,
        "type_ids": type_ids
    }
    result = json.dumps(result, ensure_ascii=False)
    print result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("script_path", help="The path to the game source code directory (often called 'script')")
    args = parser.parse_args()
    import_item_data(args.script_path)
