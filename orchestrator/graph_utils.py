import matplotlib.pyplot as plt
import os

def generate_graphs(data):
    os.makedirs("outputs/graphs", exist_ok=True)

    crowd = data.get("crowd", {})
    aggregated = crowd.get("aggregated_outputs", [])
    print(aggregated)

    if not aggregated:
        plt.figure()
        plt.text(0.5, 0.5, "No crowd data available", ha="center", va="center")
        plt.title("Crowd Activity Levels")
        path = "outputs/graphs/crowd_activity.png"
        plt.savefig(path)
        plt.close()
        return {"crowd_graph": path}

    zones = sorted(list(aggregated[0]["aggregate"].keys()))

    frame_labels = [f"{a['frame_window'][0]}–{a['frame_window'][1]}" for a in aggregated]
    values = []
    for agg in aggregated:
        vals = [agg["aggregate"][z]["avg_people"] for z in zones]
        values.append(vals)

    import numpy as np
    x = np.arange(len(zones))
    width = 0.35

    plt.figure(figsize=(12, 6))
    for i, frame in enumerate(frame_labels):
        plt.bar(x + i * width, values[i], width, label=f"Frames {frame}")

    plt.xlabel("Zones")
    plt.ylabel("Average People")
    plt.title("Crowd Activity by Zone and Frame Window")
    plt.xticks(x + width / 2, zones)
    plt.legend()
    plt.tight_layout()

    path = "outputs/graphs/crowd_activity.png"
    plt.savefig(path)
    plt.close()

    return {"crowd_graph": path}
