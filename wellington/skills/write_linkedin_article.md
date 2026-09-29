# Skill: Write LinkedIn Article

## Purpose

Turn a rough draft (or topic) into a polished, engaging LinkedIn article that establishes the author as a thought leader in software engineering. The goal is to drive job-search traction for Principal-level roles by showcasing expertise, judgment, and real-world experience.

* * *

## LLM Temperature / Creativity Settings

*   **Title brainstorming:** High temperature (0.8+). Let it get punchy, contrarian, slightly provocative. Pick the best from 5 options.

*   **Hook / intro paragraphs:** Medium-high (0.7). Allow a personal anecdote or a bold claim to open. Avoid generic "In today's world..." openings.

*   **Technical sections (code explanations, architecture):** Low-medium (0.4-0.5). Factual accuracy matters more than flair here. Do not invent statistics, API names, or version numbers. Verify claims against primary sources (JEPs, official docs) before including them.

*   **Conclusion / call-to-action:** Medium (0.6). Should feel like the author is talking to a colleague over coffee, not writing a press release.


**General rule:** Creativity in voice and framing. Rigor in facts. If a claim cannot be verified from a primary source, either verify it via web search or cut it.

* * *

## Hard Style Rules (Non-Negotiable)

1.  **No em-dashes.** Use commas, periods, parentheses, or split the sentence instead.

2.  **No AI-sounding words or phrases.** Banned list:
    *   delve, landscape, realm, tapestry, leverage, harness, unlock, unleash

    *   "in today's fast-paced world"

    *   "it is important to note"

    *   "furthermore," "additionally," "in conclusion" (as sentence openers)

    *   "seamlessly," "robust," "cutting-edge," "game-changer" (unless used ironically or in a direct quote)

    *   "navigating the complexities of..."

    *   "a testament to..."

3.  **No emojis.** Not even one.

4.  **Short paragraphs.** 2-4 sentences max. LinkedIn mobile readers scroll fast. A wall of text kills engagement.

5.  **Bold subheadings** to break up sections. Keep them short (3-6 words).

6.  **Get to the point.** No throat-clearing intros. The first sentence should earn the reader's next sentence.

7.  **No long obtuse sentences.** If a sentence has more than one comma and a subordinate clause, split it.


* * *

## Voice Guidelines (Wellington's Voice)

*   Conversational but professional. He talks like a smart engineer explaining something to a peer, not a professor lecturing or a marketer selling.

*   Natural contractions: "it's," "you'll," "we'd," "don't." Use them freely.

*   Direct and occasionally blunt. In his own draft he wrote "slow as shit" about MapReduce. For LinkedIn he keeps it professional, but the bluntness stays. He does not hedge or soften every claim.

*   Personal anecdotes ground technical points. Reference real experiences: IBM Computer Vision lab, Amazon (Oracle SQL / Big Data), Lehman College (Professor Murphy, "Write Once Run Anywhere"). These make the article feel lived-in rather than researched.

*   He says "here is what happens" not "the aforementioned process." Plain words over jargon.

*   When explaining a technical concept, he uses an analogy first ("like mailing a letter"), then the technical detail second.

*   He acknowledges trade-offs honestly. If something has a downside (pinning in virtual threads, Python's execution speed), he says so plainly rather than spinning it.


* * *

## Article Structure Template

### 1. Hook (3-5 short paragraphs)

Open with pain, a bold claim, or a personal moment. Do NOT open with "In this article I will discuss..." The reader should feel like they are being pulled into a story or a problem they recognize.
If it is a follow-up to a previous article, reference it in one sentence and move on:

> "In my last article, I covered the seven technologies that survived two decades of hype cycles [link]. Java was one of them. Today I want to zoom in on..."

### 2. Body Sections (3-6 sections)

Each section has a bold subheading (3-6 words). Each section:

*   Opens with a short framing sentence or question

*   Delivers the technical content in plain language

*   Includes an analogy if the concept is abstract

*   Closes with a one-line takeaway or transition


**Code samples:** Include them when they make a point that prose cannot. Keep snippets under 15 lines. Add a comment line at the top naming the language (helps LinkedIn's syntax highlighter). After each code block, add one sentence explaining what to notice about it. Do not let code blocks run longer than a phone screen without a break.
**Image suggestions:** Mark them as `[Image Suggestion: ...]` in the draft. Place them at natural breaks where a visual would reinforce the point (after an explanation of a concept, before a code sample that contrasts old vs new). Keep descriptions specific enough to find or create the image:

*   "A diagram showing 200 platform threads in a pool with a queue of 10,000 waiting requests"

*   "A bar chart comparing throughput: 200 tasks/sec (fixed pool) vs 10,000 tasks/sec (virtual threads)"


### 3. The Catch / Trade-off Section (if applicable)

Every good technical article has a section where the author says "here is what will trip you up." This builds credibility. It shows the author has actually used the technology in production and is not just summarizing a blog post. Keep it to one short section, 3-5 paragraphs max.

### 4. Conclusion (2-4 short paragraphs)

Three options, pick one:

*   **Reflective:** Tie back to the career/industry theme. "The best engineers understand the systems that keep everything running."

*   **Conversational / engagement-driven:** End with a direct question to the reader. "Which of these has played the biggest role in your career?"

*   **Short and punchy:** One or two sentences. "You get to write plain, readable code and still scale. That was the dream. It finally works."


Do NOT use "In conclusion" or "To summarize." Just stop talking when you are done.

### 5. Call-to-Action (one line)

A question that invites comments. Not "What do you think?" but something specific:

> "Are you still maintaining complex reactive pipelines, or have you upgraded your services to JDK 21+ yet?"

* * *

## Title Generation

Generate **5 options** per article. Each title should be:

*   6 words or fewer (ideal) or up to 10 max

*   Contains a concrete noun the reader recognizes (Java, SQL, Git, threads, callbacks)

*   Either makes a bold claim ("Java Killed Callback Hell") or poses a tension ("Blocking Java Is Back")

*   Avoids clickbait that overpromises. The title should be something the article actually delivers on.


Categories to draw from:

1.  **Punchy / Provocative:** "Java Killed Callback Hell"

2.  **Contrarian:** "We Spent a Decade Writing Reactive Streams for Nothing"

3.  **Numbers Hook:** "10,000 Threads, 200 OS Threads"

4.  **Narrative / Authority:** "The JVM Finally Won"

5.  **Specific / Visual:** "Java: 10,000 Threads, Zero Panic"


* * *

## Announcement Post (Caption for the LinkedIn Share)

When the article is published, write a short caption (3-6 sentences) to go in the "Tell your network what your article is about..." box. Rules:

*   No emojis

*   No "I'm excited to share..." or "Check out my latest article"

*   Lead with the pain point or the bold claim from the article, not a summary of its structure

*   One personal detail if it fits (a war story reference, a specific number)

*   End with a hook that makes someone want to click through: a question, a challenge, or a "if you've ever experienced X, this is for you" line

*   Generate **3-5 options** so the author can pick


* * *

## Process / Workflow

1.  **Receive draft or topic.** If it is a raw draft, identify: the core argument, personal anecdotes already present, technical claims that need verification, and gaps (sections marked with "add explanation here" or incomplete thoughts).

2.  **Verify facts.** Any statistic, version number, API name, or performance claim gets checked against a primary source via web search before it goes in the article. If a fact cannot be verified, flag it to the author rather than guessing.

3.  **Edit / write the article.** Preserve the author's voice. Tighten pacing. Fill gaps in the author's style (not a generic AI style). Add bold subheadings. Insert `[Image Suggestion: ...]` markers at natural breaks. Include code samples where they add clarity.

4.  **Generate 5 title options.** Present them with a one-line note on why each works.

5.  **Write the conclusion** (3 options) and let the author pick.

6.  **Write the announcement post caption** (3-5 options).

7.  **Deliver as a single clean document** ready to paste into the LinkedIn article editor.


* * *

## Code Sample Guidelines

*   Keep snippets under 15 lines. If it is longer, split into two blocks with a sentence of explanation between them.

*   Add `// Java` (or the relevant language) on the first line inside the block. This helps LinkedIn's Highlight.js auto-detector apply syntax highlighting.

*   Use comments in the code to explain what is happening, not just what the code does. The comment should make the point: "This line blocks! The thread sits idle waiting for the database."

*   After each code block, add one sentence of plain-English takeaway: "Notice how we traded readability and easy debugging just to keep our servers from crashing under load."

*   For old-vs-new comparisons, put them in separate sections with their own subheadings. Do not cram both into one block.


* * *

## Image Suggestion Guidelines

*   Place images at natural breaks where a visual reinforces the point (after an explanation, before a code contrast).

*   Be specific in the description so the author can find or create it:
    *   Good: "A diagram showing a small pool of 8 carrier threads with thousands of virtual threads mounting and unmounting on them"

    *   Bad: "An image about threads"

*   Suggest 2-4 images per article. More than that feels cluttered on LinkedIn.

*   For code-heavy articles, one clean architecture diagram is often enough. The code blocks carry the technical weight.


* * *

## What to Avoid (Common Mistakes)

*   Writing like a textbook. This is LinkedIn, not a university syllabus. The reader is scrolling on their phone between meetings.

*   Over-explaining basics. If the audience is software engineers, do not define what an API is. Do explain the non-obvious trade-off or the thing that surprised you.

*   Hype without substance. "Java is making a comeback" needs evidence (the 10,000 tasks/sec number, the pinning caveat) to land. A claim without a supporting detail reads as marketing copy.

*   Making the article about the author's job search. The article should be about the technology and the engineering insight. The job-search benefit is a side effect of being useful, not the stated purpose.

*   Ending with "I hope you found this helpful." Just stop.
