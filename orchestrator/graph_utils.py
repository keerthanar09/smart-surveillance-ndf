import matplotlib.pyplot as plt
import os

def generate_graphs(data):
    os.makedirs("outputs/graphs", exist_ok=True)
    graphs = {}

    crowd = data.get("crowd", {})
    aggregated = crowd.get("aggregated_outputs", [])
    print(aggregated)

    if not aggregated:
        plt.figure()
        plt.text(0.5, 0.5, "No crowd data available", ha="center", va="center")
        plt.title("Crowd Activity Levels")
        cpath = "outputs/graphs/crowd_activity.png"
        plt.savefig(cpath)
        plt.close()
        graphs["crowd_graph"] = cpath
    else:
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

        cpath = "outputs/graphs/crowd_activity.png"
        plt.savefig(cpath)
        plt.close()
        graphs["crowd_graph"] = cpath
    
    env_data = data.get("environment", {})
    env_agg = env_data.get("aggregated_environment", {})
    env_path = "outputs/graphs/environment_factors.png"

    if not env_agg:
        plt.figure()
        plt.text(0.5, 0.5, "No environment data available", ha="center", va="center")
        plt.title("Environment Factor Trends")
        plt.savefig(env_path)
        plt.close()
        graphs["environment_graph"] = env_path
    else:
        factors = list(env_agg.keys())
        values = list(env_agg.values())

        # Convert categorical labels (like "sunny", "day", etc.) to numeric codes for plotting
        unique_labels = {val: i for i, val in enumerate(sorted(set(values)))}
        numeric_values = [unique_labels[val] for val in values]

        plt.figure(figsize=(8, 4))
        plt.axis('off')
        plt.title("Environmental Factors Overview", fontsize=14, weight='bold')

        for i, (factor, value) in enumerate(env_agg.items()):
            plt.text(0, 1 - i*0.2, f"{factor.capitalize()}: {value}", fontsize=12)

        plt.tight_layout()
        plt.savefig("outputs/graphs/environment_factors.png")
        plt.close()

        graphs["environment_graph"] = env_path

    # === PLACEHOLDERS FOR FUTURE GRAPHS ===
    # # Emotion Trends Graph
    # plt.figure()
    # # TODO: Add plotting logic for emotion frequency trends
    # plt.title("Emotion Trends Over Time")
    # plt.savefig("outputs/graphs/emotion_trends.png")
    # plt.close()
    # graphs["emotion_trends"] = "outputs/graphs/emotion_trends.png"

    # # Body Language Trends Graph
    # plt.figure()
    # # TODO: Add plotting logic for body language indicators
    # plt.title("Body Language Trends")
    # plt.savefig("outputs/graphs/body_language_trends.png")
    # plt.close()
    # graphs["body_language_trends"] = "outputs/graphs/body_language_trends.png"

    # # Posture Trends Graph
    # plt.figure()
    # # TODO: Add plotting logic for posture analysis
    # plt.title("Posture Trends Over Time")
    # plt.savefig("outputs/graphs/posture_trends.png")
    # plt.close()
    # graphs["posture_trends"] = "outputs/graphs/posture_trends.png"

    # # Overall Trends Graph
    # plt.figure()
    # # TODO: Add logic combining emotion + crowd + environment scores
    # plt.title("Overall Mental Health Trends")
    # plt.savefig("outputs/graphs/overall_trends.png")
    # plt.close()
    # graphs["overall_trends"] = "outputs/graphs/overall_trends.png"

    return graphs
