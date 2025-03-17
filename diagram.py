from typing import List, Dict

def gen_linear_diagram(linear_data: List[str]) -> Dict:
    nodeDataArray = [{"key": 0, "text": "Start", "category":"Start"}]
    linkDataArray = []
    for i, step in enumerate(linear_data):
        nodeDataArray.append({
            "key": i+1,
            "text": step,
            "category": "Question",
        })
    nodeDataArray.append({"key": len(linear_data)+1, "text": "End", "category":"End"})

    for i in range(len(linear_data)+1):
        linkDataArray.append({
            "from": i,
            "to": i+1,
        })

    return {
        "nodeDataArray": nodeDataArray,
        "linkDataArray": linkDataArray
    }