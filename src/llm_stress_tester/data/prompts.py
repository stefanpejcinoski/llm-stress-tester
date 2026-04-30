"""Benchmark prompt samples for load testing.

Each suite contains a list of prompt templates. The load runner
cycles through these prompts, substituting placeholders as needed.
"""

from __future__ import annotations

from llm_stress_tester.enums import BenchmarkSuite

BENCHMARK_PROMPTS: dict[str, list[str]] = {
    BenchmarkSuite.CODING.value: [
        "Implement a Python function that finds all prime numbers up to n using the Sieve of Eratosthenes. Include type hints and docstring.",
        "Write an algorithm to detect cycles in a directed graph. Explain your approach and provide time/space complexity.",
        "Implement a thread-safe LRU cache in Python with configurable max size. Support get, put, and clear operations.",
        "Write a function that parses a CSV file into a list of dictionaries without using the csv module.",
        "Implement a binary search algorithm that returns all indices of a target value in a sorted array that may have duplicates.",
        "Create a Python decorator that caches function results with a TTL. The decorator should work with any function signature.",
        "Implement a simplified version of the A* pathfinding algorithm for a 2D grid. Handle obstacles and diagonal movement.",
        "Write a function that flattens a nested dictionary of arbitrary depth into dot-separated key-value pairs.",
    ],
    BenchmarkSuite.MATH.value: [
        "Solve this word problem: A train leaves Station A traveling at 60 mph. Two hours later, another train leaves Station B at 80 mph toward A. If they are 400 miles apart, when will they meet? Show all steps.",
        "Calculate the probability of getting exactly 3 heads in 5 coin flips, given that the first flip was heads. Explain your reasoning.",
        "Find the area of the region bounded by y = x^2 and y = 4. Show integration steps.",
        "A bag contains 5 red, 3 blue, and 2 green marbles. If you draw 3 without replacement, what is the probability of getting exactly 2 red marbles?",
        "Solve the differential equation: dy/dx + 2y = sin(x), with y(0) = 1.",
        "What is the expected number of rolls of a fair 6-sided die until you roll a 6, given that all rolls before the 6 were even numbers?",
        "Compute the determinant of a 3x3 symbolic matrix and explain each step of the calculation.",
        "In a game where you flip a coin and win $2 for heads or lose $1 for tails, what is the probability of reaching +$10 before -$5 starting from $0?",
    ],
    BenchmarkSuite.KNOWLEDGE.value: [
        "Compare and contrast the economic policies of Keynes and Friedman. Discuss their differing views on government intervention, monetary policy, and fiscal stimulus. Provide specific historical examples.",
        "Explain the process of photosynthesis, including both the light-dependent and light-independent (Calvin cycle) reactions. Describe where each occurs, what enters and exits, and how energy is stored.",
        "What are the primary causes and effects of the fall of the Roman Empire? Discuss military, political, economic, and social factors with specific dates and events.",
        "Describe the standard of care in medical malpractice cases. How is it determined, what evidence is used, and what are the challenges in proving it?",
        "Explain the structure and function of DNA. Describe replication, transcription, and translation, including key enzymes and molecules involved.",
        "What are the main principles of democracy? Compare representative democracy with direct democracy, discussing advantages and disadvantages of each system with real-world examples.",
        "Describe the geological processes that form mountains. Discuss tectonic plate interactions, erosion patterns, and how mountain ranges change over millions of years.",
        "Explain the theory of general relativity and how it differs from Newton's theory of gravity. Include discussions of time dilation, gravitational lensing, and real-world applications like GPS.",
    ],
    BenchmarkSuite.INSTRUCTION_FOLLOWING.value: [
        "Write exactly 50 words describing artificial intelligence. Output as valid JSON with the key 'description'. Do not include any other keys or code blocks.",
        "Summarize the concept of quantum computing in exactly 3 sentences. Each sentence must be under 20 words. Do not use technical jargon.",
        "List 10 programming languages. Output as a numbered list. Do not use bullet points or markdown formatting. Include the year each was created.",
        "Explain deep learning without using the words: learn, data, model, neural, network. Keep it under 100 words and make it understandable to a 12-year-old.",
        "Write a paragraph about space exploration that contains: exactly 5 paragraphs, each containing 'star', at least 3 numbers, and no more than 2 commas per sentence.",
        "Generate a recipe for pasta. It must include: a title, exactly 5 ingredients, cooking time, and steps numbered 1-10. Do not use bullet points.",
        "Write a product description for headphones that mentions 'noise cancellation' exactly 3 times and 'comfortable' at least twice. Keep it between 75 and 100 words.",
        "Describe a city using only analogies and similes. Each sentence must contain exactly one comparison. Write exactly 5 sentences.",
    ],
    BenchmarkSuite.MULTI_TURN.value: [
        "Turn 1: 'I'm researching renewable energy sources for a presentation. Can you compare solar and wind power for residential use?' (After response) Turn 2: 'What about battery storage solutions to handle intermittency?' (After response) Turn 3: 'Now compare the costs and ROI over 20 years for a typical household.'",
        "Turn 1: 'I need help designing an API for an e-commerce platform.' (After response) Turn 2: 'Now add authentication with JWT tokens and role-based access.' (After response) Turn 3: 'Implement rate limiting and caching strategies for the product catalog endpoint.'",
        "Turn 1: 'I want to learn Python. I know JavaScript well. Where should I start?' (After response) Turn 2: 'That's helpful. Can you explain Python decorators and give me exercises to practice?' (After response) Turn 3: 'Now explain generators and iterators with practical examples from data processing.'",
        "Turn 1: 'Act as a business consultant. My startup has 10 employees and I need to scale to 100 in 2 years. What organizational challenges should I anticipate?' (After response) Turn 2: 'How do I handle the cultural challenges of rapid growth?' (After response) Turn 3: 'What governance structures should I put in place for a 100-person company?'",
        "Turn 1: 'I have a persistent headache for 2 weeks. ' (After response) Turn 2: 'The pain is worst in the mornings and I also have sensitivity to light.' (After response) Turn 3: 'What tests would you recommend and what are the possible diagnoses?'",
    ],
    BenchmarkSuite.LONG_CONTEXT.value: [
        "Here is a 10,000-word report on global trade patterns. Read it carefully and then answer: What are the top 5 emerging trade corridors mentioned? For each, provide statistics and a brief analysis of growth potential.",
        "Read this 8,000-word technical documentation. Then: 1) Find all mentions of 'bandwidth'. 2) Extract all API endpoint URLs. 3) Summarize the security requirements in 3 bullet points. 4) List all error codes and their descriptions.",
        "I will provide a 15,000-word novel excerpt. After reading: 1) Create a character list with their motivations. 2) Identify the main conflict. 3) Explain the setting in detail. 4) Note any foreshadowing you find.",
        "Read this 12,000-word legal document about contract law. Then answer: What are the 3 key clauses regarding liability? What remedies are specified? Summarize the court's reasoning.",
        "Here is a 20,000-word transcript of a congressional hearing. Extract: all names of witnesses, each witness's main argument, key statistics cited, and any disagreements between witnesses.",
        "Analyze this 9,000-word medical research paper. Summarize: the hypothesis, methodology with sample sizes, key findings with p-values, limitations, and recommendations for future research.",
        "Read the following 11,000-word company quarterly report. Extract: revenue by division, percentage changes from previous quarter, Cautionary sections, names of executives quoted, and the CEO's key strategic priorities.",
        "Read this 7,000-word historical analysis of the Cold War. Find specific quotes about: the Cuban Missile Crisis, the arms race economic impact, proxy wars, and the role of technology competition.",
    ],
    BenchmarkSuite.TEXT_PROCESSING.value: [
        "Summarize the following text into exactly 5 bullet points, keeping all key statistics and proper nouns. If the text is about climate policy, extract the policy recommendations specifically: [Long article about climate policy with multiple sections]",
        "Extract all named entities from this text and classify them as PERSON, ORGANIZATION, LOCATION, DATE, or MISC. Output as JSON with arrays for each category: [Long news article covering multiple events]",
        "Analyze the sentiment of each paragraph in this product review document. Provide: per-paragraph sentiment score (-1 to 1), overall sentiment, extracted pros and cons, and a summary recommendation.",
        "Extract the structured information from this unstructured resume text: name, email, phone, education (degree, school, year), work experience (company, role, duration, key achievements), skills.",
        "Classify each paragraph into one of these categories: marketing, technical, financial, legal, general. For each classification, provide confidence level and justification in one sentence.",
        "Given this customer support conversation, extract: the customer's main issue, agent responses, resolution status, follow-up required (yes/no with reason), and overall satisfaction indicators.",
        "Extract key-value pairs from this technical specification document: protocol versions, supported features, performance metrics, compatibility requirements, and security features. Output as JSON.",
        "Compare these three product descriptions and extract: common features, distinguishing features, price points, target audiences, and stated advantages over competitors.",
    ],
}

SUITES_ORDER: list[str] = [
    BenchmarkSuite.CODING.value,
    BenchmarkSuite.MATH.value,
    BenchmarkSuite.KNOWLEDGE.value,
    BenchmarkSuite.INSTRUCTION_FOLLOWING.value,
    BenchmarkSuite.MULTI_TURN.value,
    BenchmarkSuite.LONG_CONTEXT.value,
    BenchmarkSuite.TEXT_PROCESSING.value,
]

SUITES_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    BenchmarkSuite.CODING.value: ("Coding", "Algorithm, debugging, code generation"),
    BenchmarkSuite.MATH.value: ("Math", "Word problems, probability, calculus"),
    BenchmarkSuite.KNOWLEDGE.value: ("Knowledge", "Science, history, domain expertise"),
    BenchmarkSuite.INSTRUCTION_FOLLOWING.value: ("Instruction", "Strict formatting and constraints"),
    BenchmarkSuite.MULTI_TURN.value: ("Multi-Turn", "Conversational context"),
    BenchmarkSuite.LONG_CONTEXT.value: ("Long Context", "8K-20K+ word documents"),
    BenchmarkSuite.TEXT_PROCESSING.value: ("Text Processing", "Summarization, extraction, classification"),
}


def get_all_suites() -> list[str]:
    """Return the list of available benchmark suite IDs."""
    return SUITES_ORDER


def get_suite(suitename: str) -> dict[str, list[str]] | None:
    """Return the prompt list for a given suite ID, or None."""
    if suitename in BENCHMARK_PROMPTS:
        return {suitename: BENCHMARK_PROMPTS[suitename]}
    return None


def get_all_prompt_ids() -> list[str]:
    """Return a flat list of 'suite-index' prompt IDs for every suite."""
    ids: list[str] = []
    for suitename in SUITES_ORDER:
        prompts = BENCHMARK_PROMPTS.get(suitename, [])
        for idx in range(len(prompts)):
            ids.append(f"{suitename}-{idx + 1}")
    return ids


def get_prompt(suitename: str, prompt_index: int) -> str:
    """Return a single prompt string by suitename and zero-based index."""
    prompts = BENCHMARK_PROMPTS.get(suitename, [])
    if not prompts:
        return ""
    return prompts[prompt_index % len(prompts)]


def get_prompt_suite_index(prompt_id: str) -> tuple[str, int]:
    """Parse a 'suite-N' prompt_id back to (suitename, index)."""
    parts = prompt_id.split("-", 1)
    suitename = parts[0]
    idx = int(parts[1]) - 1 if len(parts) > 1 else 0
    return suitename, idx
