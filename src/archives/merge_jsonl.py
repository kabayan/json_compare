#!/usr/bin/env python3
"""2つのJSONLファイルをマージする簡単なスクリプト"""

import json

file1 = "datas/classification.infer.jsonl"
file2 = "datas/classification.infer.qwen1.7b.jsonl"
output = "datas/merged.jsonl"

# 複数行のJSONオブジェクトを処理
def read_json_objects(filepath):
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        # 複数のJSONオブジェクトを分割
        objects = content.strip().split('\n}\n{')
        for i, obj_str in enumerate(objects):
            # 最初と最後以外には中括弧を追加
            if i > 0:
                obj_str = '{' + obj_str
            if i < len(objects) - 1:
                obj_str = obj_str + '}'

            obj = json.loads(obj_str)
            data[obj["input"]] = obj["inference"]
    return data

data1 = read_json_objects(file1)
data2 = read_json_objects(file2)

with open(output, 'w', encoding='utf-8') as out:
    for input_text in data1:
        merged = {
            "input": input_text,
            "inference1": data1[input_text],
            "inference2": data2.get(input_text, "")
        }
        out.write(json.dumps(merged, ensure_ascii=False) + '\n')

print(f"マージ完了: {output}")