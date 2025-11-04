import matplotlib.pyplot as plt
import numpy as np
import os
from collections import Counter
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def explain_single_graph(graph_path, title, context_summary):
    """Explain a single graph using Gemini."""
    prompt = f"""
    You are an AI data analyst. Analyze only the following graph titled "{title}".
    Describe what trends or patterns it shows in 3-5 sentences.
    Do not summarize the overall dataset. Only focus on this graph.
    Context: {context_summary}
    """

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        parts = [prompt]
        if os.path.exists(graph_path):
            parts.append({
                "mime_type": "image/png",
                "data": open(graph_path, "rb").read()
            })

        result = model.generate_content(parts)
        return result.text.strip() if result and result.text else "No explanation generated."

    except Exception as e:
        print(f"Gemini explanation failed for {title}:", e)
        return "Explanation unavailable due to an API issue."



def generate_graphs(data):
    os.makedirs("outputs/graphs", exist_ok=True)
    graphs = {}
    context_summary = data.get("context", "General crowd monitoring context")

    # ===== CROWD GRAPH =====
    crowd = data.get("crowd", {})
    aggregated = crowd.get("aggregated_outputs", [])
    cpath = "outputs/graphs/crowd_activity.png"
    if not aggregated:
        plt.figure()
        plt.text(0.5, 0.5, "No crowd data available", ha="center", va="center")
        plt.title("Crowd Activity Levels")
    else:
        zones = sorted(list(aggregated[0]["aggregate"].keys()))
        frame_labels = [f"{a['frame_window'][0]}–{a['frame_window'][1]}" for a in aggregated]
        values = []
        for agg in aggregated:
            vals = [agg["aggregate"][z]["avg_people"] for z in zones]
            values.append(vals)

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
    plt.savefig(cpath)
    plt.close()

    graphs["crowd_graph"] = {
        "path": cpath,
        "explanation": explain_single_graph(cpath, "Crowd Activity", context_summary)
    }

    # ===== ENVIRONMENT GRAPH =====
    env = data.get("environment", {})
    env_agg = env.get("aggregated_environment", {})
    env_path = "outputs/graphs/environment_factors.png"
    if not env_agg:
        plt.figure()
        plt.text(0.5, 0.5, "No environment data", ha="center", va="center")
        plt.title("Environment Factors")
    else:
        plt.figure(figsize=(6, 4))
        plt.bar(env_agg.keys(), [1] * len(env_agg), color="lightcoral")
        plt.xticks(rotation=30)
        plt.title("Environment Attributes Summary")
        for i, (k, v) in enumerate(env_agg.items()):
            plt.text(i, 0.9, v, ha="center", fontsize=10)
    plt.tight_layout()
    plt.savefig(env_path)
    plt.close()

    graphs["environment_graph"] = {
        "path": env_path,
        "explanation": explain_single_graph(env_path, "Environment Factors", context_summary)
    }

    # ===== EMOTION GRAPH =====
    emotion = data.get("emotion", {}).get("emotion_distribution", {})
    emo_path = "outputs/graphs/emotion_distribution.png"
    if not emotion:
        plt.figure()
        plt.text(0.5, 0.5, "No emotion data", ha="center", va="center")
        plt.title("Emotion Distribution")
    else:
        labels = list(emotion.keys())
        sizes = list(emotion.values())
        colors = plt.cm.Pastel1(np.linspace(0, 1, len(labels)))
        plt.figure(figsize=(6, 6))
        plt.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=140, colors=colors)
        plt.title("Emotion Distribution")
    plt.savefig(emo_path)
    plt.close()

    graphs["emotion_graph"] = {
        "path": emo_path,
        "explanation": explain_single_graph(emo_path, "Emotion Distribution", context_summary)
    }

    # ===== POSTURE + BODY LANGUAGE GRAPH =====
    posture_data = data.get("posture", {}).get("frame_results", [])
    posture_path = "outputs/graphs/posture_body_language.png"
    if not posture_data:
        plt.figure()
        plt.text(0.5, 0.5, "No posture data available", ha="center", va="center")
        plt.title("Posture & Body Language Trends")
    else:
        postures = [p["posture"] for p in posture_data]
        bodylangs = [p["body_language"] for p in posture_data]
        posture_counts = Counter(postures)
        body_counts = Counter(bodylangs)
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 2, 1)
        plt.bar(posture_counts.keys(), posture_counts.values(), color="skyblue")
        plt.title("Posture Frequency")
        plt.xticks(rotation=30)
        plt.subplot(1, 2, 2)
        plt.bar(body_counts.keys(), body_counts.values(), color="lightgreen")
        plt.title("Body Language Frequency")
        plt.xticks(rotation=30)
        plt.tight_layout()
    plt.savefig(posture_path)
    plt.close()

    graphs["posture_graph"] = {
        "path": posture_path,
        "explanation": explain_single_graph(posture_path, "Posture and Body Language", context_summary)
    }

    return graphs
