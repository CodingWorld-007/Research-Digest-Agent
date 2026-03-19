from agent.pipeline import ResearchPipeline
 
if __name__ == "__main__":
    inputs = [
        "https://en.wikipedia.org/wiki/Regulation_of_artificial_intelligence",
        "https://en.wikipedia.org/wiki/AI_safety",
        "https://en.wikipedia.org/wiki/Algorithmic_bias",
        "https://en.wikipedia.org/wiki/Artificial_general_intelligence",
        "https://en.wikipedia.org/wiki/Ethics_of_artificial_intelligence",
    ]
 
    pipeline = ResearchPipeline()
    pipeline.run(inputs)
 