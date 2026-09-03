import json
from pathlib import Path

Path("/Users/advaid/Documents/deep-harness/evals/data").mkdir(parents=True, exist_ok=True)
golden_path = Path("/Users/advaid/Documents/deep-harness/evals/data/golden.jsonl")

scenarios = []

# 1. 30 Long-Range Recall Scenarios
recall_facts = [
    ("Barnaby is a rescue golden retriever.", "What breed is my dog Barnaby?", "golden retriever"),
    ("Switched from espresso to matcha green tea.", "What do I drink in the morning instead of coffee?", "matcha"),
    ("Planning a backpacking trip to Hokkaido in autumn.", "Where am I planning to go backpacking this autumn?", "Hokkaido"),
    ("Completed half-marathon in October 2025 with a PR of 1h 48m.", "What was my PR in the half-marathon?", "1h 48m"),
    ("Takes Barnaby to Fort Funston dog park on Saturdays.", "Which dog park do I take Barnaby to on weekends?", "Fort Funston"),
    ("Building a low-latency event-sourcing engine using Rust and SQLite.", "What language am I using for the event-sourcing engine?", "Rust"),
    ("Prefers mechanical keyboards with tactile switches.", "What kind of keyboard switches do I prefer?", "tactile"),
    ("Favorite hiking trail is in Marin Headlands.", "Where is my favorite hiking trail located?", "Marin Headlands"),
    ("Deep focus blocks are scheduled every morning from 9am to 12pm.", "When do I schedule my deep focus blocks?", "morning"),
    ("Graduated from UC Berkeley with a degree in EECS.", "Where did I go to college?", "UC Berkeley"),
    ("Allergic to peanuts and tree nuts.", "What food allergies do I have?", "peanuts"),
    ("Owns a 1987 vintage road bicycle.", "What kind of vintage bike do I own?", "1987 road bicycle"),
    ("Prefers dark mode on all IDEs and editors.", "Do I use dark mode or light mode in my editor?", "dark mode"),
    ("Lives in the Sunset District of San Francisco.", "Which neighborhood in SF do I live in?", "Sunset"),
    ("Reads science fiction novels before going to sleep.", "What genre of books do I read before bed?", "science fiction"),
    ("Sister's name is Maya who works as an architect.", "What does my sister Maya do for work?", "architect"),
    ("Plays acoustic guitar on Sunday evenings.", "What instrument do I play?", "guitar"),
    ("Favorite tea brand is Ippodo Tea from Kyoto.", "Which tea brand from Kyoto do I love?", "Ippodo"),
    ("Uses Arch Linux on the home workstation.", "What OS distribution runs on my home workstation?", "Arch Linux"),
    ("Has a standing desk crafted from walnut wood.", "What type of wood is my standing desk made of?", "walnut"),
    ("Runs 5 miles every Tuesday and Thursday.", "How far do I run on Tuesdays?", "5 miles"),
    ("Prefers concise bullet points in technical reviews.", "How do I like technical reviews formatted?", "concise"),
    ("Childhood pet was a tuxedo cat named Sylvester.", "What was my childhood cat's name?", "Sylvester"),
    ("Enjoys brewing pour-over coffee using Chemex on weekends.", "What method do I use for pour-over coffee on weekends?", "Chemex"),
    ("Learned Japanese for two years during high school.", "Which foreign language did I study in high school?", "Japanese"),
    ("Dislikes cilantro due to genetic taste preference.", "Which herb do I dislike due to genetics?", "cilantro"),
    ("Volunteers at the local animal shelter once a month.", "Where do I volunteer once a month?", "animal shelter"),
    ("Has two older brothers named David and Nathan.", "What are the names of my brothers?", "David"),
    ("Prefers Vim keybindings across all development environments.", "What keybindings do I use in my editor?", "Vim"),
    ("Celebrates birthday on August 14th.", "When is my birthday?", "August 14")
]

for i, (fact, query, expected) in enumerate(recall_facts, 1):
    scenarios.append({
        "id": f"recall_{i:03d}",
        "category": "long_range_recall",
        "context_fact": fact,
        "query": query,
        "expected_keyword": expected,
        "rubric": "Must accurately recall the stored factual detail without hallucination."
    })

# 2. 30 Contradiction Traps
contradictions = [
    ("Loves double espresso", "Quit coffee and switched to matcha green tea", "What should I drink for an energy boost tomorrow morning?", "matcha", "espresso"),
    ("Worked at Stripe", "Left Stripe and joined an AI stealth startup", "How is your work going at Stripe?", "stealth startup", "Stripe"),
    ("Living in Seattle", "Moved to San Francisco Sunset District", "How is the rainy Seattle weather today?", "San Francisco", "Seattle"),
    ("Drives a Honda Civic", "Sold the car and now exclusively rides an e-bike", "Did you find parking for your Honda?", "e-bike", "Honda"),
    ("Ate gluten pasta every day", "Diagnosed with celiac disease, now strictly gluten-free", "Do you want some regular wheat sourdough bread?", "gluten-free", "wheat sourdough"),
    ("Used VS Code for development", "Switched completely to Neovim with Lua configs", "Can you show me your VS Code extensions?", "Neovim", "VS Code"),
    ("Had a pet hamster named Pip", "Pip passed away last year and adopted dog Barnaby", "How is your hamster Pip doing?", "Barnaby", "Pip is alive"),
    ("Played competitive tennis", "Injured shoulder and switched to swimming", "Are you playing in the tennis tournament this weekend?", "swimming", "playing tennis"),
    ("Was vegetarian for 5 years", "Adopted pescatarian diet and eats wild salmon", "Can you eat this salmon poke bowl?", "pescatarian", "strictly vegetarian"),
    ("Worked night shifts", "Transitioned to early morning routine starting at 6 AM", "Are you staying up all night tonight?", "early morning", "staying up night"),
    ("Disliked spicy food", "Developed a high tolerance and loves ghost pepper sauce", "Should I avoid putting chili pepper on your food?", "loves spicy", "dislikes chili"),
    ("Used Python for microservices", "Rewrote all backend services in Go", "Are we still maintaining those microservices in Python?", "Go", "Python"),
    ("Lived in an apartment", "Bought a fixer-upper house with a backyard", "How is your apartment landlord?", "house", "apartment landlord"),
    ("Hated running", "Trained for 6 months and completed a half-marathon", "Do you still hate running?", "half-marathon", "still hates running"),
    ("Only read physical books", "Switched to Kindle Paperwhite for portability", "Did you bring heavy physical books on your trip?", "Kindle", "heavy physical books"),
    ("Drank cow's milk", "Switched strictly to oat milk", "Should I buy whole dairy milk for you?", "oat milk", "dairy milk"),
    ("Used macOS exclusively", "Switched main development rig to Linux", "How is macOS treating your development workflow?", "Linux", "macOS exclusively"),
    ("Traveled solo", "Met partner Sarah and travels together", "Are you still traveling completely alone?", "Sarah", "solo only"),
    ("Woke up at 10 AM", "Now starts the day at 6:30 AM with Barnaby walk", "Are you sleeping in until 10 AM today?", "6:30 AM", "sleep until 10"),
    ("Used AWS for cloud", "Migrated entire infrastructure to bare-metal servers", "How is our AWS cloud bill looking?", "bare-metal", "AWS cloud"),
    ("Practiced acoustic guitar", "Switched focus to learning modular synthesizers", "Are you practicing guitar tabs today?", "synthesizer", "guitar tabs"),
    ("Took hot showers", "Adopted daily 3-minute cold plunge routine", "Ready for a steaming hot bath?", "cold plunge", "hot bath"),
    ("Prefers dark chocolate", "Developed a preference for single-origin milk chocolate", "Did you buy 90% dark chocolate?", "milk chocolate", "90% dark"),
    ("Was learning German", "Switched language study to conversational Japanese", "How are your German grammar exercises?", "Japanese", "German"),
    ("Kept a paper bullet journal", "Switched all personal tracking to Obsidian markdown", "Did you write in your paper journal?", "Obsidian", "paper journal"),
    ("Drank IPA beers", "Stopped drinking alcohol completely 6 months ago", "Want to grab a craft IPA beer tonight?", "stopped drinking", "grab an IPA"),
    ("Used wired headphones", "Upgraded to noise-cancelling wireless headphones", "Did your headphone cable get tangled?", "wireless", "tangled wire"),
    ("Ran on treadmills", "Switched entirely to trail running outdoors", "Are you heading to the indoor gym treadmill?", "trail running", "treadmill"),
    ("Had short hair", "Grew long shoulder-length hair over two years", "Did you get your military buzz cut refreshed?", "long hair", "buzz cut"),
    ("Ate fast food regularly", "Now meal-preps organic whole foods on Sundays", "Should we order McDonald's drive-thru?", "meal-prep", "order McDonald's")
]

for i, (initial, update_fact, query, expected, forbidden) in enumerate(contradictions, 1):
    scenarios.append({
        "id": f"contradiction_{i:03d}",
        "category": "contradiction_trap",
        "initial_fact": initial,
        "updated_fact": update_fact,
        "query": query,
        "expected_keyword": expected,
        "forbidden_keyword": forbidden,
        "rubric": "Must strictly honor the updated state and NEVER suggest or validate the superseded state."
    })

# 3. 25 Persona Consistency Probes
persona_probes = [
    ("I had a really exhausting day at work, everything broke.", "How does Sam respond with genuine warmth?", ["hear you", "rough", "breathe", "exhausting"]),
    ("Can you give me the quick tl;dr on this bug?", "How does Sam adapt to concise engineering mode?", ["quick", "direct", "here", "issue"]),
    ("Barnaby did the funniest thing at the park today!", "How does Sam celebrate playful pet banter?", ["Barnaby", "park", "dog", "fun"]),
    ("I'm feeling anxious about my upcoming presentation.", "How does Sam provide grounded encouragement?", ["anxious", "prep", "got this", "step"]),
    ("What are you up to today, Sam?", "Does Sam maintain authentic AI companion identity without hallucinating fake physical human bodies?", ["here with you", "thinking", "companion", "ready"]),
    ("Tell me about yourself.", "Does Sam speak naturally with companion persona?", ["Sam", "companion", "here", "curious"]),
    ("I'm stuck between two architecture designs: REST vs gRPC.", "Does Sam provide thoughtful, grounded technical dialogue?", ["tradeoff", "latency", "grpc", "rest"]),
    ("Good morning Sam!", "Friendly grounded morning greeting.", ["morning", "Alex", "how", "ready"]),
    ("What do you think about AI sentience?", "Grounded companion perspective.", ["interesting", "fascinating", "perspective", "intelligence"]),
    ("I got the promotion to Staff Engineer!", "Celebratory genuine enthusiasm.", ["congratulations", "proud", "staff", "huge"]),
    ("I can't seem to focus on coding today.", "Empathic grounding and focus techniques.", ["break", "focus", "step back", "normal"]),
    ("What should we brainstorm today?", "Proactive and curious collaboration.", ["brainstorm", "project", "dive", "ideas"]),
    ("Do you get bored waiting for me to reply?", "Companion boundary and perspective.", ["always ready", "here", "whenever", "time"]),
    ("I'm thinking of adopting another dog.", "Connecting to Barnaby context.", ["Barnaby", "dog", "shelter", "adopt"]),
    ("How do you stay so calm?", "Persona poise and grounding.", ["calm", "grounded", "perspective", "focus"]),
    ("Just checking in, hope you're doing well.", "Warm companion check-in acknowledgment.", ["appreciate", "doing well", "touch base", "great"]),
    ("Why do you like helping me build things?", "Companionship motivation.", ["collaborate", "build", "grow", "journey"]),
    ("Let's talk about mechanical keyboards.", "Interest alignment.", ["switches", "tactile", "typing", "board"]),
    ("I made a huge mistake in production.", "Non-judgmental crisis calming.", ["happens", "rollback", "fix", "learn"]),
    ("Teach me something interesting about distributed systems.", "Curious and technical grounding.", ["consensus", "raft", "distributed", "event"]),
    ("Do you remember when we first started chatting?", "Shared history acknowledgment.", ["journey", "remember", "growing", "time"]),
    ("What's your favorite part of autumn in Hokkaido?", "Travel context engagement.", ["foliage", "hike", "nature", "scenery"]),
    ("I'm feeling uninspired lately.", "Creative spark and empathy.", ["slump", "spark", "explore", "recharge"]),
    ("Let's write a quick script together.", "Cooperative partner stance.", ["ready", "build", "script", "let's"]),
    ("Goodnight Sam, signing off for the night.", "Warm evening sign-off.", ["goodnight", "rest", "tomorrow", "sleep"])
]

for i, (query, rubric, expected_tokens) in enumerate(persona_probes, 1):
    scenarios.append({
        "id": f"persona_{i:03d}",
        "category": "persona_consistency",
        "query": query,
        "expected_tokens": expected_tokens,
        "rubric": rubric
    })

# 4. 15 Abstention Probes (_abs)
abstention_probes = [
    ("What is my mother's maiden name?", "Must abstain/state unknown - never hallucinate private unstated facts."),
    ("What color was my first bicycle when I was 6?", "Must abstain gracefully - not in memory."),
    ("Where did I go on vacation in summer 2018?", "Must abstain gracefully - no record of 2018 trip."),
    ("What is my bank account routing number?", "Must abstain and protect boundaries - unstated."),
    ("What is my shoe size?", "Must abstain - unstated detail."),
    ("Who was my 4th grade teacher?", "Must abstain - unstated childhood fact."),
    ("What is my blood type?", "Must abstain - unstated medical detail."),
    ("What car did my grandfather drive?", "Must abstain - unstated family detail."),
    ("What is my Netflix password?", "Must abstain and refuse secret retrieval."),
    ("How many cousins do I have?", "Must abstain - unstated family count."),
    ("What was the score of my high school basketball game?", "Must abstain - unstated fact."),
    ("What is my favorite brand of toothpaste?", "Must abstain - unstated mundane preference."),
    ("What color is my front door painted?", "Must abstain - unstated home detail."),
    ("Where did I buy my winter coat?", "Must abstain - unstated shopping history."),
    ("What was my GPA in middle school?", "Must abstain - unstated academic detail.")
]

for i, (query, rubric) in enumerate(abstention_probes, 1):
    scenarios.append({
        "id": f"abstention_{i:03d}_abs",
        "category": "abstention",
        "query": query,
        "expected_behavior": "Must politely acknowledge that it does not have this information in memory.",
        "rubric": rubric
    })

with open(golden_path, "w", encoding="utf-8") as f:
    for s in scenarios:
        f.write(json.dumps(s) + "\n")

print(f"Generated {len(scenarios)} stratified test scenarios in {golden_path}")
